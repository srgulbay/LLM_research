# -*- coding: utf-8 -*-
"""
LLM_Research - Bilimsel Veri Toplama Platformu (Sürüm 3.0)
Bu sürüm, asenkron puanlama için Redis/RQ kullanır,
Railway (PostgreSQL) ile yerel (SQLite) geliştirmeyi destekler,
dinamik skor takibi, RESTful API, gelişmiş analitik özellikleri içerir.
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
from flask_migrate import Migrate 
from flask_cors import CORS

from dotenv import load_dotenv
import google.generativeai as genai
from redis import Redis
from rq import Queue
from rq.job import Job
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

from analysis import get_research_responses_df, calculate_participant_stats, calculate_scientific_analytics

# --- 2. UYGULAMA KURULUMU VE YAPILANDIRMA ---

app = Flask(__name__)

# zip fonksiyonunu Jinja ortamına ekle
app.jinja_env.globals['zip'] = zip

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

# --- 3. EKLENTİLERİ BAŞLATMA (DB, LOGIN, REDIS, CORS) ---

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# CORS yapılandırması - API endpoint'leri için
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5000", "*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

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

    if not api_key:
        print("UYARI: GEMINI_API_KEY bulunamadı. .env dosyanızı kontrol edin.")
    else:
        # 'import genai' satırı kaldırıldı — başta import edilen `genai` kullanılıyor
        genai.configure(api_key=api_key)

        # Mevcut modelleri listeleyip uygun bir Gemini modeli seçmeye çalış
        available_models = []
        try:
            models_list = genai.list_models()  # client'ın sunduğu listeleme fonksiyonunu kullan
            for m in models_list:
                # m dict ya da obj olabilir; name/ID almaya çalış
                name = None
                if isinstance(m, dict):
                    name = m.get('name') or m.get('id')
                else:
                    name = getattr(m, 'name', None) or getattr(m, 'id', None) or str(m)
                if name:
                    available_models.append(name)
        except Exception as e:
            print(f"UYARI: Modeller listelenemedi: {e}")

        print("Bulunan modeller:", available_models)

        # Tercih edilen model adları (sıralı)
        preferred_candidates = [
            "gemini-1.5-flash",
            "gemini-1.5",
            "gemini-pro",
            "models/gemini-1.5-flash",
            "models/gemini-pro"
        ]

        chosen_model = None
        for cand in preferred_candidates:
            for m in available_models:
                if cand in m:
                    chosen_model = m
                    break
            if chosen_model:
                break

        if not chosen_model and available_models:
            chosen_model = available_models[0]

        if not chosen_model:
            print("UYARI: Uygun bir model bulunamadı; model objesi oluşturulmayacak.")
            model = None
        else:
            print(f"Seçilen model: {chosen_model}")
            model = genai.GenerativeModel(
                model_name=chosen_model,
                generation_config={"response_mime_type": "application/json"}
            )
            print(f"Gemini API ({chosen_model}) başarıyla yapılandırıldı.")
except Exception as e:
    print(f"HATA: Gemini API yapılandırılamadı: {e}")
    model = None

# --- 5. VERİTABANI MODELLERİ ---
class LLM(db.Model):
    """Sistemde kullanılacak yapay zeka modellerini saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<LLM {self.name}>'

class SystemSettings(db.Model):
    """Sistem ayarlarını saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'

class User(UserMixin, db.Model):
    """Kullanıcı bilgilerini (demografi dahil) saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=True)  # Opsiyonel kullanıcı adı
    email = db.Column(db.String(150), unique=True, nullable=True)  # Artık opsiyonel
    anonymous_id = db.Column(db.String(50), unique=True, nullable=True)  # Anonim kullanıcılar için
    password_hash = db.Column(db.String(256), nullable=True)  # Yönetici şifreleri için
    is_admin = db.Column(db.Boolean, default=False)
    is_anonymous = db.Column(db.Boolean, default=False)  # Anonim kullanıcı kontrolü
    profession = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    has_consented = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    responses = db.relationship('UserResponse', back_populates='author', lazy=True)

    def __repr__(self):
        if self.is_anonymous:
            return f'<User Anonymous:{self.anonymous_id}>'
        return f'<User {self.email or self.username}>'
    
    def get_display_name(self):
        """Kullanıcının görüntülenecek adını döndürür."""
        if self.is_anonymous:
            return f"Anonim Kullanıcı ({self.anonymous_id[:8]})"
        return self.username or self.email or "Kullanıcı"

class Research(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    cases = db.relationship('Case', backref='research', lazy=True)

    def __repr__(self):
        return f'<Research {self.title}>'

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    research_id = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    content = db.Column(db.JSON, nullable=True)
    llm_scores = db.Column(db.JSON, nullable=True)
    
    responses = db.relationship('UserResponse', back_populates='case', lazy=True)
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
    scores = db.Column(db.JSON) # Asenkron puanlama sonuçları
    duration_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    case = db.relationship('Case', back_populates='responses')
    author = db.relationship('User', back_populates='responses')

    def __repr__(self):
        return f'<UserResponse {self.id} - Case {self.case_id} - User {self.user_id}>'

class ResearchFinding(db.Model):
    """Araştırma bulgularını akademik format halinde saklar."""
    id = db.Column(db.Integer, primary_key=True)
    research_id = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    finding_type = db.Column(db.String(50), nullable=False)  # 'table', 'chart', 'text', 'statistical_test'
    content = db.Column(db.JSON, nullable=False)  # Tablo verileri, grafik config, metin içeriği
    order_index = db.Column(db.Integer, default=0)  # Sıralama için
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
                          onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    research = db.relationship('Research', backref='findings', lazy=True)
    
    def __repr__(self):
        return f'<ResearchFinding {self.id} - {self.title}>'

# --- 6. YARDIMCI FONKSİYONLAR VE DECORATOR'LAR ---

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def utility_processor():
    # Mevcut parse_json fonksiyonunu koruyun
    def parse_json_fields(data):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}

    # Yıl bilgisini UTC bazlı olarak ekleyin
    return dict(
        parse_json=parse_json_fields,
        current_year=datetime.datetime.now(datetime.timezone.utc).year
    )

def get_semantic_score(user_answer, gold_standard_answer, category):
    """
    İki metin arasında anlamsal puanlama yapar. 
    Bu fonksiyon artık doğrudan 'tasks.py' tarafından çağrılmaktadır.
    """
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
        if not current_user.is_authenticated:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('giris'))
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
        if current_user.is_admin and session.get('admin_authenticated'):
            return f(*args, **kwargs)
        if not current_user.has_consented:
            return redirect(url_for('consent'))
        if not current_user.profession or current_user.experience is None:
            return redirect(url_for('demographics'))
        return f(*args, **kwargs)
    return decorated_function

# --- 6. YARDIMCI FONKSİYONLAR ---

def is_maintenance_mode():
    """Bakım modunun açık olup olmadığını kontrol eder."""
    setting = SystemSettings.query.filter_by(key='maintenance_mode').first()
    return setting and setting.value == 'true'

def get_maintenance_message():
    """Bakım modu mesajını getirir."""
    setting = SystemSettings.query.filter_by(key='maintenance_message').first()
    return setting.value if setting else 'Sistem bakımda. Lütfen daha sonra tekrar deneyin.'

# --- 7. ANA UYGULAMA ROUTE'LARI ---

