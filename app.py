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
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, Response, session  # session eklendi
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import google.generativeai as genai
from redis import Redis
from rq import Queue
from rq.job import Job
from werkzeug.security import generate_password_hash, check_password_hash  # Eklendi
import pandas as pd
import datetime

# --- 2. UYGULAMA KURULUMU VE YAPILANDIRMA ---

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

# Projenin ana dizinini belirle
basedir = os.path.abspath(os.path.dirname(__file__))

# Flask uygulamasını başlat
app = Flask(__name__)

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
    responses = db.relationship('UserResponse', backref='author', lazy=True)

class Case(db.Model):
    """Vaka içeriğini JSON olarak tutan ve bir Research'e bağlı olan model."""
    id = db.Column(db.Integer, primary_key=True)
    # Hangi araştırmaya ait olduğu (zorunlu)
    research_id = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)

    # Bütün vaka içeriği (başlık, anamnez, fizik muayene, LLM yanıtları, gold standard vb.) JSON içinde saklanır
    content = db.Column(db.JSON, nullable=False)

    responses = db.relationship('UserResponse', backref='case', lazy=True)
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
    """Kullanıcıların vakalara verdiği yanıtları ve skorları saklayan model (esnek JSON)."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Yeni: Kullanıcının forma verdiği tüm yanıtlar burada JSON olarak tutulacak
    # Örnek: {"user_diagnosis": "...", "user_differential": "...", ...}
    answers = db.Column(db.JSON, nullable=False)

    duration_seconds = db.Column(db.Integer, nullable=True)
    job_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Puanlama sonuçları JSON içinde saklanır:
    # Örnek: {"final_score": 90, "scores": {"diagnosis": 90, "tests": 80, "treatment": 85, "dosage": 95}, "reasons": {"diagnosis": "...", ...}}
    scores = db.Column(db.JSON, nullable=True)

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
    researches = Research.query.filter_by(is_active=True).all()
    # Henüz aktif araştırma yoksa yöneticiyi uyar
    if not researches and current_user.is_admin:
        flash("Sistemde aktif araştırma bulunmuyor. Lütfen yönetici panelinden vaka yükleyin.", "warning")
    return render_template('select_research.html', researches=researches)


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
    return render_template('completion.html', research=research)

# --- 8. KULLANICI YÖNETİMİ ---

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if current_user.is_authenticated and not current_user.is_admin:
        return redirect(url_for('select_research'))
    if current_user.is_authenticated and current_user.is_admin and session.get('admin_authenticated'):
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        if not email:
            flash('Lütfen geçerli bir e-posta adresi girin.', 'danger')
            return redirect(url_for('giris'))

        user = User.query.filter_by(email=email).first()

        if not user:
            is_first_user_admin = User.query.count() == 0
            user = User(email=email, is_admin=False)
            db.session.add(user)
            db.session.commit()
            flash('Araştırmamıza hoş geldiniz! Lütfen devam edin.', 'success')

        # Eğer bulunan kullanıcı bir admin ise, bu sayfadan giriş yapmasına izin verme
        if user.is_admin:
            flash('Yönetici girişi için lütfen /admin/login sayfasını kullanın.', 'warning')
            return redirect(url_for('admin_login'))

        login_user(user, remember=True)

        if not user.has_consented:
            return redirect(url_for('consent'))
        if not user.profession or user.experience is None:
            return redirect(url_for('demographics'))

        return redirect(url_for('select_research'))

    # --- SADECE BU SATIRI GÜNCELLİYORUZ ---
    # Eski: return render_template('giris.html')
    # Yeni:
    return render_template('giris_new.html')

@app.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    if current_user.has_consented:
        return redirect(url_for('demographics'))
    
    if request.method == 'POST':
        current_user.has_consented = True
        db.session.commit()
        return redirect(url_for('demographics'))
        
    return render_template('consent.html')

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
        
    return render_template('demographics.html')

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
    return render_template('my_responses.html', responses=responses)

# --- 9. YÖNETİCİ PANELİ ---
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
    return render_template('admin/admin_dashboard.html', researches=researches, stats=stats)

@app.route('/admin/upload_csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    flash('CSV yükleme şimdilik devre dışı, lütfen JSON kullanın.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_json', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_json():
    # POST metodu ile form gönderildiğinde çalışacak kısım
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
                new_case = Case(
                    research_id=new_research.id,
                    content=content
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
    
    # GET metodu ile sayfa ilk kez açıldığında, yükleme formunu göster
    return render_template('upload_research.html')

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

    if not responses:
        flash(f'"{research.title}" araştırması için henüz hiç yanıt verisi bulunmuyor.', 'info')
        return redirect(url_for('research_admin_dashboard', research_id=research_id))

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
    """Sistemdeki tüm LLM'leri listeler."""
    llms = LLM.query.order_by(LLM.id.desc()).all()
    return render_template('manage_llms.html', llms=llms)

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
    return render_template('manage_researches.html', researches=researches)


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
            return render_template('add_edit_research.html', title=title, description=description)
        
        # Aynı başlıkta bir araştırma olup olmadığını kontrol et
        existing_research = Research.query.filter_by(title=title).first()
        if existing_research:
            flash('Bu başlıkta bir araştırma zaten mevcut. Lütfen farklı bir başlık kullanın.', 'danger')
            return render_template('add_edit_research.html', title=title, description=description)

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
    return render_template('add_edit_research.html')


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
            return render_template('add_edit_research.html', research=research)

        # Eğer başlık değiştiyse çakışma kontrolü
        if title != research.title:
            existing = Research.query.filter_by(title=title).first()
            if existing:
                flash('Bu başlıkta başka bir araştırma zaten mevcut. Lütfen farklı bir başlık kullanın.', 'danger')
                return render_template('add_edit_research.html', research=research)

        research.title = title
        research.description = description
        research.is_active = is_active
        
        db.session.commit()
        flash(f'"{research.title}" araştırması güncellendi.', 'success')
        return redirect(url_for('manage_researches'))

    # --- DEĞİŞİKLİK: Araştırmaya ait vakaları da çekip şablona gönderiyoruz ---
    cases = Case.query.filter_by(research_id=research.id).all()
    
    # GET request için dolu formu ve vaka listesini göster
    return render_template('add_edit_research.html', research=research, cases=cases)

