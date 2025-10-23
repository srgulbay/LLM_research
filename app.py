# -*- coding: utf-8 -*-
"""
LLM_Research - Bilimsel Veri Toplama Platformu (Sürüm 2.1)
Bu sürüm, asenkron puanlama için Redis/RQ kullanır,
Railway (PostgreSQL) ile yerel (SQLite) geliştirmeyi destekler ve
dinamik skor takibi özelliği içerir.
"""

# --- 1. GEREKLİ KÜTÜPHANELER ---
import os
import json
import csv
import io
import random
import datetime
import time
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from dotenv import load_dotenv
import google.generativeai as genai
from redis import Redis
from rq import Queue
from rq.job import Job
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

# --- YENİ EKLENEN SATIR ---
# (NOT: Daha önce buraya eklenmiş olan "from test_routes import *" satırı SİLİNDİ)
# ---

# --- 2. UYGULAMA KURULUMU VE YAPILANDIRMA ---

app = Flask(__name__)

# --- YENİ EKLENEN SATIR ---
app.jinja_env.globals['zip'] = zip
# ---

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

# Projenin ana dizinini belirle
basedir = os.path.abspath(os.path.dirname(__file__))

# Gizli Anahtar
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'yerel-gelistirme-icin-guvensiz-anahtar')

# Veritabanı Yapılandırması (Railway/PostgreSQL veya Yerel/SQLite)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 3. EKLENTİLERİ BAŞLATMA (DB, LOGIN, REDIS) ---

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'giris'
login_manager.login_message = "Bu araştırma platformunu kullanmak için lütfen giriş yapın."
login_manager.login_message_category = "info"

# Redis ve RQ (Asenkron Görev Kuyruğu) Yapılandırması
redis_url = os.getenv('REDIS_URL')
if not redis_url:
    print("UYARI: REDIS_URL bulunamadı. Görevler yerel olarak çalışmayabilir.")
    conn = None
    queue = None
else:
    conn = Redis.from_url(redis_url)
    queue = Queue("default", connection=conn)

# --- 4. GEMINI API YAPILANDIRMASI ---

model = None
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "AIzaSy...":
        raise ValueError("GEMINI_API_KEY bulunamadı veya ayarlanmamış. Lütfen .env dosyanızı kontrol edin.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    print("Gemini API (gemini-2.5-flash) başarıyla yapılandırıldı.")
except Exception as e:
    print(f"HATA: Gemini API yapılandırılamadı: {e}")

# --- 5. VERİTABANI MODELLERİ ---
class LLM(db.Model):
    """Sistemde kullanılacak yapay zeka modellerini saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<LLM {self.name}>'

class User(UserMixin, db.Model):
    """Kullanıcı bilgilerini (demografi dahil) saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Yönetici şifreleri için eklendi
    is_admin = db.Column(db.Boolean, default=False)
    profession = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    has_consented = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # --- GÜNCELLENECEK SATIR ---
    responses = db.relationship('UserResponse', back_populates='author', lazy=True)
    # ---

    def __repr__(self):
        return f'<User {self.email}>'

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    research_id = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    content = db.Column(db.JSON, nullable=True)

    # --- YENİ SÜTUN ---
    # Her LLM'in bu vaka için aldığı skorları saklar.
    # Örnek: {"GPT-4": {"overall_score": 92.5, "question_scores": {"q1": 90}}, "Gemini-Pro": {...}}
    llm_scores = db.Column(db.JSON, nullable=True)
    # ---

    # --- DEĞİŞTİRİLDİ: backref yerine back_populates kullanılıyor ---
    responses = db.relationship('UserResponse', back_populates='case', lazy=True)
    # Eğer hala ayrı gold/reference tabloyu kullanmak isterseniz ilişkiyi bırakabilirsiniz
    reference_answers = db.relationship('ReferenceAnswer', backref='case', lazy=True)

class ReferenceAnswer(db.Model):
    """Vakalar için 'Altın Standart' yanıtlarını tutan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    source = db.Column(db.String(100), nullable=False, index=True) # 'gold', 'chatgpt' etc.
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class UserResponse(db.Model):
    """Kullanıcının bir vakaya verdiği yanıt ve bu yanıta ait metadata."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    answers = db.Column(db.JSON, nullable=False)
    confidence_score = db.Column(db.Integer)
    clinical_rationale = db.Column(db.Text)
    scores = db.Column(db.JSON)
    duration_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # --- DEĞİŞTİRİLDİ: case ilişkisi back_populates ile tanımlandı ---
    case = db.relationship('Case', back_populates='responses')
    author = db.relationship('User', back_populates='responses')

    def __repr__(self):
        return f'<UserResponse {self.id} - Case {self.case_id} - User {self.user_id}>'

class Research(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Bu araştırma altındaki vakaları bağlamak için ilişki
    cases = db.relationship('Case', backref='research', lazy=True)

    def __repr__(self):
        return f'<Research {self.title}>'

# --- 6. YARDIMCI FONKSİYONLAR VE DECORATOR'LAR ---

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def parse_json_fields(data):
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}

@app.context_processor
def utility_processor():
    return dict(parse_json=parse_json_fields)

def get_semantic_score(user_answer, gold_standard_answer, category):
    # This function is now primarily called by tasks.py
    if not model:
        print("HATA: Hakem LLM modeli yüklenemedi.")
        return 0, {"reason": "Hakem LLM modeli yüklenemediği için skorlama yapılamadı.", "raw": "Model not loaded."}
    prompt = f"""
    Sen, bir hekimin vaka yanıtının '{category}' bölümünü değerlendiren, pragmatik ve deneyimli bir klinik uzmansın.
    Temel görevin, "Kullanıcı Yanıtı"nın, hastanın doğru ve güvenli bir şekilde tedavi edilmesini sağlayacak kadar YETERLİ olup olmadığını değerlendirmektir.
    Kullanıcının yanıtını "Altın Standart Yanıt" ile anlamsal olarak karşılaştır ve 0-100 arasında bir puan ver.

    Değerlendirme Kuralları:
    1. YETERLİLİK: Kullanıcının yanıtı, klinik olarak en önemli unsurları içeriyorsa tam puan ver. "sol/sağ" gibi pratik olmayan detay eksikliğinden puan KIRMA.
    2. TETKİK: 'Tetkik' kategorisinde, altın standart 'gerekmez' diyorsa, kullanıcının da 'yok' veya 'gerekmez' demesine tam puan ver. Gereksiz tetkik istemesinden puan kır.
    3. DOZAJ: 'Dozaj' kategorisinde, ilacın adından ziyade dozun, sıklığın ve uygulama şeklinin doğruluğuna odaklan.

    Yanıtını SADECE şu JSON formatında ver:
    {{ "score": <0-100 arası sayı>, "reasoning": "<1 cümlelik Türkçe gerekçe>" }}
    ---
    Altın Standart Yanıt ({category}): "{gold_standard_answer}"
    ---
    Kullanıcı Yanıtı ({category}): "{user_answer}"
    ---
    """
    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        score = int(result.get("score", 0))
        reasoning = result.get("reasoning", "Gerekçe alınamadı.")
        return score, {"reason": reasoning, "raw": response.text}
    except Exception as e:
        print(f"Gemini API hatası ({category}): {e}")
        return 0, {"reason": f"API Hatası: {e}", "raw": str(e)}

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Önce Flask-Login ile normal kullanıcı girişi yapılmış mı diye bak
        if not current_user.is_authenticated:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('giris'))

        # Kullanıcı giriş yapmışsa ama admin değilse veya admin oturumu açık değilse
        if not current_user.is_admin or not session.get('admin_authenticated'):
            flash("Yönetici yetkiniz yok veya yönetici oturumunuz açık değil.", "danger")
            return redirect(url_for('admin_login'))

        return f(*args, **kwargs)
    return decorated_function