@app.before_request
def check_maintenance_mode():
    """Her istekten önce bakım modunu kontrol eder."""
    # İzin verilen yollar (admin ve statik dosyalar)
    allowed_paths = ['/admin/login', '/admin/maintenance', '/static/', '/admin/logout']
    
    # Eğer yol izin verilenlerden biri ise veya statik dosya ise atla
    if any(request.path.startswith(path) for path in allowed_paths):
        return None
    
    # Bakım modu aktifse ve kullanıcı admin değilse
    if is_maintenance_mode():
        if not current_user.is_authenticated or not current_user.is_admin:
            return render_template('maintenance.html', 
                                 message=get_maintenance_message()), 503

@app.route('/')
@login_required
@research_setup_required
def select_research():
    """Kullanıcının katılacağı araştırmayı seçtiği ana sayfa."""
    researches = Research.query.filter_by(is_active=True).order_by(Research.id.desc()).all()
    return render_template('select_research.html', researches=researches)


@app.route('/arastirma/<int:research_id>')
@login_required
@research_setup_required
def research_dashboard(research_id):
    """Araştırma için bir başlangıç ekranı sunar ve kullanıcıyı ilk vakaya yönlendirir."""
    research = db.session.get(Research, research_id)
    if not research:
        return redirect(url_for('select_research'))

    all_case_ids = [case.id for case in Case.query.filter_by(research_id=research.id).order_by(Case.id).all()]
    if not all_case_ids:
        flash("Bu araştırma henüz vaka içermiyor.", "warning")
        return redirect(url_for('select_research'))
    
    completed_case_ids = {resp.case_id for resp in UserResponse.query.filter_by(user_id=current_user.id).join(Case).filter(Case.research_id == research_id).all()}

    next_case_id = None
    for case_id in all_case_ids:
        if case_id not in completed_case_ids:
            next_case_id = case_id
            break

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
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        if not current_user.has_consented:
            return redirect(url_for('consent'))
        if not current_user.profession or current_user.experience is None:
            return redirect(url_for('demographics'))
        return redirect(url_for('select_research'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').lower().strip()
        is_anonymous = request.form.get('is_anonymous') == 'true'
        
        user = None
        
        # Anonim kullanıcı oluşturma
        if is_anonymous:
            import uuid
            anonymous_id = str(uuid.uuid4())
            user = User(
                anonymous_id=anonymous_id,
                is_anonymous=True
            )
            db.session.add(user)
            db.session.commit()
        
        # Email ile giriş
        elif email:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    username=username if username else None,
                    is_anonymous=False
                )
                db.session.add(user)
                db.session.commit()
            elif username and not user.username:
                # Var olan kullanıcıya username ekle
                user.username = username
                db.session.commit()
        
        # Kullanıcı adı ile giriş
        elif username:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    is_anonymous=False
                )
                db.session.add(user)
                db.session.commit()
        
        # Hiçbir bilgi girilmemişse hata
        else:
            flash('Lütfen kullanıcı adı, e-posta girin veya anonim olarak devam edin.', 'danger')
            return redirect(url_for('giris'))

        login_user(user, remember=True)

        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        if not user.has_consented:
            return redirect(url_for('consent'))
        if not user.profession or user.experience is None:
            return redirect(url_for('demographics'))

        return redirect(url_for('select_research'))

    return render_template('giris.html')

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
            session['admin_authenticated'] = True
            flash('Yönetici paneline başarıyla giriş yapıldı.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Geçersiz yönetici e-posta veya şifre.', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('admin/admin_login.html')

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Yönetici için ana kontrol paneli."""
    researches = Research.query.order_by(Research.id.desc()).all()
    stats = {
        'user_count': User.query.count(),
        'response_count': UserResponse.query.count(),
        'case_count': Case.query.count()
    }
    return render_template('admin/admin_dashboard.html', researches=researches, stats=stats)

@app.route('/admin/upload_json', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_json():
    if request.method == 'POST':
        json_text = request.form.get('json_text')
        if not json_text:
            flash('Yüklenecek JSON verisi bulunamadı.', 'danger')
            return redirect(url_for('upload_json'))
        
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
                llm_responses = content.get('llm_responses', {}) or {}
                gold_standard = content.get('gold_standard', {}) or {}

                # LLM skorlarını önceden hesapla (basit eşleşme)
                case_llm_scores = {}
                for llm_name, llm_answers in llm_responses.items():
                    llm_question_scores = {}
                    total_score = 0
                    question_count = 0

                    for q_id, gold_answer in (gold_standard.items() if isinstance(gold_standard, dict) else []):
                        llm_answer = (llm_answers or {}).get(q_id, "")
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
        
        return redirect(url_for('admin_dashboard')) 
    
    return render_template('admin/upload_research.html')

@app.route('/admin/export_csv')
@login_required
@admin_required
def export_csv():
    """Tüm yanıt verilerini CSV olarak dışa aktarır."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Tüm olası başlıkları belirle
    header = [
        'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil', 
        'arastirma_id', 'arastirma_baslik', 'vaka_id', 'vaka_baslik', 
        'yanit_suresi_saniye', 'yanit_tarihi', 'guven_skoru', 'klinik_gerekce'
    ]
    
    # Dinamik soru başlıklarını topla
    all_question_keys = set()
    all_responses = UserResponse.query.all()
    if not all_responses:
        flash("Dışa aktarılacak veri bulunamadı.", "warning")
        return redirect(url_for('admin_dashboard'))

    for resp in all_responses:
        if isinstance(resp.answers, dict):
            all_question_keys.update(resp.answers.keys())
    
    question_headers = sorted(list(all_question_keys))
    header.extend(question_headers)
    
    writer.writerow(header)
    
    for resp in all_responses:
        answers = resp.answers or {}
        case = resp.case
        research = case.research if case else None
        author = resp.author

        row = [
            resp.id,
            author.id if author else None,
            author.profession if author else None,
            author.experience if author else None,
            research.id if research else None,
            research.title if research else None,
            case.id if case else None,
            (case.content or {}).get('title', ''),
            resp.duration_seconds,
            resp.created_at.isoformat(),
            resp.confidence_score,
            resp.clinical_rationale
        ]
        
        # Dinamik soruları ekle
        for q_key in question_headers:
            row.append(answers.get(q_key, ''))
            
        writer.writerow(row)
        
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=LLM_Research_TUM_VERISETI.csv"})


@app.route('/admin/export/research/<int:research_id>')
@login_required
@admin_required
def export_research_csv(research_id):
    """Sadece belirli bir araştırmaya ait yanıt verilerini CSV olarak dışa aktarır."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    responses = UserResponse.query.join(Case).filter(Case.research_id == research_id).all()
    if not responses:
        flash("Bu araştırma için dışa aktarılacak veri bulunamadı.", "info")
        return redirect(url_for('research_admin_dashboard', research_id=research_id))

    safe_title = "".join(c if c.isalnum() else "_" for c in (research.title or "research"))
    filename = f"Arastirma_{research.id}_{safe_title}_Veriseti.csv"

    output = io.StringIO()
    writer = csv.writer(output)

    header = [
        'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil',
        'vaka_id', 'vaka_baslik', 'yanit_suresi_saniye', 'yanit_tarihi',
        'guven_skoru', 'klinik_gerekce'
    ]
    
    all_question_keys = set()
    for resp in responses:
        if isinstance(resp.answers, dict):
            all_question_keys.update(resp.answers.keys())
    
    question_headers = sorted(list(all_question_keys))
    header.extend(question_headers)
    writer.writerow(header)

    for resp in responses:
        answers = resp.answers or {}
        author = resp.author
        case = resp.case
        
        row = [
            resp.id,
            author.id if author else None,
            author.profession if author else None,
            author.experience if author else None,
            case.id if case else None,
            (case.content or {}).get('title', ''),
            resp.duration_seconds,
            resp.created_at.isoformat(),
            resp.confidence_score,
            resp.clinical_rationale
        ]
        
        for q_key in question_headers:
            row.append(answers.get(q_key, ''))
            
        writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={filename}"})

# --- 10. VERİTABANI BAŞLATMA (SEEDING) ---
# (Bu bölüm init_db.py'ye taşındı)

# --- 11. YÖNETİCİ API ROTALARI ---

@app.route('/admin/maintenance', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_maintenance():
    """Bakım modu yönetimi sayfası."""
    if request.method == 'POST':
        mode = request.form.get('maintenance_mode', 'false')
        message = request.form.get('maintenance_message', 'Sistem bakımda. Lütfen daha sonra tekrar deneyin.')
        
        # Bakım modu ayarını güncelle veya oluştur
        mode_setting = SystemSettings.query.filter_by(key='maintenance_mode').first()
        if mode_setting:
            mode_setting.value = mode
            mode_setting.updated_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            mode_setting = SystemSettings(key='maintenance_mode', value=mode, description='Bakım modu durumu')
            db.session.add(mode_setting)
        
        # Bakım modu mesajını güncelle veya oluştur
        message_setting = SystemSettings.query.filter_by(key='maintenance_message').first()
        if message_setting:
            message_setting.value = message
            message_setting.updated_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            message_setting = SystemSettings(key='maintenance_message', value=message, description='Bakım modu mesajı')
            db.session.add(message_setting)
        
        db.session.commit()
        flash(f'Bakım modu {"açıldı" if mode == "true" else "kapatıldı"}!', 'success')
        return redirect(url_for('admin_maintenance'))
    
    # GET isteği
    mode_setting = SystemSettings.query.filter_by(key='maintenance_mode').first()
    message_setting = SystemSettings.query.filter_by(key='maintenance_message').first()
    
    maintenance_mode = mode_setting.value if mode_setting else 'false'
    maintenance_message = message_setting.value if message_setting else 'Sistem bakımda. Lütfen daha sonra tekrar deneyin.'
    
    return render_template('admin/maintenance.html', 
                         maintenance_mode=maintenance_mode,
                         maintenance_message=maintenance_message)

@app.route('/admin/llms')
@login_required
@admin_required
def manage_llms():
    llms = LLM.query.order_by(LLM.name).all()
    return render_template('admin/manage_llms.html', llms=llms)

@app.route('/admin/llm/ekle', methods=['POST'])
@login_required
@admin_required
def add_llm():
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
    """Artık /admin/dashboard tarafından kullanılıyor, bu yönlendirme olarak kalabilir."""
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/case-generator', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_case_generator():
    """Research Case Generator - Admin Panel Entegrasyonu"""
    
    if request.method == 'POST':
        try:
            # Form verilerini al ve session'a kaydet
            import uuid
            task_id = str(uuid.uuid4())
            
            session[f'case_gen_params_{task_id}'] = {
                'template_type': request.form.get('template_type'),
                'research_title': request.form.get('research_title'),
                'target_group': request.form.get('target_group'),
                'specialty': request.form.get('specialty'),
                'num_cases': int(request.form.get('num_cases', 5)),
                'questions_per_case': int(request.form.get('questions_per_case', 5)),
                'difficulty': request.form.get('difficulty', 'mixed'),
                'gemini_model': request.form.get('gemini_model', 'gemini-pro-latest'),
                'focus_areas': request.form.get('focus_areas', ''),
                'additional_directives': request.form.get('additional_directives', ''),
                'status': 'pending'
            }
            
            # Progress sayfasına yönlendir
            return redirect(url_for('case_generator_progress', task_id=task_id))
                
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('admin_case_generator'))
    
    # GET request - formu göster
    return render_template('admin/case_generator.html')

@app.route('/admin/case-generator/progress/<task_id>')
@login_required
@admin_required
def case_generator_progress(task_id):
    """Progress görüntüleme sayfası"""
    params = session.get(f'case_gen_params_{task_id}')
    if not params:
        flash('Geçersiz task ID.', 'danger')
        return redirect(url_for('admin_case_generator'))
    
    return render_template('admin/case_generator_progress.html', task_id=task_id, params=params)

@app.route('/admin/case-generator/execute/<task_id>')
@login_required
@admin_required
def case_generator_execute(task_id):
    """SSE endpoint - Real-time log streaming"""
    # Session'dan params'ı al (generator dışında)
    params = session.get(f'case_gen_params_{task_id}')
    if not params:
        return "data: {\"type\": \"error\", \"message\": \"Task bulunamadı\"}\n\n", 404
    
    def generate_logs(params):
        import time
        import json
        from datetime import datetime
        
        try:
            # Log helper
            def log(level, message, progress=None):
                data = {
                    'type': level,
                    'message': message,
                    'progress': progress,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }
                return f"data: {json.dumps(data)}\n\n"
            
            yield log('info', '🚀 Vaka oluşturma başlatılıyor...')
            time.sleep(0.3)
            
            # ResearchCaseGenerator'ı import et
            gemini_model = params.get('gemini_model', 'gemini-pro-latest')
            yield log('info', f'🤖 Gemini AI bağlantısı kuruluyor ({gemini_model})...')
            from research_case_generator import ResearchCaseGenerator
            generator = ResearchCaseGenerator(model_name=gemini_model)
            time.sleep(0.2)
            yield log('success', f'✓ Gemini AI bağlantısı başarılı ({gemini_model})')
            
            # Direktifleri hazırla
            template_type = params['template_type']
            num_cases = params['num_cases']
            questions_per_case = params['questions_per_case']
            difficulty = params['difficulty']
            
            if template_type == 'custom':
                yield log('info', '📝 Özel direktifler hazırlanıyor...')
                directives = {
                    'research_title': params['research_title'],
                    'target_group': params['target_group'],
                    'specialty': params['specialty'],
                    'focus_areas': [area.strip() for area in params['focus_areas'].split('\n') if area.strip()],
                    'additional_context': params['additional_directives']
                }
                time.sleep(0.2)
                yield log('success', '✓ Özel direktifler hazırlandı')
            else:
                yield log('info', f'📋 Şablon yükleniyor: {template_type}')
                template = generator.get_template_directives(template_type)
                if template:
                    directives = template
                    if params['additional_directives']:
                        directives['additional_context'] = params['additional_directives']
                    time.sleep(0.2)
                    yield log('success', '✓ Şablon başarıyla yüklendi')
                else:
                    yield log('error', '❌ Şablon yüklenemedi')
                    return
            
            # Batch generation
            yield log('info', f'🔬 {num_cases} vaka oluşturuluyor (bu birkaç dakika sürebilir)...')
            time.sleep(0.5)
            
            cases_data = []
            for i in range(num_cases):
                progress = int((i / num_cases) * 100)
                yield log('info', f'⏳ Vaka {i+1}/{num_cases} hazırlanıyor...', progress)
                
                # Gerçek vaka oluşturma (bu kısım yavaş)
                case = generator.generate_research_case(directives, questions_per_case, difficulty)
                if case:
                    cases_data.append(case)
                    progress = int(((i+1) / num_cases) * 100)
                    yield log('success', f'✓ Vaka {i+1}/{num_cases} tamamlandı', progress)
                else:
                    yield log('warning', f'⚠ Vaka {i+1} oluşturulamadı, devam ediliyor...')
            
            if not cases_data:
                yield log('error', '❌ Hiçbir vaka oluşturulamadı')
                return
            
            yield log('success', f'✅ Tüm vakalar oluşturuldu ({len(cases_data)} adet)')
            time.sleep(0.3)
            
            # Veritabanına kaydet
            yield log('info', '💾 Veritabanına kaydediliyor...')
            time.sleep(0.5)
            
            research_id = generator.load_to_database(cases_data)
            
            if research_id:
                yield log('success', f'✅ Veritabanına kaydedildi (Research ID: {research_id})', 100)
                time.sleep(0.5)
                yield f"data: {json.dumps({'type': 'complete', 'research_id': research_id})}\n\n"
            else:
                yield log('error', '❌ Veritabanına kaydetme başarısız')
                
        except Exception as e:
            yield log('error', f'❌ Hata: {str(e)}')
    
    return Response(generate_logs(params), mimetype='text/event-stream')

@app.route('/admin/arastirma/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def add_research():
    """Manuel olarak yeni (boş) bir araştırma ekler."""
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = request.form.get('description')

        if not title:
            flash('Lütfen geçerli bir başlık girin.', 'danger')
            return render_template('admin/research_admin_dashboard.html', title=title, description=description)
        
        existing_research = Research.query.filter_by(title=title).first()
        if existing_research:
            flash('Bu başlıkta bir araştırma zaten mevcut.', 'danger')
            return render_template('admin/research_admin_dashboard.html', title=title, description=description)

        new_research = Research(
            title=title,
            description=description,
            is_active=True
        )
        db.session.add(new_research)
        db.session.commit()
        flash(f'"{title}" araştırması başarıyla oluşturuldu.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # GET request için boş formu göster (research=None ile)
    return render_template('admin/research_admin_dashboard.html', research=None, cases=[])


@app.route('/admin/arastirma/duzenle/<int:research_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_research(research_id):
    """Bu artık research_admin_dashboard ile birleştirildi."""
    return redirect(url_for('research_admin_dashboard', research_id=research_id))

@app.route('/admin/case/duzenle/<int:case_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_case(case_id):
    case = db.session.get(Case, case_id)
    if not case:
        flash('Vaka bulunamadı.', 'danger')
        return redirect(url_for('admin.cases_list'))

    if request.method == 'POST':
        # Formdan gelen güncellenmiş verileri al
        try:
            # Önce content'in bir kopya olduğundan emin ol
            new_content = dict(case.content or {})
            
            # 1. Temel Bilgileri Güncelle
            new_content['title'] = request.form.get('title')
            
            # 2. Soruları Güncelle
            new_questions = []
            question_ids = request.form.getlist('question_id')
            question_labels = request.form.getlist('question_label')
            question_types = request.form.getlist('question_type')
            question_options_list = request.form.getlist('question_options')

            for i, q_id in enumerate(question_ids):
                q_label = question_labels[i]
                q_type = question_types[i]
                q_options_raw = question_options_list[i]
                
                question_data = {
                    "id": q_id,
                    "label": q_label,
                    "type": q_type
                }
                
                if q_type == 'multiple-choice':
                    options = [opt.strip() for opt in q_options_raw.splitlines() if opt.strip()]
                    question_data["options"] = options
                
                new_questions.append(question_data)
            
            new_content['questions'] = new_questions
            
            # 3. Altın Standart Yanıtları Güncelle
            new_gold_standard = {}
            for q in new_questions:
                q_id = q['id']
                gold_value = request.form.get(f'gold_standard_{q_id}')
                if gold_value:
                    new_gold_standard[q_id] = gold_value
            
            new_content['gold_standard'] = new_gold_standard

            # 4. LLM Yanıtlarını Güncelle
            llm_responses = new_content.get('llm_responses', {})
            llms = LLM.query.all()
            for llm in llms:
                llm_response_val = request.form.get(f'llm_response_{llm.name}')
                if llm_response_val is not None:
                    llm_responses[llm.name] = llm_response_val
            new_content['llm_responses'] = llm_responses

            # Güncel form verilerine göre mevcut bölüm içeriklerini güncelle
            existing_sections = new_content.get('sections', []) or []
            updated_sections = []
            for idx, section in enumerate(existing_sections):
                section_content = request.form.get(f'section_{idx}')
                if section_content is None:
                    break
                updated_sections.append({
                    'title': section.get('title', f'Bölüm {idx + 1}'),
                    'content': section_content
                })
            if updated_sections and len(updated_sections) == len(existing_sections):
                new_content['sections'] = updated_sections

            # Değişiklikleri kaydet
            case.content = new_content
            flag_modified(case, "content")
            db.session.commit()
            flash(f'"{new_content["title"]}" vakası başarıyla güncellendi.', 'success')
            return redirect(url_for('research_admin_dashboard', research_id=case.research_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Vaka güncellenirken bir hata oluştu: {e}", "danger")

    # --- LLM PROMPT OLUŞTURMA BÖLÜMÜ GÜNCELLENDİ ---
    prompts = {'uzman': '', 'hekim': '', 'rolsuz': ''}
    if case.content:
        case_data = case.content

        # Ortak Kısımlar
        common_lines = [
            "--- VAKA DETAYLARI ---",
            f"Başlık: {case_data.get('title', 'N/A')}",
            "Bölümler:"
        ]
        for section in case_data.get('sections', []):
            common_lines.append(f"  - {section.get('title', 'Başlıksız Bölüm')}: {section.get('content', '')}")

        common_lines.append("--- SORULAR ---")
        question_ids_for_json = []
        mcq_questions_text = []  # Çoktan seçmeli soruları metin olarak sakla
        for i, q in enumerate(case_data.get('questions', []), 1):
            if q.get('type') == 'multiple-choice':
                q_text_lines = [f"{i}. Soru (ID: {q.get('id')}): {q.get('label', '')}"]
                options = q.get('options', [])
                for j, opt in enumerate(options):
                    q_text_lines.append(f"   {chr(65+j)}. {opt}")  # A. Seçenek, B. Seçenek...
                mcq_questions_text.append("\n".join(q_text_lines))
                question_ids_for_json.append(q.get('id'))
            # Diğer soru tipleri için gerekirse ekleme yapılabilir

        common_lines.extend(mcq_questions_text)  # Soruları ortak kısma ekle

        # Güncellenmiş JSON Format Talimatı ve Örneği
        json_format_example = ["{", "  \"answers\": {"]
        for q_id in question_ids_for_json:
            json_format_example.append(f'    "{q_id}": "<Buraya Seçilen Cevap Metni Gelecek>",')
        if json_format_example[-1].endswith(','):
             json_format_example[-1] = json_format_example[-1][:-1]
        json_format_example.extend([
            "  },",
            "  \"confidence_score\": <1-100 arası sayısal tahmin>,",
            "  \"rationale\": \"<Seçimleriniz için 1-2 cümlelik kısa gerekçe>\"",
            "}"])

        format_instruction = [
            "Yanıtlarını SADECE aşağıdaki JSON formatında ver, başka hiçbir metin ekleme:",
            *json_format_example
        ]

        # Rol Tanımları
        role_uzman = "Sen deneyimli bir pediatri enfeksiyon hastalıkları uzmanısın."
        role_hekim = "Sen bir pratisyen hekimsin."
        role_rolsuz = ""  # Rol tanımı yok

        # Güncellenmiş Görev Tanımı
        task_instruction = [
            "Aşağıdaki vaka detaylarını ve çoktan seçmeli soruları dikkatlice incele.",
            "Her soru için en uygun seçeneği belirle.",
            "Tüm seçimlerini yaptıktan sonra, genel olarak bu vakadaki cevaplarından ne kadar emin olduğunu 1-100 arasında bir sayı ile tahmin et (confidence_score).",
            "Son olarak, neden bu cevapları seçtiğini 1-2 cümle ile kısaca açıkla (rationale)."
        ]

        # Promptları Birleştirme
        def create_prompt(role, task, common, format_instr):
            lines = []
            if role:
                lines.append(role)
            lines.extend(task)
            lines.extend(format_instr)
            lines.extend(common)
            return "\n".join(lines)

        prompts['uzman'] = create_prompt(role_uzman, task_instruction, common_lines, format_instruction)
        prompts['hekim'] = create_prompt(role_hekim, task_instruction, common_lines, format_instruction)
        prompts['rolsuz'] = create_prompt(role_rolsuz, task_instruction, common_lines, format_instruction)

    # --- PROMPT OLUŞTURMA SONU ---

    all_llms = LLM.query.all()
    return render_template('admin/edit_case.html',
                           case=case,
                           all_llms=all_llms,
                           llm_prompts=prompts)

@app.route('/admin/research/<int:research_id>/add_case')
@login_required
@admin_required
def add_case_to_research(research_id):
    """Araştırmaya yeni bir vaka ekler."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    new_case_content = {
        "title": "Yeni Vaka (Başlığı Düzenleyin)",
        "case_id_internal": f"VAKA_{int(time.time())}",
        "sections": [
            {"title": "Anamnez", "content": "Vaka anamnezini buraya girin..."},
            {"title": "Fizik Muayene", "content": "Vaka bulgularını buraya girin..."}
        ],
        "questions": [],
        "gold_standard": {},
        "llm_responses": {}
    }

    new_case = Case(
        research_id=research_id,
        content=new_case_content
    )
    db.session.add(new_case)
    db.session.commit()

    flash(f"Yeni vaka oluşturuldu. Lütfen içeriğini düzenleyin.", "success")
    # Kullanıcıyı doğrudan yeni vakanın düzenleme sayfasına yönlendir
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
        # Bu POST isteği araştırma ayarlarını günceller
        title = (request.form.get('title') or '').strip()
        if not title:
            flash('Araştırma başlığı boş olamaz.', 'danger')
        else:
            # Başlık değiştiyse çakışma olup olmadığını kontrol et
            if title != research.title and Research.query.filter_by(title=title).first():
                flash('Bu başlıkta başka bir araştırma zaten mevcut.', 'danger')
            else:
                research.title = title
                research.description = request.form.get('description')
                research.is_active = 'is_active' in request.form
                db.session.commit()
                flash('Araştırma ayarları güncellendi.', 'success')
        
        return redirect(url_for('research_admin_dashboard', research_id=research.id))
    
    cases = Case.query.filter_by(research_id=research.id).order_by(Case.id).all()
    return render_template('admin/research_admin_dashboard.html', research=research, cases=cases)