@app.route('/admin/case/duzenle/<int:case_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_case(case_id):
    """Yönetici için vaka ve içindeki soruları düzenleme rotası."""
    case = db.session.get(Case, case_id)
    if not case:
        flash('Vaka bulunamadı.', 'danger')
        return redirect(url_for('manage_researches'))

    if request.method == 'POST':
        try:
            # Mevcut content güvenli şekilde kopyalanır / oluşturulur
            current_content = case.content if isinstance(case.content, dict) else {}
            new_content = current_content.copy()

            # Basit alan güncellemeleri
            title = request.form.get('title')
            if title is not None:
                new_content['title'] = title.strip()

            # Sorular formundan gelen verileri işle
            question_ids = request.form.getlist('question_id')
            question_types = request.form.getlist('question_type')
            question_labels = request.form.getlist('question_label')
            question_options = request.form.getlist('question_options')  # multiline textarea ile gönderilebilir

            questions = []
            count = max(len(question_ids), len(question_types), len(question_labels))
            for i in range(count):
                qid = question_ids[i] if i < len(question_ids) else f"q{i+1}"
                qtype = question_types[i] if i < len(question_types) else (question_types[-1] if question_types else 'open-ended')
                qlabel = question_labels[i] if i < len(question_labels) else ''
                question = {"id": qid, "type": qtype, "label": qlabel}

                if qtype == 'multiple-choice':
                    opts_text = question_options[i] if i < len(question_options) else ''
                    opts = [opt.strip() for opt in opts_text.splitlines() if opt.strip()]
                    question['options'] = opts

                questions.append(question)

            if questions:
                new_content['questions'] = questions

            # --- YENİ EKLENEN KISIM: LLM Yanıtlarını Güncelle ---
            llm_responses = new_content.get('llm_responses', {})
            llm_responses['chatgpt'] = request.form.get('llm_chatgpt', '')
            llm_responses['gemini'] = request.form.get('llm_gemini', '')
            llm_responses['deepseek'] = request.form.get('llm_deepseek', '')
            new_content['llm_responses'] = llm_responses
            # --- YENİ KISIM BİTTİ ---
            
            case.content = new_content
            db.session.commit()
            flash(f'Vaka "{case.content.get("title","(başlıksız)")}" güncellendi.', 'success')
            return redirect(url_for('research_admin_dashboard', research_id=case.research_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Vaka düzenlenirken hata: {e}")
            flash(f'Vaka güncellenirken hata oluştu: {e}', 'danger')
            return redirect(url_for('manage_researches'))

    # GET: düzenleme formunu göster
    return render_template('edit_case.html', case=case)

@app.route('/admin/research/<int:research_id>/add_case')
@login_required
@admin_required
def add_case_to_research(research_id):
    """Bir araştırmaya arayüzden yeni, boş bir vaka ekler."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Vaka eklenecek araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_panel'))

    # Boş bir vaka için varsayılan içerik yapısı
    new_case_content = {
        "title": "Yeni Vaka (Başlığı Düzenleyin)",
        "case_id_internal": f"VAKA_{int(datetime.datetime.now().timestamp())}",
        "sections": [
            {"title": "Anamnez", "content": ""},
            {"title": "Fizik Muayene", "content": ""}
        ],
        "questions": [],
        "gold_standard": {},
        "llm_responses": {
            "chatgpt": "",
            "gemini": "",
            "deepseek": ""
        }
    }

    new_case = Case(
        research_id=research.id,
        content=new_case_content
    )
    db.session.add(new_case)
    db.session.commit()
    
    flash("Yeni vaka oluşturuldu. Lütfen detaylarını düzenleyin.", "success")
    return redirect(url_for('edit_case', case_id=new_case.id))

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
        # Araştırma ayarlarını güncelle
        research.title = (request.form.get('title') or '').strip()
        research.description = request.form.get('description')
        research.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Araştırma ayarları güncellendi.', 'success')
        return redirect(url_for('research_admin_dashboard', research_id=research.id))

    cases = Case.query.filter_by(research_id=research.id).all()
    return render_template('admin/research_admin_dashboard.html', research=research, cases=cases)

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
    return "<p class='text-green-600 font-semibold fade-in'>HTMX de başarıyla çalışıyor! Sayfa yenilenmedi.</p>"

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
@login_required
@research_setup_required
def case_detail(case_id):
    """Kullanıcının bir vakayı çözdüğü dinamik vaka ekranı."""
    case = db.session.get(Case, case_id)
    if not case:
        flash("Vaka bulunamadı.", "danger")
        return redirect(url_for('select_research'))
    
    research_id = case.research_id

    # Yöneticiler için kısıtlamaları kaldır
    if not current_user.is_admin:
        existing_response = UserResponse.query.filter_by(user_id=current_user.id, case_id=case_id).first()
        if existing_response:
            flash("Bu vakayı daha önce zaten çözdünüz.", "info")
            return redirect(url_for('research_dashboard', research_id=research_id))

    # İlerleme çubuğu için verileri hazırla
    all_case_ids = [c.id for c in Case.query.filter_by(research_id=research_id).order_by(Case.id).all()]
    completed_case_ids = {resp.case_id for resp in UserResponse.query.filter_by(user_id=current_user.id).join(Case).filter(Case.research_id == research_id).all()}
    try:
        current_case_index = all_case_ids.index(case_id) + 1
    except ValueError:
        return redirect(url_for('research_dashboard', research_id=research_id))
    total_cases = len(all_case_ids)

    if request.method == 'POST':
        # Kullanıcı yönetici ise yanıt kaydetme, sadece yönlendir
        if current_user.is_admin:
            flash("Yönetici modunda yanıt kaydedilemez.", "info")
            return redirect(url_for('research_dashboard', research_id=research_id))

        answers = {key: value for key, value in request.form.items() if key != 'duration_seconds'}
        try:
            duration_val = int(request.form.get('duration_seconds', 0))
        except (ValueError, TypeError):
            duration_val = None

        new_response = UserResponse(
            case_id=case.id,
            author=current_user,
            answers=answers,
            duration_seconds=duration_val
        )
        db.session.add(new_response)
        db.session.commit()

        completed_case_ids.add(case_id)
        next_case_id = None
        for cid in all_case_ids:
            if cid not in completed_case_ids:
                next_case_id = cid
                break
        
        if next_case_id:
            return redirect(url_for('case_detail', case_id=next_case_id))
        else:
            flash("Araştırmayı başarıyla tamamladınız! İşte sonuçlarınız.", "success")
            return redirect(url_for('final_report', research_id=research_id))

    return render_template('case.html', 
                           case=case, 
                           current_case_index=current_case_index, 
                           total_cases=total_cases)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # seed_database()  # Eğer init_db.py kullanıyorsanız burada çalıştırmayın
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))