def research_setup_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('giris'))
        # Eğer kullanıcı yönetici ise ve yönetici oturumu açıksa kontrolleri atla
        if current_user.is_admin and session.get('admin_authenticated'):
            return f(*args, **kwargs)
        if not current_user.has_consented:
            return redirect(url_for('consent'))
        if not current_user.profession or current_user.experience is None:
            return redirect(url_for('demographics'))
        return f(*args, **kwargs)
    return decorated_function

# --- 7. ANA UYGULAMA ROUTE'LARI ---

@app.route('/')
@login_required
@research_setup_required
def select_research():
    """Kullanıcının katılacağı araştırmayı seçtiği ana sayfa."""
    researches = Research.query.filter_by(is_active=True).order_by(Research.id.desc()).all()
    # DEĞİŞİKLİK:
    return render_template('select_research.html', researches=researches) # _new kaldırıldı


@app.route('/arastirma/<int:research_id>')
@login_required
@research_setup_required
def research_dashboard(research_id):
    """Araştırma için bir başlangıç ekranı sunar ve kullanıcıyı ilk vakaya yönlendirir."""
    research = db.session.get(Research, research_id)
    if not research:
        return redirect(url_for('select_research'))

    # Bu araştırmadaki tüm vakaların ID'lerini sıralı bir şekilde al
    all_case_ids = [case.id for case in Case.query.filter_by(research_id=research.id).order_by(Case.id).all()]
    if not all_case_ids:
        flash("Bu araştırma henüz vaka içermiyor.", "warning")
        return redirect(url_for('select_research'))
    
    # Kullanıcının bu araştırmada çözdüğü vakaların ID'lerini al
    completed_case_ids = {resp.case_id for resp in UserResponse.query.filter_by(user_id=current_user.id).join(Case).filter(Case.research_id == research_id).all()}

    # Çözülecek bir sonraki vakayı bul
    next_case_id = None
    for case_id in all_case_ids:
        if case_id not in completed_case_ids:
            next_case_id = case_id
            break

    # Eğer tüm vakalar çözüldüyse, doğrudan final raporuna yönlendir
    if next_case_id is None:
        return redirect(url_for('final_report', research_id=research_id))

    return render_template('research_dashboard.html', 
                           research=research, 
                           total_cases=len(all_case_ids),
                           completed_count=len(completed_case_ids),
                           next_case_id=next_case_id)


@app.route('/arastirma/<int:research_id>/tamamlandi')
@login_required
def completion_page(research_id):
    """Araştırma tamamlandığında gösterilecek teşekkür sayfası."""
    research = db.session.get(Research, research_id)
    # Bu dosyanın içeriğini bir önceki adımda düzeltmiştik
    return render_template('completion.html', research=research)