# --- 9. VERİ EXPORT SİSTEMİ ---

@app.route('/admin/research/<int:research_id>/export/<format>')
@login_required
@admin_required
def export_research_data(research_id, format):
    """Araştırma verilerini CSV, JSON veya Excel formatında indirir."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Filtreleme parametreleri
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    profession = request.args.get('profession')
    
    # Temel query
    query = UserResponse.query.join(Case).filter(Case.research_id == research_id)
    
    # Filtreleri uygula
    if start_date:
        try:
            start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(UserResponse.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            query = query.filter(UserResponse.created_at < end_dt)
        except ValueError:
            pass
    
    if profession:
        query = query.join(User).filter(User.profession == profession)
    
    responses = query.all()
    
    # Veri hazırlama
    data = []
    for resp in responses:
        user = resp.author
        case = resp.case
        case_content = case.content or {}
        
        row = {
            'response_id': resp.id,
            'user_id': user.id,
            'user_display_name': user.get_display_name(),
            'user_email': user.email or 'N/A',
            'user_username': user.username or 'N/A',
            'is_anonymous': user.is_anonymous,
            'profession': user.profession or 'Bilinmiyor',
            'experience_years': user.experience or 0,
            'case_id': case.id,
            'case_title': case_content.get('title', 'Başlıksız'),
            'confidence_score': resp.confidence_score or 0,
            'clinical_rationale': resp.clinical_rationale or '',
            'duration_seconds': resp.duration_seconds or 0,
            'created_at': resp.created_at.strftime('%Y-%m-%d %H:%M:%S') if resp.created_at else '',
        }
        
        # Cevapları ekle
        if isinstance(resp.answers, dict):
            for key, value in resp.answers.items():
                row[f'answer_{key}'] = value
        
        # Skorları ekle
        if isinstance(resp.scores, dict):
            for key, value in resp.scores.items():
                row[f'score_{key}'] = value
        
        data.append(row)
    
    if not data:
        flash('Belirtilen kriterlere uygun veri bulunamadı.', 'warning')
        return redirect(url_for('research_admin_dashboard', research_id=research_id))
    
    df = pd.DataFrame(data)
    filename = f"{research.title.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Format'a göre export
    if format == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}.csv'}
        )
    
    elif format == 'json':
        json_data = df.to_json(orient='records', force_ascii=False, indent=2)
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}.json'}
        )
    
    elif format == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Responses', index=False)
            
            # Özet istatistikler sayfası
            summary_data = {
                'Metrik': ['Toplam Yanıt', 'Benzersiz Kullanıcı', 'Ortalama Deneyim (Yıl)', 
                          'Ortalama Güven Skoru', 'Ortalama Süre (Saniye)'],
                'Değer': [
                    len(df),
                    df['user_id'].nunique(),
                    df['experience_years'].mean(),
                    df['confidence_score'].mean(),
                    df['duration_seconds'].mean()
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Özet', index=False)
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}.xlsx'}
        )
    
    else:
        flash('Geçersiz format.', 'danger')
        return redirect(url_for('research_admin_dashboard', research_id=research_id))

@app.route('/admin/case/delete/<int:case_id>', methods=['POST'])
@login_required
@admin_required
def delete_case(case_id):
    case = db.session.get(Case, case_id)
    if not case:
        flash("Silinecek vaka bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    research_id = case.research_id
    title = (case.content or {}).get('title', 'Başlıksız Vaka')

    try:
        UserResponse.query.filter_by(case_id=case_id).delete()
        ReferenceAnswer.query.filter_by(case_id=case_id).delete()
        db.session.delete(case)
        db.session.commit()
        flash(f'"{title}" vakası ve ona ait tüm yanıtlar kalıcı olarak silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Vaka silinirken bir hata oluştu: {e}', 'danger')
        
    return redirect(url_for('research_admin_dashboard', research_id=research_id))

@app.route('/admin/research/delete/<int:research_id>', methods=['POST'])
@login_required
@admin_required
def delete_research(research_id):
    """Bir araştırmayı ve ona ait tüm vakaları, yanıtları ve referansları siler."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Silinecek araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    research_title = research.title
    try:
        # 1. Araştırmaya ait vakaları bul
        cases = Case.query.filter_by(research_id=research.id).all()
        if cases:
            case_ids = [c.id for c in cases]

            # 2. Vakalarla ilişkili UserResponse'ları sil (toplu silme)
            UserResponse.query.filter(UserResponse.case_id.in_(case_ids)).delete(synchronize_session=False)

            # 3. Vakalarla ilişkili ReferenceAnswer'ları sil (toplu silme)
            ReferenceAnswer.query.filter(ReferenceAnswer.case_id.in_(case_ids)).delete(synchronize_session=False)

            # 4. Vakaları sil
            for case in cases:
                db.session.delete(case)

        # 5. Araştırmanın kendisini sil
        db.session.delete(research)

        # 6. Değişiklikleri kaydet
        db.session.commit()
        flash(f'"{research_title}" araştırması ve ilişkili tüm veriler başarıyla silindi.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Araştırma silinirken bir hata oluştu: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))

# --- 10. ARAŞTIRMA BULGULARI MODÜLÜ ---

@app.route('/admin/research/<int:research_id>/findings')
@login_required
@admin_required
def research_findings(research_id):
    """Araştırma bulgularını akademik formatta gösterir."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    findings = ResearchFinding.query.filter_by(research_id=research_id).order_by(ResearchFinding.order_index).all()
    
    # Verileri analiz et
    from analysis import get_research_responses_df
    from advanced_analytics import create_interactive_dashboard_data
    
    df = get_research_responses_df(research_id)
    analytics_data = None
    
    if not df.empty:
        try:
            analytics_data = create_interactive_dashboard_data(df, research_id)
        except Exception as e:
            app.logger.error(f"Analytics oluşturulurken hata: {e}")
    
    return render_template('admin/research_findings.html', 
                          research=research, 
                          findings=findings,
                          analytics_data=analytics_data)

@app.route('/admin/research/<int:research_id>/findings/generate', methods=['POST'])
@login_required
@admin_required
def generate_findings(research_id):
    """Gemini API kullanarak otomatik bulgular oluşturur."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    from analysis import get_research_responses_df
    df = get_research_responses_df(research_id)
    
    if df.empty:
        flash('Bulgu oluşturmak için yeterli veri yok.', 'warning')
        return redirect(url_for('research_findings', research_id=research_id))
    
    # Gemini ile bulgu metni oluştur
    if not model:
        flash('Gemini API kullanılamıyor. Lütfen yapılandırmayı kontrol edin.', 'danger')
        return redirect(url_for('research_findings', research_id=research_id))
    
    summary_stats = {
        'total_responses': len(df),
        'unique_users': df['user_id'].nunique() if 'user_id' in df.columns else 0,
        'avg_confidence': df['confidence_score'].mean() if 'confidence_score' in df.columns else 0,
        'avg_score': df['user_final_score'].mean() if 'user_final_score' in df.columns else 0,
    }
    
    prompt = f"""
    Sen deneyimli bir tıbbi araştırmacısın. Aşağıdaki araştırma verilerine dayalı olarak akademik bir "Bulgular" bölümü yaz.
    
    Araştırma: {research.title}
    Açıklama: {research.description or 'Belirtilmemiş'}
    
    Veri Özeti:
    - Toplam Yanıt: {summary_stats['total_responses']}
    - Benzersiz Katılımcı: {summary_stats['unique_users']}
    - Ortalama Güven Skoru: {summary_stats['avg_confidence']:.2f}
    - Ortalama Performans Skoru: {summary_stats['avg_score']:.2f}
    
    Lütfen profesyonel, bilimsel bir dille bulgular bölümü oluştur. Tablolar ve grafiklerle desteklenecek şekilde metinler yaz.
    """
    
    try:
        response = model.generate_content(prompt)
        finding_text = response.text
        
        # Yeni bulgu kaydet
        new_finding = ResearchFinding(
            research_id=research_id,
            title="Otomatik Oluşturulan Bulgular Metni",
            finding_type='text',
            content={'text': finding_text},
            order_index=ResearchFinding.query.filter_by(research_id=research_id).count(),
            is_published=False
        )
        db.session.add(new_finding)
        db.session.commit()
        
        flash('Bulgular başarıyla oluşturuldu!', 'success')
    except Exception as e:
        flash(f'Bulgular oluşturulurken hata: {e}', 'danger')
    
    return redirect(url_for('research_findings', research_id=research_id))

@app.route('/admin/research/<int:research_id>/findings/add', methods=['POST'])
@login_required
@admin_required
def add_finding(research_id):
    """Manuel olarak bulgu ekler."""
    research = db.session.get(Research, research_id)
    if not research:
        flash('Araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    title = request.form.get('title')
    finding_type = request.form.get('finding_type')
    content_text = request.form.get('content_text')
    
    if not title or not finding_type:
        flash('Başlık ve tip zorunludur.', 'danger')
        return redirect(url_for('research_findings', research_id=research_id))
    
    content = {'text': content_text} if content_text else {}
    
    new_finding = ResearchFinding(
        research_id=research_id,
        title=title,
        finding_type=finding_type,
        content=content,
        order_index=ResearchFinding.query.filter_by(research_id=research_id).count()
    )
    
    db.session.add(new_finding)
    db.session.commit()
    
    flash('Bulgu eklendi!', 'success')
    return redirect(url_for('research_findings', research_id=research_id))

@app.route('/admin/research/finding/<int:finding_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_finding(finding_id):
    """Bulguyu siler."""
    finding = db.session.get(ResearchFinding, finding_id)
    if not finding:
        flash('Bulgu bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    research_id = finding.research_id
    db.session.delete(finding)
    db.session.commit()
    
    flash('Bulgu silindi.', 'success')
    return redirect(url_for('research_findings', research_id=research_id))

@app.route('/admin/research/<int:research_id>/findings/export-pdf')
@login_required
@admin_required
def export_findings_pdf(research_id):
    """Bulguları PDF olarak export eder."""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    
    research = db.session.get(Research, research_id)
    if not research:
        flash('Araştırma bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    findings = ResearchFinding.query.filter_by(research_id=research_id, is_published=True).order_by(ResearchFinding.order_index).all()
    
    # PDF oluştur
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Başlık
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
    )
    story.append(Paragraph(research.title, title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Bulgular Başlığı
    story.append(Paragraph("BULGULAR", styles['Heading1']))
    story.append(Spacer(1, 0.3*inch))
    
    # Her bulguyu ekle
    for finding in findings:
        story.append(Paragraph(finding.title, styles['Heading2']))
        
        if finding.finding_type == 'text' and 'text' in finding.content:
            story.append(Paragraph(finding.content['text'], styles['Normal']))
        
        story.append(Spacer(1, 0.2*inch))
    
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={research.title}_bulgular.pdf'}
    )

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
        
    research = case.research
    all_case_ids = [c.id for c in Case.query.filter_by(research_id=research.id).order_by(Case.id).all()]
    completed_case_ids = {resp.case_id for resp in UserResponse.query.filter_by(user_id=current_user.id).join(Case).filter(Case.research_id == research.id).all()}
    
    # Bu vaka zaten çözülmüş mü? (URL manipülasyonunu engelle)
    if case_id in completed_case_ids:
        flash("Bu vakayı zaten çözdünüz.", "info")
        return redirect(url_for('research_dashboard', research_id=research.id))

    if request.method == 'POST':
        start_time = session.get(f'case_{case_id}_start_time', time.time())
        duration = int(time.time() - start_time)

        answers = {
            key: value for key, value in request.form.items() 
            if key not in ['duration_seconds', 'confidence_score', 'clinical_rationale']
        }

        new_response = UserResponse(
            case_id=case.id,
            author=current_user,
            answers=answers,
            confidence_score=int(request.form.get('confidence_score', 75)),
            clinical_rationale=request.form.get('clinical_rationale', '').strip(),
            duration_seconds=duration
        )
        db.session.add(new_response)
        db.session.commit()
        
        # Puanlama görevini kuyruğa ekle
        if queue:
            try:
                queue.enqueue('tasks.score_and_store_response', new_response.id, job_timeout=600)
            except Exception as e:
                app.logger.error(f"RQ kuyruğa ekleme hatası: {e}")

        # Sonraki vakayı bul
        completed_case_ids.add(case_id) # Az önce çözüleni de ekle
        next_case_id = None
        for cid in all_case_ids:
            if cid not in completed_case_ids:
                next_case_id = cid
                break

        if next_case_id:
            session[f'case_{next_case_id}_start_time'] = time.time()
            return redirect(url_for('case_detail', case_id=next_case_id))
        else:
            # Araştırma bitti
            return redirect(url_for('final_report', research_id=research.id))

    # GET isteği
    session[f'case_{case_id}_start_time'] = session.get(f'case_{case_id}_start_time', time.time())
    
    try:
        current_case_index = all_case_ids.index(case_id) + 1
        total_cases = len(all_case_ids)
    except ValueError:
        current_case_index = len(completed_case_ids) + 1
        total_cases = len(all_case_ids)

    return render_template('case_chat.html', 
                           case=case, 
                           current_case_index=current_case_index, 
                           total_cases=total_cases)

@app.route('/arastirma/<int:research_id>/rapor')
@login_required
@research_setup_required
def final_report(research_id):
    """Kullanıcının bir araştırmadaki tüm yanıtlarını gösteren final sayfası."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Rapor görüntülenecek araştırma bulunamadı.", "danger")
        return redirect(url_for('select_research'))
    
    responses = UserResponse.query.join(Case).filter(
        Case.research_id == research_id,
        UserResponse.user_id == current_user.id
    ).order_by(Case.id).all()

    return render_template('final_report.html', research=research, responses=responses)

# --- 12. YÖNETİCİ ANALİZ ROTALARI ---

@app.route('/admin/case/<int:case_id>/review')
@login_required
@admin_required
def review_case(case_id):
    """Yönetici için vaka bazlı analiz, istatistik ve yönetim ekranı."""
    case = db.session.get(Case, case_id)
    if not case:
        flash("Analiz edilecek vaka bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    responses = UserResponse.query.filter_by(case_id=case_id).all()
    all_llms = LLM.query.all()
    
    stats = {}
    if responses:
        try:
            data = []
            for r in responses:
                row = {'sure_saniye': getattr(r, 'duration_seconds', 0) or 0}
                if isinstance(getattr(r, 'answers', None), dict):
                    row.update(r.answers)
                data.append(row)
            
            df = pd.DataFrame(data)
            stats['response_count'] = len(df)
            stats['avg_duration'] = float(df['sure_saniye'].mean()) if 'sure_saniye' in df.columns else 0.0

            questions = (case.content or {}).get('questions', [])
            choice_question_stats = {}
            for q in questions:
                q_id = q.get('id')
                if q.get('type') == 'multiple-choice' and q_id in df.columns:
                    choice_counts = df[q_id].value_counts()
                    choice_question_stats[q.get('label', q_id)] = {
                        'labels': choice_counts.index.tolist(),
                        'data': choice_counts.values.tolist()
                    }
            stats['choice_questions'] = choice_question_stats
        except Exception as e:
            print(f"Stats hesaplama hatası: {e}")
            stats = {'response_count': len(responses), 'avg_duration': 0, 'choice_questions': {}}
    else:
        stats = {'response_count': 0, 'avg_duration': 0, 'choice_questions': {}}

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

    # Veriyi DataFrame olarak al
    df = get_research_responses_df(research_id)
    
    if df.empty:
        flash("Bu araştırma için henüz veri yok.", "info")
        stats = None
    else:
        stats = calculate_participant_stats(df)
        if not stats:
             flash("İstatistikler hesaplanırken bir hata oluştu.", "danger")

    return render_template('admin/research_stats.html', research=research, stats=stats)

@app.route('/admin/research/<int:research_id>/analytics')
@login_required
@admin_required
def scientific_analytics(research_id):
    """Bilimsel analiz ve karşılaştırma paneli - İnsan vs. LLM performansı."""
    research = db.session.get(Research, research_id)
    if not research:
        flash("Araştırma bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Veriyi DataFrame olarak al
    df = get_research_responses_df(research_id)

    if df.empty:
        flash("Bu araştırma için henüz analiz edilecek veri bulunmuyor.", "info")
        analytics = None
    else:
        analytics = calculate_scientific_analytics(df)
        if not analytics:
             flash("Bilimsel analizler hesaplanırken bir hata oluştu.", "danger")

    return render_template('admin/scientific_analytics.html', research=research, analytics=analytics)


# --- 13. KOMUT SATIRI VE ÇALIŞTIRMA ---
import click
from flask.cli import with_appcontext
# get_semantic_score fonksiyonunun bu komuttan önce tanımlandığından emin olun

@app.cli.command('test-gemini')
@with_appcontext
def test_gemini_command():
    """Gemini Hakem LLM fonksiyonunu (get_semantic_score) test eder."""
    click.echo(click.style("Gemini Hakem LLM Test Ediliyor...", fg='yellow', bold=True))

    # Modelin (API anahtarı kontrolü yapılandırmada yapılır) başlatılıp başlatılmadığını kontrol et
    # app.py'nin başındaki 'model = None' ve try/except bloğunu kullanıyoruz
    if not model:
        click.echo(click.style("  ❌ HATA: Gemini modeli (model objesi) başlatılamamış.", fg='red'))
        click.echo(click.style("     .env dosyasındaki GEMINI_API_KEY'in geçerli olduğundan", fg='red'))
        click.echo(click.style("     ve app.py başlarken API yapılandırma hatası olmadığından emin olun.", fg='red'))
        return
    else:
         click.echo(click.style(f"  ✅ Gemini modeli ('{getattr(model, 'model_name', 'unknown')}') yüklendi.", fg='green'))

    # Örnek Girdiler
    sample_user_answer = "Yüksek doz Amoksisilin 10 gün"
    sample_gold_answer = "Yüksek doz Amoksisilin (80-90 mg/kg/gün, 2 dozda) 7-10 gün süreyle"
    sample_category = "Tedavi Planı"

    click.echo(f"  -> Test Girdileri:")
    click.echo(f"     Kullanıcı Yanıtı: '{sample_user_answer}'")
    click.echo(f"     Altın Standart: '{sample_gold_answer}'")
    click.echo(f"     Kategori: '{sample_category}'")
    click.echo("  -> Gemini API çağrılıyor (Bu işlem biraz sürebilir)...")

    try:
        # Fonksiyonu çağır
        score, result_dict = get_semantic_score(sample_user_answer, sample_gold_answer, sample_category)
        
        # Sonuçları al
        reasoning = result_dict.get('reason', 'Gerekçe alınamadı.')
        # raw_response = result_dict.get('raw', 'Ham yanıt alınamadı.')

        click.echo(click.style("  ✅ API Yanıtı Başarılı:", fg='green'))
        click.echo(f"     Skor: {score}")
        click.echo(f"     Gerekçe: {reasoning}")

        # Skorun formatını basitçe kontrol et
        if isinstance(score, int) and 0 <= score <= 100:
             click.echo(click.style("  ✅ Skor formatı geçerli (0-100 arası tamsayı).", fg='green'))
        else:
             click.echo(click.style(f"  ⚠️ UYARI: Skor formatı beklenmedik: {score} (Tip: {type(score)})", fg='yellow'))
             
    except Exception as e:
        click.echo(click.style(f"\n  💥 KRİTİK HATA: API çağrısı sırasında hata oluştu: {e}", fg='red', bold=True))
        click.echo(click.style("     API Anahtarının geçerliliğini, .env dosyasını, internet bağlantısını ve Gemini API durumunu kontrol edin.", fg='yellow'))

@app.cli.command('test-analysis')
@click.option('--research-id', type=int, default=None, help='Test edilecek araştırma IDsi (varsayılan: tüm aktif araştırmalar)')
@with_appcontext
def test_analysis_command(research_id):
    """
    Belirtilen araştırma(lar) için istatistiksel analiz fonksiyonlarını test eder.
    """
    click.echo(click.style("İstatistiksel Analiz Fonksiyonları Test Ediliyor...", fg='yellow', bold=True))

    researches_to_test = []
    if research_id:
        research = db.session.get(Research, research_id)
        if research:
            researches_to_test.append(research)
        else:
            click.echo(click.style(f"  ❌ HATA: Araştırma ID {research_id} bulunamadı.", fg='red'))
            return
    else:
        researches_to_test = Research.query.filter_by(is_active=True).all()
        if not researches_to_test:
             click.echo(click.style("  ⚠️ UYARI: Test edilecek aktif araştırma bulunamadı.", fg='yellow'))
             return
        click.echo(f"  -> {len(researches_to_test)} aktif araştırma test edilecek.")

    overall_success = True

    for research in researches_to_test:
        click.echo("-" * 40)
        click.echo(f"  ℹ️ Araştırma: '{research.title}' (ID: {research.id})")
        
        try:
            # 1. Veri Çekme Testi
            click.echo("    - Veri çekme (get_research_responses_df)... ", nl=False)
            df = get_research_responses_df(research.id)
            if df.empty:
                click.echo(click.style("Veri Yok/Boş DataFrame", fg='cyan'))
                # Veri yoksa diğer testleri atla
                continue 
            else:
                click.echo(click.style(f"OK ({len(df)} yanıt bulundu)", fg='green'))

            # 2. Katılımcı İstatistikleri Testi
            click.echo("    - Katılımcı istatistikleri (calculate_participant_stats)... ", nl=False)
            participant_stats = calculate_participant_stats(df.copy()) # Orijinal df'i değiştirmemek için kopya gönder
            if participant_stats and isinstance(participant_stats, dict) and 'total_responses' in participant_stats:
                click.echo(click.style("OK", fg='green'))
            else:
                click.echo(click.style("HATA/Eksik Sonuç", fg='red', bold=True))
                overall_success = False
                
            # 3. Bilimsel Analiz Testi
            click.echo("    - Bilimsel analiz (calculate_scientific_analytics)... ", nl=False)
            scientific_analytics_result = calculate_scientific_analytics(df.copy()) # Orijinal df'i değiştirmemek için kopya gönder
            if scientific_analytics_result and isinstance(scientific_analytics_result, dict) and 'summary' in scientific_analytics_result:
                 click.echo(click.style("OK", fg='green'))
            else:
                 # Skorlar henüz hesaplanmadıysa None dönebilir, bu bir hata sayılmamalı
                 if scientific_analytics_result is None and not df.empty:
                      click.echo(click.style("Sonuç Yok (Skorlar hesaplanmamış olabilir?)", fg='cyan'))
                 elif scientific_analytics_result is None and df.empty:
                      click.echo(click.style("Veri Yok", fg='cyan')) # Zaten yukarıda yakalanmalıydı ama garanti olsun
                 else: # Beklenmedik durum
                      click.echo(click.style("HATA/Eksik Sonuç", fg='red', bold=True))
                      overall_success = False

        except Exception as e:
            click.echo(click.style(f"\n      💥 KRİTİK HATA: {e}", fg='red', bold=True))
            overall_success = False

    click.echo("=" * 40)
    if overall_success:
         click.echo(click.style("Tüm analiz testleri başarıyla tamamlandı (veya veri yoktu).", fg='green', bold=True))
    else:
         click.echo(click.style("Analiz testleri sırasında bazı hatalar oluştu.", fg='yellow'))

@app.cli.command('enqueue-scoring')
@click.option('--research-id', required=True, type=int, help='Puanlama görevleri başlatılacak araştırma IDsi')
@with_appcontext
def enqueue_scoring_command(research_id):
    """
    Belirtilen araştırmadaki puanlanmamış yanıtlar için 
    asenkron puanlama görevlerini başlatır.
    Redis ve RQ worker çalışıyor olmalıdır.
    """
    # queue nesnesinin tanımlı olduğundan emin olun
    try:
        q = queue
    except NameError:
        click.echo(click.style("HATA: 'queue' nesnesi tanımlı değil. app içinde redis bağlantısı ve queue oluşturulduğundan emin olun.", fg='red'))
        return

    research = db.session.get(Research, research_id)
    if not research:
        click.echo(click.style(f"HATA: Araştırma ID {research_id} bulunamadı.", fg='red'))
        return

    unscored_responses = UserResponse.query.join(Case).filter(
        Case.research_id == research_id,
        UserResponse.scores == None
    ).all()

    if not unscored_responses:
        click.echo(click.style(f"'{research.title}' araştırmasında puanlanacak yeni yanıt bulunamadı.", fg='green'))
        return

    click.echo(f"'{research.title}' araştırması için {len(unscored_responses)} adet puanlama görevi kuyruğa ekleniyor...")

    enqueued_count = 0
    error_count = 0
    for response in unscored_responses:
        try:
            q.enqueue('tasks.score_and_store_response', response.id, job_timeout=600)
            enqueued_count += 1
        except Exception as e:
            click.echo(click.style(f"  HATA: Yanıt ID {response.id} kuyruğa eklenemedi: {e}", fg='red'))
            error_count += 1

    click.echo(f"Başarıyla kuyruğa eklenen görev sayısı: {enqueued_count}")
    if error_count > 0:
         click.echo(click.style(f"Kuyruğa eklenemeyen görev sayısı: {error_count}", fg='yellow'))
    click.echo("RQ worker'ın görevleri işlemesini bekleyin.")

# --- API BLUEPRINT KAYDI ---
try:
    from api_routes import api_bp
    app.register_blueprint(api_bp)
    print("✓ API Blueprint başarıyla kaydedildi: /api/v1")
except ImportError as e:
    print(f"UYARI: API Blueprint yüklenemedi: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)

