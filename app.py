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
    """Tıbbi vaka senaryolarını ve AI yanıtlarını saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    anamnesis = db.Column(db.Text, nullable=False)
    physical_exam = db.Column(db.Text, nullable=False)
    chatgpt_response = db.Column(db.Text, nullable=False)
    gemini_response = db.Column(db.Text, nullable=False)
    deepseek_response = db.Column(db.Text, nullable=False)
    responses = db.relationship('UserResponse', backref='case', lazy=True)
    reference_answers = db.relationship('ReferenceAnswer', backref='case', lazy=True)

class ReferenceAnswer(db.Model):
    """Vakalar için 'Altın Standart' yanıtlarını tutan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    source = db.Column(db.String(100), nullable=False, index=True) # 'gold', 'chatgpt' etc.
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class UserResponse(db.Model):
    """Kullanıcıların vakalara verdiği yanıtları ve skorları saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # User Inputs
    user_diagnosis = db.Column(db.Text, nullable=False)
    user_differential = db.Column(db.Text, nullable=False)
    user_tests = db.Column(db.Text, nullable=False)
    user_drug_class = db.Column(db.String(100), nullable=True)
    user_active_ingredient = db.Column(db.String(200), nullable=True)
    user_dosage_notes = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    job_id = db.Column(db.String(36), nullable=True) # For polling
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Scoring Results from tasks.py
    diagnosis_score = db.Column(db.Float, default=0.0)
    investigation_score = db.Column(db.Float, default=0.0)
    treatment_score = db.Column(db.Float, default=0.0)
    dosage_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float, default=0.0)
    score_reasons = db.Column(db.JSON, nullable=True)
    llm_raw = db.Column(db.JSON, nullable=True)

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
def index():
    cases = Case.query.all()
    random.shuffle(cases)
    return render_template('index.html', cases=cases)

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
@login_required
@research_setup_required
def case_detail(case_id):
    case = db.session.get(Case, case_id)
    if not case:
        flash("Vaka bulunamadı.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_response = UserResponse(
            case_id=case.id,
            author=current_user,
            user_diagnosis=request.form['user_diagnosis'],
            user_differential=request.form['user_differential'],
            user_tests=request.form['user_tests'],
            user_drug_class=request.form.get('user_drug_class', ''),
            user_active_ingredient=request.form.get('user_active_ingredient', ''),
            user_dosage_notes=request.form.get('user_dosage_notes', ''),
            duration_seconds=request.form.get('duration_seconds', 0, type=int),
            job_id=None # Will be set after enqueuing
        )
        db.session.add(new_response)
        db.session.commit()

        if queue:
            try:
                from tasks import score_and_store_response
                job = queue.enqueue(score_and_store_response, new_response.id)
                new_response.job_id = job.id
                db.session.commit()
                app.logger.info(f"Response {new_response.id} puanlama için kuyruğa eklendi (Job ID: {job.id}).")
                flash("Yanıtınız kaydedildi ve puanlama için sıraya alındı. Sonuçlar birkaç dakika içinde hazır olacaktır.", "info")
            except Exception as e:
                app.logger.error(f"Redis kuyruğuna eklenirken hata: {e}")
                flash("Yanıtınız kaydedildi ancak puanlama başlatılamadı. Lütfen yöneticiye başvurun.", "danger")
        else:
            app.logger.warning("Redis bağlantısı yok. Asenkron puanlama atlandı.")
            flash("Yanıtınız kaydedildi ancak puanlama sistemi aktif değil.", "warning")

        return redirect(url_for('results', response_id=new_response.id))
    
    return render_template('case.html', case=case)

@app.route('/results/<int:response_id>')
@login_required
def results(response_id):
    user_response = db.session.get(UserResponse, response_id)
    if not user_response:
        flash("Yanıt bulunamadı.", "danger")
        return redirect(url_for('index'))
    
    if user_response.user_id != current_user.id and not current_user.is_admin:
        flash("Bu yanıta erişim yetkiniz yok.", "danger")
        return redirect(url_for('index'))

    reasons = user_response.score_reasons or {}
    user_response.diagnosis_reasoning = reasons.get('diagnosis', 'Puanlama bekleniyor...')
    user_response.investigation_reasoning = reasons.get('tests', 'Puanlama bekleniyor...')
    user_response.treatment_reasoning = reasons.get('treatment', 'Puanlama bekleniyor...')
    user_response.dosage_reasoning = reasons.get('dosage', 'Puanlama bekleniyor...')

    return render_template('results.html', user_response=user_response)

# --- 8. KULLANICI YÖNETİMİ ---

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if current_user.is_authenticated and not current_user.is_admin:
        return redirect(url_for('index'))
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

        return redirect(url_for('index'))

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
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        current_user.profession = request.form['profession']
        current_user.experience = int(request.form['experience'])
        db.session.commit()
        return redirect(url_for('index'))
        
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
@login_required
@admin_required
def admin_panel():
    return render_template('admin.html', 
                           user_count=User.query.count(), 
                           response_count=UserResponse.query.count(), 
                           case_count=Case.query.count())

@app.route('/admin/upload_csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    flash('CSV yükleme şimdilik devre dışı, lütfen JSON kullanın.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_json', methods=['POST'])
@login_required
@admin_required
def upload_json():
    json_text = request.form.get('json_text')
    if not json_text:
        flash('Yüklenecek JSON verisi bulunamadı.', 'danger')
        return redirect(url_for('admin_panel'))
        
    try:
        cases_data = json.loads(json_text)
        if not isinstance(cases_data, list):
            raise ValueError("JSON bir liste formatında olmalıdır: [...]")
            
        cases_added_count = 0
        for case_obj in cases_data:
            new_case = Case(
                title=case_obj.get('title', 'Başlıksız Vaka'),
                anamnesis=json.dumps(case_obj.get('anamnesis', {})),
                physical_exam=json.dumps(case_obj.get('physical_exam', {})),
                chatgpt_response=json.dumps(case_obj.get('chatgpt_response', {})),
                gemini_response=json.dumps(case_obj.get('gemini_response', {})),
                deepseek_response=json.dumps(case_obj.get('deepseek_response', {}))
            )
            db.session.add(new_case)
            db.session.flush()

            ref_answers = [
                ReferenceAnswer(case_id=new_case.id, source='gold', content=case_obj.get('gold_standard_response', {})),
            ]
            db.session.add_all(ref_answers)
            cases_added_count += 1
            
        db.session.commit()
        flash(f'{cases_added_count} yeni vaka JSON üzerinden yüklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Vakalar kaydedilirken hata: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

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
        reasons = resp.score_reasons or {}
        row = [
            resp.id, resp.author.id, resp.author.profession, resp.author.experience,
            resp.case.id, resp.case.title, resp.duration_seconds, resp.created_at.isoformat(),
            resp.user_diagnosis, resp.user_differential, resp.user_tests,
            resp.user_drug_class, resp.user_active_ingredient, resp.user_dosage_notes,
            resp.diagnosis_score, resp.investigation_score, resp.treatment_score, resp.dosage_score, resp.final_score,
            reasons.get('diagnosis'), reasons.get('tests'),
            reasons.get('treatment'), reasons.get('dosage'),
        ]
        writer.writerow(row)
        
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=LLM_Research_Dataset.csv"})

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
        for case_data in initial_cases_data:
            new_case = Case(
                title=case_data.get("title"), anamnesis=json.dumps(case_data.get("anamnesis", {})),
                physical_exam=json.dumps(case_data.get("physical_exam", {})),
                chatgpt_response=json.dumps(case_data.get("chatgpt_response", {})),
                gemini_response=json.dumps(case_data.get("gemini_response", {})),
                deepseek_response=json.dumps(case_data.get("deepseek_response", {}))
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

# --- 11. ASENKRON GÖREV DURUMU (POLLING) ROTASI ---

@app.route('/results/<int:response_id>/status')
@login_required
def get_response_status(response_id):
    ur = db.session.get(UserResponse, response_id)
    
    if not ur or (ur.user_id != current_user.id and not current_user.is_admin):
        return {"status": "error", "message": "Yanıt bulunamadı veya yetki yok."}, 404
    
    if not ur.job_id:
        # Puanlama henüz başlamamış veya bir hata oluşmuş olabilir
        if ur.final_score > 0.0:
            return jsonify_finished_response(ur)
        return {"status": "pending", "message": "Puanlama görevi henüz atanmamış, bekleniyor..."}, 202
        
    if not conn:
        return {"status": "error", "message": "Redis bağlantısı kurulamadı."}, 500
        
    try:
        job = Job.fetch(ur.job_id, connection=conn)
    except Exception as e:
        app.logger.error(f"Redis'ten Job alınırken hata: {e}")
        if ur.final_score > 0.0:
             return jsonify_finished_response(ur)
        return {"status": "error", "message": "Puanlama görevi Redis'te bulunamadı."}, 404

    if job.is_finished:
        db.session.refresh(ur)
        return jsonify_finished_response(ur)
    elif job.is_failed:
        return {"status": "failed", "message": "Puanlama sırasında bir hata oluştu. Lütfen yöneticiye başvurun."}
    else:
        status_message = job.meta.get('status', 'Puanlama sıraya alındı, başlatılıyor...')
        return {"status": "processing", "message": status_message}

def jsonify_finished_response(ur: UserResponse):
    reasons = ur.score_reasons or {}
    return {
        "status": "finished",
        "final_score": ur.final_score,
        "diagnosis_score": ur.diagnosis_score,
        "investigation_score": ur.investigation_score,
        "treatment_score": ur.treatment_score,
        "dosage_score": ur.dosage_score,
        "reasoning": {
            "diagnosis": reasons.get('diagnosis', 'Tamamlandı.'),
            "tests": reasons.get('tests', 'Tamamlandı.'),
            "treatment": reasons.get('treatment', 'Tamamlandı.'),
            "dosage": reasons.get('dosage', 'Tamamlandı.')
        }
    }

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Yönetici paneli için şifreli giriş."""
    # Zaten yönetici oturumu açıksa direkt panele gönder
    if current_user.is_authenticated and current_user.is_admin and session.get('admin_authenticated'):
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.is_admin and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session['admin_authenticated'] = True
            flash('Yönetici paneline başarıyla giriş yapıldı.', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Geçersiz yönetici e-posta veya şifre.', 'danger')

    return render_template('admin_login.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # seed_database()  # Eğer init_db.py kullanıyorsanız burada çalıştırmayın
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))