# --- 8. KULLANICI YÖNETİMİ ---

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    """Kullanıcı girişi ve kaydı (e-posta tabanlı)."""
    if current_user.is_authenticated:
        # Eğer yönetici ise yönetici paneline yönlendir
        if current_user.is_admin:
            # ESKİ: return redirect(url_for('admin_panel'))
            # YENİ ve DOĞRU:
            return redirect(url_for('admin_dashboard'))
        # Aksi halde araştırma seçim sayfasına yönlendir
        return redirect(url_for('select_research'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        if not email:
            flash('Lütfen bir e-posta adresi girin.', 'danger')
            return redirect(url_for('giris'))

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            db.session.add(user)
            db.session.commit()

        login_user(user, remember=True)

        # Eğer yönetici ise yönetici paneline yönlendir
        if user.is_admin:
            # ESKİ: return redirect(url_for('admin_panel'))
            # YENİ ve DOĞRU:
            return redirect(url_for('admin_dashboard'))

        # Onay kontrol et
        if not user.has_consented:
            return redirect(url_for('consent'))

        # Demografi kontrol et
        if not user.profession:
            return redirect(url_for('demographics'))

        return redirect(url_for('select_research'))

    # DEĞİŞİKLİK:
    return render_template('giris.html') # _new kaldırıldı

@app.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    if current_user.has_consented:
        return redirect(url_for('demographics'))
    
    if request.method == 'POST':
        current_user.has_consented = True
        db.session.commit()
        return redirect(url_for('demographics'))
        
    # DEĞİŞİKLİK:
    return render_template('consent.html') # _new kaldırıldı

@app.route('/demographics', methods=['GET', 'POST'])
@login_required
def demographics():
    if not current_user.has_consented:
        return redirect(url_for('consent'))
    if current_user.profession and current_user.experience is not None:
        return redirect(url_for('select_research'))
        
    if request.method == 'POST':
        current_user.profession = request.form['profession']
        current_user.experience = int(request.form['experience'])
        db.session.commit()
        return redirect(url_for('select_research'))
        
    # DEĞİŞİKLİK:
    return render_template('demographics.html') # _new kaldırıldı

@app.route('/logout')
@login_required
def logout():
    # Yönetici oturumunu da kapat
    session.pop('admin_authenticated', None)
    logout_user()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('giris'))

@app.route('/yanitlarim')
@login_required
def my_responses():
    responses = UserResponse.query.filter_by(user_id=current_user.id).order_by(UserResponse.created_at.desc()).all()
    # DEĞİŞİKLİK:
    return render_template('my_responses.html', responses=responses) # _new kaldırıldı

# --- 9. YÖNETİCİ PANELİ ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Yönetici paneli için şifreli giriş."""
    if current_user.is_authenticated and current_user.is_admin and session.get('admin_authenticated'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.is_admin and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session['admin_authenticated'] = True  # Yönetici oturumunu özel olarak işaretle
            flash('Yönetici paneline başarıyla giriş yapıldı.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Geçersiz yönetici e-posta veya şifre.', 'danger')
            return redirect(url_for('admin_login'))

    # GET isteği için, artık yöneticiye özel yeni giriş sayfasını göster
    # DEĞİŞİKLİK:
    return render_template('admin/admin_login.html') # _new kaldırıldı

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """
    Yönetici için ana kontrol paneli. Mevcut araştırmaları listeler
    ve genel istatistikleri sunar.
    (Eski admin_panel fonksiyonunun yeni adı ve şablon yolu.)
    """
    researches = Research.query.order_by(Research.id.desc()).all()
    stats = {
        'user_count': User.query.count(),
        'response_count': UserResponse.query.count(),
        'case_count': Case.query.count()
    }
    # --- DEĞİŞİKLİK: ---
    return render_template('admin/admin_dashboard.html', researches=researches, stats=stats) # _new kaldırıldı

@app.route('/admin/upload_csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    flash('CSV yükleme şimdilik devre dışı, lütfen JSON kullanın.', 'info')
    return redirect(url_for('admin_panel'))

# upload_json fonksiyonu (GET -> yeni şablon)
@app.route('/admin/upload_json', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_json():
    if request.method == 'POST':
        json_text = request.form.get('json_text')
        if not json_text:
            flash('Yüklenecek JSON verisi bulunamadı.', 'danger')
            return redirect(url_for('upload_json'))  # Yükleme sayfasına geri yönlendir
        
        try:
            data = json.loads(json_text)
        
            research_title = data.get('research_title')
            if not research_title:
                raise ValueError("JSON içinde 'research_title' alanı zorunludur.")

            if Research.query.filter_by(title=research_title).first():
                flash(f'"{research_title}" başlıklı bir araştırma zaten mevcut.', 'danger')
                return redirect(url_for('upload_json'))

            new_research = Research(
                title=research_title,
                description=data.get('research_description', ''),
                is_active=True
            )
            db.session.add(new_research)
            db.session.flush()

            cases_data = data.get('cases', [])
            if not cases_data or not isinstance(cases_data, list):
                raise ValueError("JSON içinde en az bir vaka ('cases' listesi) bulunmalıdır.")

            for case_content in cases_data:
                content = case_content if isinstance(case_content, dict) else {"raw": case_content}

                # LLM'leri ve altın standardı al
                llm_responses = content.get('llm_responses', {}) or {}
                gold_standard = content.get('gold_standard', {}) or content.get('gold_standard_response', {}) or {}

                case_llm_scores = {}
                for llm_name, llm_answers in llm_responses.items():
                    llm_question_scores = {}
                    total_score = 0
                    question_count = 0

                    for q_id, gold_answer in (gold_standard.items() if isinstance(gold_standard, dict) else []):
                        llm_answer = (llm_answers or {}).get(q_id, "")
                        # Basit eşleşme mantığı (daha sonra get_semantic_score ile değiştirilebilir)
                        try:
                            score = 100 if str(llm_answer).strip().lower() == str(gold_answer).strip().lower() else 0
                        except Exception:
                            score = 0
                        llm_question_scores[q_id] = score
                        total_score += score
                        question_count += 1

                    overall_score = (total_score / question_count) if question_count > 0 else 0
                    case_llm_scores[llm_name] = {"overall_score": round(overall_score, 2), "question_scores": llm_question_scores}

                new_case = Case(
                    research_id=new_research.id,
                    content=content,
                    llm_scores=case_llm_scores or None
                )
                db.session.add(new_case)
                
            db.session.commit()
            flash(f'"{research_title}" araştırması ve {len(cases_data)} vaka başarıyla yüklendi.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'JSON yüklenirken bir hata oluştu: {e}', 'danger')
            return redirect(url_for('upload_json'))
        
        # Başarılı yükleme sonrası ana yönetici paneline yönlendir
        return redirect(url_for('admin_dashboard')) 
    
    # DEĞİŞİKLİK:
    return render_template('admin/upload_research.html') # _new kaldırıldı

@app.route('/admin/export_csv')
@login_required
@admin_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    header = [
        'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil', 
        'vaka_id', 'vaka_baslik', 'yanit_suresi_saniye', 'yanit_tarihi',
        'kullanici_tani', 'kullanici_ayirici_tani', 'kullanici_tetkik', 
        'kullanici_ilac_grubu', 'kullanici_etken_madde', 'kullanici_doz_notlari',
        'tani_skoru', 'tetkik_skoru', 'tedavi_skoru', 'doz_skoru', 'final_skor',
        'tani_gerekcesi', 'tetkik_gerekcesi', 'tedavi_gerekcesi', 'doz_gerekcesi',
    ]
    writer.writerow(header)
    
    for resp in UserResponse.query.all():
        scores = resp.scores or {}
        scores_map = scores.get('scores', {}) if isinstance(scores, dict) else {}
        reasons = scores.get('reasons', {}) if isinstance(scores, dict) else {}
        answers = resp.answers or {}

        case_title = ''
        try:
            case_title = resp.case.content.get('title', '') if resp.case and resp.case.content else ''
        except Exception:
            case_title = ''

        row = [
            resp.id,
            resp.author.id if resp.author else None,
            resp.author.profession if resp.author else None,
            resp.author.experience if resp.author else None,
            resp.case.id if resp.case else None,
            case_title,
            resp.duration_seconds,
            resp.created_at.isoformat(),
            # Cevaplar (answers JSON içinden)
            answers.get('user_diagnosis', ''),
            answers.get('user_differential', ''),
            answers.get('user_tests', ''),
            answers.get('user_drug_class', ''),
            answers.get('user_active_ingredient', ''),
            answers.get('user_dosage_notes', ''),
            # Skorlar (scores JSON içinden)
            scores_map.get('diagnosis', ''),
            scores_map.get('tests', ''),
            scores_map.get('treatment', ''),
            scores_map.get('dosage', ''),
            scores.get('final_score', ''),
            # Gerekçeler / reasons
            reasons.get('diagnosis', ''), reasons.get('tests', ''),
            reasons.get('treatment', ''), reasons.get('dosage', ''),
        ]
        writer.writerow(row)
        
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=LLM_Research_Dataset.csv"})

@app.route('/admin/export/research/<int:research_id>')
@login_required
@admin_required
def export_research_csv(research_id):
    """Sadece belirli bir araştırmaya ait yanıt verilerini CSV olarak dışa aktarır."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Veri seti indirilecek araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_panel'))

    safe_title = "".join(c if c.isalnum() else "_" for c in (research.title or "research"))
    filename = f"Arastirma_{research.id}_{safe_title}_Veriseti.csv"

    # Araştırmaya ait yanıtları al
    responses = UserResponse.query.join(Case).filter(Case.research_id == research_id).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Temel başlıklar
    header = [
        'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil',
        'vaka_id', 'vaka_baslik', 'yanit_suresi_saniye', 'yanit_tarihi'
    ]

    # Dinamik soru başlıklarını ilk yanıttan al
    first_response_answers = responses[0].answers or {}
    question_headers = sorted(first_response_answers.keys())
    header.extend(question_headers)

    writer.writerow(header)

    for resp in responses:
        answers = resp.answers or {}
        try:
            case_title = resp.case.content.get('title', '') if resp.case and resp.case.content else ''
        except Exception:
            case_title = ''

        row = [
            resp.id,
            resp.author.id if resp.author else None,
            resp.author.profession if resp.author else None,
            resp.author.experience if resp.author else None,
            resp.case.id if resp.case else None,
            case_title,
            resp.duration_seconds,
            resp.created_at.isoformat()
        ]

        for q_key in question_headers:
            row.append(answers.get(q_key, ''))

        writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={filename}"})

# --- 10. VERİTABANI BAŞLATMA (SEEDING) ---

def seed_database():
    if Case.query.first() is not None:
        print("Veritabanı zaten veri içeriyor, seeding atlandı.")
        return

    print("Veritabanı boş, başlangıç vakaları ekleniyor...")
    initial_cases_data = [
        {
            "title": "Vaka 1: Huzursuz Bebek", "anamnesis": {"Hasta": "18 aylık, erkek.", "Şikayet": "Huzursuzluk, ateş ve sol kulağını çekiştirme."},
            "physical_exam": {"Bulgu": "Sol kulak zarında hiperemi ve bombeleşme."},
            "gold_standard_response": {"tanı": "Akut Otitis Media", "tetkik": "Ek tetkik gerekmez", "tedavi_plani": "Antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
            "chatgpt_response": {}, "gemini_response": {}, "deepseek_response": {}
        },
        {
            "title": "Vaka 2: Öksüren Çocuk", "anamnesis": {"Hasta": "4 yaşında, kız.", "Şikayet": "3 gündür ateş, öksürük ve hızlı nefes alma."},
            "physical_exam": {"Bulgu": "Sağ akciğer alt zonda krepitan raller."},
            "gold_standard_response": {"tanı": "Toplum Kökenli Pnömoni", "tetkik": "Akciğer Grafisi", "tedavi_plani": "Oral antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
            "chatgpt_response": {}, "gemini_response": {}, "deepseek_response": {}
        }
    ]
    
    try:
        # Varsayılan research: yoksa oluştur
        default_research = Research.query.first()
        if not default_research:
            default_research = Research(title="Seed Research", description="Seed ile oluşturulan varsayılan araştırma", is_active=True)
            db.session.add(default_research)
            db.session.flush()

        for case_data in initial_cases_data:
            content = {
                "title": case_data.get("title"),
                "anamnesis": case_data.get("anamnesis", {}),
                "physical_exam": case_data.get("physical_exam", {}),
                "chatgpt_response": case_data.get("chatgpt_response", {}),
                "gemini_response": case_data.get("gemini_response", {}),
                "deepseek_response": case_data.get("deepseek_response", {}),
                "gold_standard_response": case_data.get("gold_standard_response", {})
            }
            new_case = Case(
                research_id=default_research.id,
                content=content
            )
            db.session.add(new_case)
            db.session.flush()
            
            ref_answer = ReferenceAnswer(case_id=new_case.id, source='gold', content=case_data.get('gold_standard_response', {}))
            db.session.add(ref_answer)
            
        db.session.commit()
        print(f"{len(initial_cases_data)} başlangıç vakası eklendi.")
    except Exception as e:
        db.session.rollback()
        print(f"Seeding sırasında hata: {e}")

# --- 11. YÖNETİCİ API ROTALARI ---
@app.route('/api/case/<int:case_id>/add_llm_response', methods=['POST'])
@login_required
@admin_required
def add_llm_response_to_case(case_id):
    """Bir vakaya modal üzerinden LLM yanıtı ekler."""
    case = db.session.get(Case, case_id)
    if not case:
        return {"status": "error", "message": "Vaka bulunamadı."}, 404

    data = request.get_json(force=True, silent=True) or {}
    llm_name = data.get('llm_name')
    response_text = data.get('response_text')

    if not llm_name or not response_text:
        return {"status": "error", "message": "Eksik bilgi."}, 400

    # Güvenli kopyalama ve güncelleme
    new_content = case.content.copy() if isinstance(case.content, dict) else {}
    new_content.setdefault('llm_responses', {})
    new_content['llm_responses'][llm_name] = response_text
    case.content = new_content
    db.session.commit()

    return {"status": "success", "message": f'"{llm_name}" yanıtı eklendi.'}

@app.route('/admin/llms')
@login_required
@admin_required
def manage_llms():
    llms = LLM.query.order_by(LLM.name).all()
    # DEĞİŞİKLİK:
    return render_template('admin/manage_llms.html', llms=llms) # _new kaldırıldı

@app.route('/admin/llm/ekle', methods=['POST'])
@login_required
@admin_required
def add_llm():
    """Yeni bir LLM ekler."""
    name = (request.form.get('name') or '').strip()
    description = request.form.get('description')
    if not name:
        flash('Model adı boş olamaz.', 'danger')
        return redirect(url_for('manage_llms'))

    if LLM.query.filter_by(name=name).first():
        flash('Bu model zaten mevcut.', 'danger')
        return redirect(url_for('manage_llms'))

    new_llm = LLM(name=name, description=description)
    db.session.add(new_llm)
    db.session.commit()
    flash(f'"{name}" modeli başarıyla eklendi.', 'success')
    return redirect(url_for('manage_llms'))

@app.route('/admin/arastirmalar')
@login_required
@admin_required
def manage_researches():
    """Mevcut tüm araştırmaları listeleyen sayfa."""
    researches = Research.query.order_by(Research.id.desc()).all()
    # DEĞİŞİKLİK:
    return render_template('admin/manage_researches.html', researches=researches) # _new kaldırıldı


@app.route('/admin/arastirma/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def add_research():
    """Yeni bir araştırma eklemek için form ve işlevsellik."""
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = request.form.get('description')

        if not title:
            flash('Lütfen geçerli bir başlık girin.', 'danger')
            return render_template('admin/research_admin_dashboard.html', title=title, description=description)
        
        # Aynı başlıkta bir araştırma olup olmadığını kontrol et
        existing_research = Research.query.filter_by(title=title).first()
        if existing_research:
            flash('Bu başlıkta bir araştırma zaten mevcut. Lütfen farklı bir başlık kullanın.', 'danger')
            return render_template('admin/research_admin_dashboard.html', title=title, description=description) # _new kaldırıldı

        new_research = Research(
            title=title,
            description=description,
            is_active=True  # Yeni eklenen araştırmalar varsayılan olarak aktif olsun
        )
        db.session.add(new_research)
        db.session.commit()
        flash(f'"{title}" araştırması başarıyla oluşturuldu.', 'success')
        return redirect(url_for('manage_researches'))
    
    # GET request için boş formu göster
    # DEĞİŞİKLİK:
    return render_template('admin/research_admin_dashboard.html') # _new kaldırıldı


@app.route('/admin/arastirma/duzenle/<int:research_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_research(research_id):
    """Mevcut bir araştırmayı düzenlemek için form ve işlevsellik."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Düzenlenecek araştırma bulunamadı.', 'danger')
        return redirect(url_for('manage_researches'))

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = request.form.get('description')
        # Checkbox işaretliyse 'is_active' formda bulunur, değilse bulunmaz.
        is_active = 'is_active' in request.form

        # Başlık boşsa hata ver
        if not title:
            flash('Lütfen geçerli bir başlık girin.', 'danger')
            return render_template('admin/research_admin_dashboard.html', research=research)

        # Eğer başlık değiştiyse çakışma kontrolü
        if title != research.title:
            existing = Research.query.filter_by(title=title).first()
            if existing:
                flash('Bu başlıkta başka bir araştırma zaten mevcut. Lütfen farklı bir başlık kullanın.', 'danger')
                return render_template('admin/research_admin_dashboard.html', research=research) # _new kaldırıldı

        research.title = title
        research.description = description
        research.is_active = is_active
        
        db.session.commit()
        flash(f'"{research.title}" araştırması güncellendi.', 'success')
        return redirect(url_for('manage_researches'))

    cases = Case.query.filter_by(research_id=research.id).all()
    
    # DEĞİŞİKLİK:
    return render_template('admin/research_admin_dashboard.html', research=research, cases=cases) # _new kaldırıldı

@app.route('/admin/case/duzenle/<int:case_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_case(case_id):
    """Yönetici için vaka ve içindeki soruları düzenleme rotası."""
    case = db.session.get(Case, case_id)
    if not case:
        flash('Düzenlenecek vaka bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        # ...existing POST handling (güncelleme)...
        pass

    # DEĞİŞİKLİK:
    return render_template('admin/edit_case.html', case=case) # _new kaldırıldı

@app.route('/admin/research/<int:research_id>/add_case')
@login_required
@admin_required
def add_case_to_research(research_id):
    """Araştırmaya yeni bir vaka ekler."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    import datetime
    
    new_case_content = {
        "title": "Yeni Vaka (Başlığı Düzenleyin)",
        "case_id_internal": f"VAKA_{datetime.datetime.now().timestamp()}",
        "sections": [
            {"title": "Anamnez", "content": ""},
            {"title": "Fizik Muayene", "content": ""}
        ],
        # --- EKLENECEK SATIR ---
        "questions": [],
        # ---
        "gold_standard": {},
        "llm_responses": {}
    }

    new_case = Case(
        research_id=research_id,
        content=new_case_content
    )
    db.session.add(new_case)
    db.session.commit()

    flash(f"Yeni vaka başarıyla oluşturuldu.", "success")
    return redirect(url_for('research_admin_dashboard', research_id=research_id))

@app.route('/admin/research/<int:research_id>/dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def research_admin_dashboard(research_id):
    """Araştırma için yönetim paneli (ayarlar, vakalar, veri indirme)."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Düzenlenecek araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        research.title = request.form.get('title')
        research.description = request.form.get('description')
        research.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Araştırma ayarları güncellendi.', 'success')
        return redirect(url_for('research_admin_dashboard', research_id=research.id))
    
    cases = Case.query.filter_by(research_id=research.id).all()
    # DEĞİŞİKLİK:
    return render_template('admin/research_admin_dashboard.html', research=research, cases=cases) # _new kaldırıldı

@app.route('/admin/case/delete/<int:case_id>', methods=['POST'])
@login_required
@admin_required
def delete_case(case_id):
    case = db.session.get(Case, case_id)
    if not case:
        flash("Silinecek vaka bulunamadı.", "danger")
        return redirect(url_for('admin_panel'))
    
    research_id = case.research_id
    title = (case.content or {}).get('title', 'Başlıksız Vaka')

    # Önce bu vakaya ait tüm kullanıcı yanıtlarını sil
    UserResponse.query.filter_by(case_id=case_id).delete()
    
    # Sonra vakanın kendisini sil
    db.session.delete(case)
    db.session.commit()
    
    flash(f'"{title}" vakası ve ona ait tüm yanıtlar kalıcı olarak silindi.', 'success')
    return redirect(url_for('edit_research', research_id=research_id))

@app.route('/test_modern')
def modern_test_page():
    """Yeni layout ve Tailwind'in çalıştığını test eden sayfayı sunar."""
    return render_template('test_modern.html')


@app.route('/htmx_test', methods=['POST'])
def htmx_test():
    """HTMX butonunun isteğini karşılar ve bir HTML parçası döndürür."""
    return "<p class='text-green-600 font-semibold'>HTMX de başarıyla çalışıyor! Sayfa yenilenmedi.</p>"

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
@login_required
@research_setup_required
def case_detail(case_id):
    """Kullanıcının bir vakayı çözmesi için sayfa."""
    case = db.session.get(Case, case_id)
    if not case:
        flash("Vaka bulunamadı.", "danger")
        return redirect(url_for('select_research'))

    if request.method == 'POST':
        # Başlangıç zamanını session'dan al
        start_time = session.get(f'case_{case_id}_start_time', time.time())
        duration = int(time.time() - start_time)

        # Formdan gelen verileri ayır
        answers = {
            key: value for key, value in request.form.items() 
            if key not in ['duration_seconds', 'confidence_score', 'clinical_rationale']
        }

        # Yeni yanıt oluştur ve kaydet
        new_response = UserResponse(
            case_id=case.id,
            author=current_user,
            answers=answers,
            # --- YENİ VERİLER ---
            confidence_score=int(request.form.get('confidence_score', 75)),
            clinical_rationale=request.form.get('clinical_rationale', '').strip(),
            # ---
            duration_seconds=duration
        )
        db.session.add(new_response)
        db.session.commit()

        flash("Vakanız kaydedildi.", "success")

        # Sonraki vakaya yönlendir veya final rapor göster
        research = case.research
        answered_subq = db.session.query(UserResponse.case_id).filter_by(user_id=current_user.id).distinct()
        next_case = Case.query.filter(
            Case.research_id == research.id,
            Case.id.notin_(answered_subq)
        ).first()

        if next_case:
            session[f'case_{next_case.id}_start_time'] = time.time()
            return redirect(url_for('case_detail', case_id=next_case.id))
        else:
            return redirect(url_for('final_report', research_id=research.id))

    # GET isteği - vakaları göster
    session[f'case_{case_id}_start_time'] = session.get(f'case_{case_id}_start_time', time.time())
    # DEĞİŞİKLİK:
    return render_template('case.html', case=case) # _new kaldırıldı

@app.route('/arastirma/<int:research_id>/rapor')
@login_required
@research_setup_required
def final_report(research_id):
    """Kullanıcının bir araştırmadaki tüm yanıtlarını gösteren final sayfası."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Rapor görüntülenecek araştırma bulunamadı.", "danger")
        return redirect(url_for('select_research'))
    
    # Kullanıcının bu araştırmadaki tüm yanıtlarını, vaka sırasına göre çek
    responses = UserResponse.query.join(Case).filter(
        Case.research_id == research_id,
        UserResponse.user_id == current_user.id
    ).order_by(Case.id).all()

    # Modernize edilmiş yeni rapor şablonunu kullan
    # DEĞİŞİKLİK:
    return render_template('final_report.html', research=research, responses=responses) # _new kaldırıldı

# --- 12. KOMUT SATIRI TESTİ İÇİN ROTA ---
import click
from flask.cli import with_appcontext

@app.cli.command('test-routes')
@with_appcontext
def test_routes_command():
    """
    Uygulamadaki tüm basit GET rotalarını test eder ve durum kodlarını raporlar.
    """
    click.echo(click.style("Uygulama Rotaları Test Ediliyor...", fg='yellow', bold=True))

    client = app.test_client()
    links = [rule.rule for rule in app.url_map.iter_rules() if 'GET' in rule.methods and not rule.arguments]

    success_count = 0
    error_count = 0

    for link in sorted(links):
        try:
            response = client.get(link)
            if response.status_code == 200:
                click.echo(f"  ✅ {click.style(link, fg='green'):<50} {click.style('OK', fg='green')}")
                success_count += 1
            elif 300 <= response.status_code < 400:
                click.echo(f"  ↪️ {click.style(link, fg='cyan'):<50} {click.style(f'Yönlendirme ({response.status_code})', fg='cyan')}")
                success_count += 1
            else:
                click.echo(f"  ❌ {click.style(link, fg='red'):<50} {click.style(f'HATA ({response.status_code})', fg='red', bold=True)}")
                error_count += 1
        except Exception as e:
            click.echo(f"  💥 {click.style(link, fg='red'):<50} {click.style(f'KRİTİK HATA: {e}', fg='red', bold=True)}")
            error_count += 1

    click.echo("-" * 60)
    if error_count == 0:
        click.echo(click.style(f"Tüm {success_count} rota başarıyla test edildi!", fg='green', bold=True))
    else:
        click.echo(click.style(f"Test tamamlandı. Başarılı: {success_count}, Hatalı: {error_count}", fg='yellow'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # seed_database()  # Eğer init_db.py kullanıyorsanız burada çalıştırmayın
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
# test_app.py

import pytest
import json
from app import app, db, User, Research, Case, LLM, UserResponse

# --- DEĞİŞİKLİK BURADA ---
@pytest.fixture(scope='session')
def test_client():
    """
    Tüm test oturumu için TEK BİR test istemcisi ve temiz bir veritabanı oluşturur.
    """
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
    })

    testing_client = app.test_client()

    ctx = app.app_context()
    ctx.push()

    db.create_all()

    yield testing_client  

    db.session.remove()
    db.drop_all()
    ctx.pop()

def test_ana_sayfa_yonlendirmesi(test_client):
    """1. Test: Giriş yapmamış bir kullanıcı ana sayfaya gittiğinde giriş sayfasına yönlendirilir mi?"""
    response = test_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert 'Giriş Yap veya Hesap Oluştur' in response.data.decode('utf-8')

def test_kullanici_kayit_ve_onboarding_sureci(test_client):
    """2. Test: Yeni bir kullanıcı kaydolup onam ve demografi adımlarını tamamlayabilir mi?"""
    response = test_client.post('/giris', data={'email': 'test@kullanici.com'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Araştırma Katılım Onayı' in response.data.decode('utf-8')

    response = test_client.post('/consent', follow_redirects=True)
    assert response.status_code == 200
    assert 'Katılımcı Bilgileri' in response.data.decode('utf-8')

    response = test_client.post('/demographics', data={'profession': 'Pratisyen Hekim', 'experience': 5}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Mevcut Araştırmalar' in response.data.decode('utf-8')

    user = User.query.filter_by(email='test@kullanici.com').first()
    assert user is not None
    assert user.has_consented is True
    assert user.profession == 'Pratisyen Hekim'

def test_yonetici_giris_ve_panel_erisim(test_client):
    """3. Test: Yönetici doğru şifreyle giriş yapıp yönetici paneline erişebilir mi?"""
    from werkzeug.security import generate_password_hash
    admin_user = User(email='admin@test.com', is_admin=True, password_hash=generate_password_hash('123456'))
    db.session.add(admin_user)
    db.session.commit()
    
    response = test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Yönetici Ana Paneli' in response.data.decode('utf-8')

def test_yonetici_arastirma_yukleme_ve_yonetme(test_client):
    """4. Test: Yönetici yeni bir araştırmayı JSON ile yükleyebilir ve yönetebilir mi?"""
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    test_client.post('/admin/llm/ekle', data={'name': 'GPT-4'})
    llm = LLM.query.filter_by(name='GPT-4').first()
    assert llm is not None

    research_json = {
        "research_title": "Test Araştırması", "research_description": "Bu bir test araştırmasıdır.",
        "cases": [
            {"title": "Test Vaka 1", "sections": [{"title": "Anamnez", "content": "Test"}],
             "questions": [{"id": "q1", "type": "open-ended", "label": "Test Soru?"}],
             "gold_standard": {"q1": "Test Cevap"}}
        ]
    }
    response = test_client.post('/admin/upload_json', data={'json_text': json.dumps(research_json)}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Test Araştırması' in response.data.decode('utf-8')

    research = Research.query.filter_by(title='Test Araştırması').first()
    assert research is not None
    assert len(research.cases) == 1
    assert research.cases[0].content['title'] == 'Test Vaka 1'

def test_kullanici_vaka_cozum_akisi(test_client):
    """5. Test: Kullanıcı bir araştırmayı baştan sona tamamlayıp final raporunu görebilir mi?"""
    test_client.post('/giris', data={'email': 'test@kullanici.com'})
    
    research = Research.query.filter_by(title='Test Araştırması').first()
    response = test_client.get(f'/arastirma/{research.id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'Araştırmaya Başla' in response.data.decode('utf-8')

    case = research.cases[0]
    response = test_client.get(f'/case/{case.id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'Test Vaka 1' in response.data.decode('utf-8')
    assert 'Test Soru?' in response.data.decode('utf-8')

    response = test_client.post(f'/case/{case.id}', data={'q1': 'Kullanıcı Cevabı', 'duration_seconds': 120}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Araştırmayı başarıyla tamamladınız!' in response.data.decode('utf-8')
    assert 'Final Raporu' in response.data.decode('utf-8')

    user_response = UserResponse.query.first()
    assert user_response is not None
    assert user_response.case_id == case.id
    assert user_response.answers['q1'] == 'Kullanıcı Cevabı'

def test_yonetici_vaka_analiz_ekrani(test_client):
    """6. Test: Yönetici bir vaka için analiz ekranına erişebilir mi?"""
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    research = Research.query.filter_by(title='Test Araştırması').first()
    case = research.cases[0]

    response = test_client.get(f'/admin/case/{case.id}/review')
    assert response.status_code == 200
    assert 'Vaka Analiz' in response.data.decode('utf-8')
    assert 'Yanıt Sayısı' in response.data.decode('utf-8')
    assert 'Ortalama Süre' in response.data.decode('utf-8')

@app.route('/admin/case/<int:case_id>/review')
@login_required
@admin_required
def review_case(case_id):
    """Yönetici için vaka bazlı analiz, istatistik ve yönetim ekranı."""
    case = db.session.get(Case, case_id)
    if not case:
        flash("Analiz edilecek vaka bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Bu vakaya verilmiş tüm kullanıcı yanıtlarını çek
    responses = UserResponse.query.filter_by(case_id=case_id).all()
    all_llms = LLM.query.all()
    
    stats = {}
    if responses:
        try:
            # Veriyi Pandas DataFrame'e dönüştür
            data = []
            for r in responses:
                row = {'sure_saniye': getattr(r, 'duration_seconds', 0) or 0}
                if isinstance(getattr(r, 'answers', None), dict):
                    row.update(r.answers)
                data.append(row)
            
            df = pd.DataFrame(data)
            stats['response_count'] = len(df)
            stats['avg_duration'] = float(df['sure_saniye'].mean()) if 'sure_saniye' in df.columns else 0.0

            # Vakanın sorularını al
            questions = case.content.get('questions', []) if isinstance(case.content, dict) else []
            choice_question_stats = {}
            for q in questions:
                if q.get('type') == 'multiple-choice' and q.get('id') in df.columns:
                    choice_counts = df[q['id']].value_counts()
                    choice_question_stats[q.get('label', q.get('id'))] = {
                        'labels': choice_counts.index.tolist(),
                        'data': choice_counts.values.tolist()
                    }
            stats['choice_questions'] = choice_question_stats
        except Exception as e:
            print(f"Stats hesaplama hatası: {e}")
            stats = {'response_count': len(responses), 'avg_duration': 0, 'choice_questions': {}}

    return render_template('case_review.html', 
                           case=case, 
                           responses=responses, 
                           all_llms=all_llms,
                           stats=stats)

@app.route('/admin/research/<int:research_id>/stats')
@login_required
@admin_required
def research_dashboard_admin(research_id):
    """Araştırma seviyesinde ileri istatistik paneli."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    responses = UserResponse.query.join(Case).filter(Case.research_id == research_id).all()
    
    if not responses:
        flash("Bu araştırma için henüz veri yok.", "info")
        return redirect(url_for('research_admin_dashboard', research_id=research_id))

    try:
        # Veri çerçevesi oluştur
        rows = []
        for r in responses:
            author = getattr(r, 'author', None)
            row = {
                'unvan': getattr(author, 'profession', None),
                'deneyim': getattr(author, 'experience', None) or 0,
                'sure_saniye': getattr(r, 'duration_seconds', None) or 0,
                'confidence_score': getattr(r, 'confidence_score', None) or 0,
                'clinical_rationale': getattr(r, 'clinical_rationale', None) or '',
            }
            if isinstance(getattr(r, 'answers', None), dict):
                row.update(r.answers)
            rows.append(row)

        df = pd.DataFrame(rows) if rows else pd.DataFrame()

        stats = {}

        # 1. Temel istatistikler
        stats['total_responses'] = len(responses)
        stats['avg_experience'] = float(df['deneyim'].mean()) if 'deneyim' in df.columns else 0.0
        stats['avg_duration'] = float(df['sure_saniye'].mean()) if 'sure_saniye' in df.columns else 0.0
        stats['avg_confidence'] = float(df['confidence_score'].mean()) if 'confidence_score' in df.columns else 0.0

        # 2. Meslek dağılımı
        if not df.empty and 'unvan' in df.columns:
            profession_counts = df['unvan'].fillna('Bilinmiyor').value_counts()
            stats['profession_chart'] = {
                'labels': profession_counts.index.tolist(),
                'data': profession_counts.values.tolist()
            }
        else:
            stats['profession_chart'] = {'labels': [], 'data': []}

        # 3. Unvanlara göre ortalama güven skoru
        if not df.empty and 'unvan' in df.columns and 'confidence_score' in df.columns:
            confidence_by_profession = df.groupby('unvan')['confidence_score'].mean().sort_values(ascending=False)
            stats['confidence_by_profession'] = {
                'labels': confidence_by_profession.index.tolist(),
                'data': [float(v) for v in confidence_by_profession.values.tolist()]
            }
        else:
            stats['confidence_by_profession'] = {'labels': [], 'data': []}

        # 4. Deneyim yılı vs. karar süresi (deneyim kategorilerine göre)
        if not df.empty and 'deneyim' in df.columns and 'sure_saniye' in df.columns:
            # Deneyim kategorileri: 0-5, 5-10, 10-15, 15+
            def categorize_experience(exp):
                if exp < 5:
                    return '0-5 yıl'
                elif exp < 10:
                    return '5-10 yıl'
                elif exp < 15:
                    return '10-15 yıl'
                else:
                    return '15+ yıl'

            df['exp_category'] = df['deneyim'].apply(categorize_experience)
            avg_duration_by_exp = df.groupby('exp_category')['sure_saniye'].mean()
            
            # Sıralama
            category_order = ['0-5 yıl', '5-10 yıl', '10-15 yıl', '15+ yıl']
            avg_duration_by_exp = avg_duration_by_exp.reindex([c for c in category_order if c in avg_duration_by_exp.index])
            
            stats['experience_vs_duration'] = {
                'labels': avg_duration_by_exp.index.tolist(),
                'data': [float(v) for v in avg_duration_by_exp.values.tolist()]
            }
        else:
            stats['experience_vs_duration'] = {'labels': [], 'data': []}

        # 5. Güven skoru dağılımı (histogram-style)
        if not df.empty and 'confidence_score' in df.columns:
            confidence_bins = [0, 25, 50, 75, 100]
            confidence_labels = ['0-25', '25-50', '50-75', '75-100']
            df['confidence_bin'] = pd.cut(df['confidence_score'], bins=confidence_bins, labels=confidence_labels, include_lowest=True)
            confidence_dist = df['confidence_bin'].value_counts().sort_index()
            
            stats['confidence_distribution'] = {
                'labels': confidence_dist.index.astype(str).tolist(),
                'data': confidence_dist.values.tolist()
            }
        else:
            stats['confidence_distribution'] = {'labels': [], 'data': []}

    except Exception as e:
        print(f"İstatistik hesaplama hatası: {e}")
        stats = {
            'total_responses': len(responses),
            'avg_experience': 0,
            'avg_duration': 0,
            'avg_confidence': 0,
            'profession_chart': {'labels': [], 'data': []},
            'confidence_by_profession': {'labels': [], 'data': []},
            'experience_vs_duration': {'labels': [], 'data': []},
            'confidence_distribution': {'labels': [], 'data': []}
        }

    return render_template('admin/research_stats.html', research=research, stats=stats) # _new kaldırıldı

@app.route('/admin/research/<int:research_id>/analytics')
@login_required
@admin_required
def scientific_analytics(research_id):
    """Bilimsel analiz ve karşılaştırma paneli - İnsan vs. LLM performansı."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Bu araştırmadaki tüm kullanıcı yanıtlarını çek
    responses = UserResponse.query.join(Case).filter(Case.research_id == research_id).all()
    if not responses:
        flash("Bu araştırma için henüz analiz edilecek veri bulunmuyor.", "info")
        return redirect(url_for('research_admin_dashboard', research_id=research_id))

    try:
        # Pandas ile veri analizi
        data = []
        for r in responses:
            user_score = r.scores.get('overall_score', 0) if r.scores else 0
            row = {
                'unvan': getattr(r.author, 'profession', 'Bilinmiyor'),
                'deneyim': getattr(r.author, 'experience', 0) or 0,
                'kullanici_skor': user_score,
                'guven_skoru': r.confidence_score or 0
            }
            
            # Her LLM'in skorunu satıra ekle
            if r.case and r.case.llm_scores:
                for llm_name, scores in r.case.llm_scores.items():
                    row[f'llm_skor_{llm_name}'] = scores.get('overall_score', 0) if isinstance(scores, dict) else 0
            
            data.append(row)

        df = pd.DataFrame(data)

        analytics = {}

        # 1. Genel Performans Karşılaştırması (İnsan vs. LLM'ler)
        performance_labels = ['İnsan (Ortalama)']
        performance_data = [round(df['kullanici_skor'].mean(), 2)]
        
        llm_cols = [col for col in df.columns if col.startswith('llm_skor_')]
        for col in sorted(llm_cols):
            llm_name = col.replace('llm_skor_', '')
            performance_labels.append(llm_name)
            performance_data.append(round(df[col].mean(), 2))

        analytics['overall_performance'] = {
            'labels': performance_labels,
            'data': performance_data
        }

        # 2. Unvanlara Göre İnsan Performansı
        if 'unvan' in df.columns:
            perf_by_profession = df.groupby('unvan')['kullanici_skor'].mean().sort_values(ascending=False)
            analytics['performance_by_profession'] = {
                'labels': perf_by_profession.index.tolist(),
                'data': [round(float(x), 2) for x in perf_by_profession.values.tolist()]
            }
        else:
            analytics['performance_by_profession'] = {'labels': [], 'data': []}

        # 3. Güven vs. Gerçek Performans (Korelasyon)
        if 'guven_skoru' in df.columns and 'kullanici_skor' in df.columns:
            if not df['guven_skoru'].isnull().all() and not df['kullanici_skor'].isnull().all():
                correlation = float(df['guven_skoru'].corr(df['kullanici_skor']))
                analytics['confidence_correlation'] = round(correlation, 3)
            else:
                analytics['confidence_correlation'] = None
        else:
            analytics['confidence_correlation'] = None

        # 4. İstatistiksel Özetler
        analytics['summary'] = {
            'total_responses': len(responses),
            'avg_human_score': round(float(df['kullanici_skor'].mean()), 2),
            'avg_confidence': round(float(df['guven_skoru'].mean()), 2),
            'avg_experience': round(float(df['deneyim'].mean()), 1)
        }

    except Exception as e:
        print(f"Bilimsel analiz hatası: {e}")
        analytics = {
            'overall_performance': {'labels': [], 'data': []},
            'performance_by_profession': {'labels': [], 'data': []},
            'confidence_correlation': None,
            'summary': {'total_responses': len(responses), 'avg_human_score': 0, 'avg_confidence': 0, 'avg_experience': 0}
        }

    return render_template('admin/scientific_analytics.html', research=research, analytics=analytics)