# -*- coding: utf-8 -*-
"""
LLM_Research - Bilimsel Veri Toplama Platformu (Sürüm 2.0)
Bu sürüm, asenkron puanlama için Redis/RQ kullanır ve
Railway (PostgreSQL) ile yerel (SQLite) geliştirmeyi destekler.
"""

# --- 1. GEREKLİ KÜTÜPHANELER ---
import os
import json
import csv
import io
import random
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from dotenv import load_dotenv
import google.generativeai as genai
from redis import Redis
from rq import Queue
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
    # Railway/PostgreSQL veritabanı
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Yerel SQLite veritabanı
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

# --- 5. VERİTABANI MODELLERİ (TASKS.PY VE DB.SQLITE İLE UYUMLU) ---

class User(UserMixin, db.Model):
    """Kullanıcı bilgilerini (demografi dahil) saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
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
    anamnesis = db.Column(db.Text, nullable=False)       # JSON String
    physical_exam = db.Column(db.Text, nullable=False)   # JSON String
    # gold_standard_response artık ReferenceAnswer tablosunda tutulacak.
    chatgpt_response = db.Column(db.Text, nullable=False) # JSON String
    gemini_response = db.Column(db.Text, nullable=False)  # JSON String
    deepseek_response = db.Column(db.Text, nullable=False)# JSON String
    responses = db.relationship('UserResponse', backref='case', lazy=True)
    reference_answers = db.relationship('ReferenceAnswer', backref='case', lazy=True)

class ReferenceAnswer(db.Model):
    """Vakalar için 'Altın Standart' ve diğer LLM yanıtlarını tutan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    source = db.Column(db.String(100), nullable=False, index=True) # 'gold', 'chatgpt', 'gemini'
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class UserResponse(db.Model):
    """Kullanıcıların vakalara verdiği yanıtları ve ayrıntılı skorları saklayan tablo."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Kullanıcı Girdileri
    user_diagnosis = db.Column(db.Text, nullable=False)
    user_differential = db.Column(db.Text, nullable=False)
    user_tests = db.Column(db.Text, nullable=False)
    user_drug_class = db.Column(db.String(100), nullable=True)
    user_active_ingredient = db.Column(db.String(200), nullable=True)
    user_dosage_notes = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # LLM Değerlendirme Girdileri (tasks.py tarafından doldurulur)
    diagnosis_score = db.Column(db.Float, default=0.0)
    investigation_score = db.Column(db.Float, default=0.0)
    treatment_score = db.Column(db.Float, default=0.0)
    dosage_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float, default=0.0)
    
    # tasks.py'deki JSON gerekçelendirme modeline uyumlu
    score_reasons = db.Column(db.JSON, nullable=True) 
    llm_raw = db.Column(db.JSON, nullable=True) 
    
    # Eski modelden (app.py) gelen sütunlar - uyumluluk için eklendi ama kullanılmayacak.
    # diagnosis_reasoning vb. yerine score_reasons kullanılacak.


# --- 6. YARDIMCI FONKSİYONLAR VE DECORATOR'LAR ---

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login için kullanıcıyı ID'sine göre yükler."""
    return db.session.get(User, int(user_id))

def parse_json_fields(data):
    """Veritabanından gelen JSON string'ini Python dict'ine güvenli bir şekilde çevirir."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}

@app.context_processor
def utility_processor():
    """HTML şablonları içinde parse_json_fields fonksiyonunu kullanılabilir hale getirir."""
    return dict(parse_json=parse_json_fields)

def get_semantic_score(user_answer, gold_standard_answer, category):
    """
    Kullanıcı yanıtını Gemini API ile pragmatik ve anlamsal olarak puanlar.
    Bu fonksiyon artık tasks.py tarafından (arka planda) çağrılır.
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
    """Sadece yönetici kullanıcıların erişebileceği sayfalar için decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def research_setup_required(f):
    """Kullanıcının onam ve demografi adımlarını tamamlamasını zorunlu kılan decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('giris'))
        if not current_user.has_consented:
            return redirect(url_for('consent'))
        if not current_user.profession or current_user.experience is None:
            return redirect(url_for('demographics'))
        return f(*args, **kwargs)
    return decorated_function

# --- 7. ANA UYGULAMA ROUTE'LARI (SAYFALAR) ---

@app.route('/')
@login_required
@research_setup_required
def index():
    """Ana sayfa, vakaları rastgele sıralanmış olarak listeler."""
    cases = Case.query.all()
    random.shuffle(cases)
    return render_template('index.html', cases=cases)

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
@login_required
@research_setup_required
def case_detail(case_id):
    """Vaka detaylarını gösterir, kullanıcıdan yanıt alır ve puanlama görevini kuyruğa ekler."""
    case = db.session.get(Case, case_id)
    if not case:
        flash("Vaka bulunamadı.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Formdan tüm yanıtları al
        diag = request.form['user_diagnosis']
        diff = request.form['user_differential']
        tests = request.form['user_tests']
        drug_class = request.form.get('user_drug_class', '')
        active_ingredient = request.form.get('user_active_ingredient', '')
        dosage_notes = request.form.get('user_dosage_notes', '')
        duration = request.form.get('duration_seconds', 0, type=int)
        
        # Yeni yanıtı veritabanına kaydet (henüz skorlanmamış)
        new_response = UserResponse(
            case_id=case.id, 
            author=current_user, 
            user_diagnosis=diag, 
            user_differential=diff, 
            user_tests=tests, 
            user_drug_class=drug_class, 
            user_active_ingredient=active_ingredient,
            user_dosage_notes=dosage_notes, 
            duration_seconds=duration
            # Skorlar varsayılan olarak 0.0 olacak
        )
        db.session.add(new_response)
        db.session.commit()
        
        # ASENKRON PUANLAMA
        # Puanlama görevini Redis kuyruğuna ekle
        if queue:
            try:
                from tasks import score_and_store_response
                queue.enqueue(score_and_store_response, new_response.id)
                app.logger.info(f"Response {new_response.id} puanlama için kuyruğa eklendi.")
            except Exception as e:
                app.logger.error(f"Redis kuyruğuna eklenirken hata: {e}")
                flash("Yanıtınız kaydedildi ancak puanlama başlatılamadı. Lütfen yöneticiye başvurun.", "danger")
        else:
            app.logger.warning("Redis bağlantısı yok. Asenkron puanlama atlandı.")
            flash("Yanıtınız kaydedildi ancak puanlama sistemi aktif değil.", "warning")

        # Kullanıcıyı sonuçlar sayfasına yönlendir
        # (Sonuçlar hemen görünmeyebilir, tasks.py'nin çalışması gerekir)
        flash("Yanıtınız kaydedildi ve puanlama için sıraya alındı. Sonuçlar birkaç dakika içinde hazır olacaktır.", "info")
        return redirect(url_for('results', response_id=new_response.id))
    
    return render_template('case.html', case=case)

@app.route('/results/<int:response_id>')
@login_required
def results(response_id):
    """Skorları ve AI karşılaştırma tablosunu gösterir."""
    user_response = db.session.get(UserResponse, response_id)
    if not user_response:
        flash("Yanıt bulunamadı.", "danger")
        return redirect(url_for('index'))
    
    # Sadece kendi yanıtını veya admin ise tüm yanıtları görmesine izin ver
    if user_response.user_id != current_user.id and not current_user.is_admin:
        flash("Bu yanıta erişim yetkiniz yok.", "danger")
        return redirect(url_for('index'))

    # tasks.py'nin doldurmasını beklediğimiz JSON gerekçelerini
    # results.html'nin beklediği formata dönüştür
    reasons = user_response.score_reasons or {}
    user_response.diagnosis_reasoning = reasons.get('diagnosis', 'Puanlama bekleniyor...')
    user_response.investigation_reasoning = reasons.get('tests', 'Puanlama bekleniyor...')
    user_response.treatment_reasoning = reasons.get('treatment', 'Puanlama bekleniyor...')
    user_response.dosage_reasoning = reasons.get('dosage', 'Puanlama bekleniyor...')

    return render_template('results.html', user_response=user_response)

# --- 8. KULLANICI YÖNETİMİ VE ARAŞTIRMA AKIŞI ROUTE'LARI ---

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    """Şifresiz giriş/kayıt sayfası."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        if not email:
            flash('Lütfen geçerli bir e-posta adresi girin.', 'danger')
            return redirect(url_for('giris'))

        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Sisteme ilk giren kullanıcıyı otomatik olarak admin yap
            is_first_user_admin = User.query.count() == 0
            user = User(email=email, is_admin=is_first_user_admin)
            db.session.add(user)
            db.session.commit()
            flash('Araştırmamıza hoş geldiniz! Lütfen devam edin.', 'success')
        
        login_user(user, remember=True)
        
        # Yönlendirme mantığı (Onam/Demografi kontrolü)
        if not user.has_consented:
            return redirect(url_for('consent'))
        if not user.profession or user.experience is None:
            return redirect(url_for('demographics'))
        
        return redirect(url_for('index'))

    return render_template('giris.html')

@app.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    """Bilgilendirilmiş onam sayfası."""
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
    """Demografik bilgi toplama sayfası."""
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
    """Kullanıcı çıkış işlemi."""
    logout_user()
    return redirect(url_for('giris'))

@app.route('/yanitlarim')
@login_required
def my_responses():
    """Kullanıcının kendi geçmiş yanıtlarını listeler."""
    responses = UserResponse.query.filter_by(user_id=current_user.id).order_by(UserResponse.created_at.desc()).all()
    return render_template('my_responses.html', responses=responses)

# --- 9. YÖNETİCİ PANELİ ROUTE'LARI ---

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Yönetici paneli ana sayfası."""
    return render_template('admin.html', 
                           user_count=User.query.count(), 
                           response_count=UserResponse.query.count(), 
                           case_count=Case.query.count())

@app.route('/admin/upload_csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    """CSV formatında toplu vaka yükleme işlemi. (JSON tercih edilir)"""
    flash('CSV yükleme şimdilik devre dışı, lütfen JSON kullanın.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_json', methods=['POST'])
@login_required
@admin_required
def upload_json():
    """JSON formatında toplu vaka yükleme işlemi."""
    json_text = request.form.get('json_text')
    json_file = request.files.get('json_file')
    raw_data = None
    
    if json_text:
        raw_data = json_text
    elif json_file and json_file.filename != '':
        try:
            raw_data = json_file.stream.read().decode("UTF8")
        except Exception as e:
            flash(f'Dosya okunurken hata: {e}', 'danger')
            return redirect(url_for('admin_panel'))
            
    if not raw_data:
        flash('Yüklenecek JSON verisi bulunamadı.', 'danger')
        return redirect(url_for('admin_panel'))
        
    try:
        cases_data = json.loads(raw_data)
        if not isinstance(cases_data, list):
            raise ValueError("JSON bir liste formatında olmalıdır: [...]")
            
        cases_added_count = 0
        for case_obj in cases_data:
            # Yeni Vaka oluştur
            new_case = Case(
                title=case_obj.get('title', 'Başlıksız Vaka'),
                anamnesis=json.dumps(case_obj.get('anamnesis', {})),
                physical_exam=json.dumps(case_obj.get('physical_exam', {})),
                # AI yanıtları için eski sütunları doldur (results.html uyumluluğu için)
                chatgpt_response=json.dumps(case_obj.get('chatgpt_response', {})),
                gemini_response=json.dumps(case_obj.get('gemini_response', {})),
                deepseek_response=json.dumps(case_obj.get('deepseek_response', {}))
            )
            db.session.add(new_case)
            db.session.commit() # Case'in ID alması için commit et

            # ReferenceAnswer'ları oluştur (tasks.py'nin ihtiyaç duyduğu)
            ref_answers = [
                ReferenceAnswer(case_id=new_case.id, source='gold', content=case_obj.get('gold_standard_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='chatgpt', content=case_obj.get('chatgpt_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='gemini', content=case_obj.get('gemini_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='deepseek', content=case_obj.get('deepseek_response', {}))
            ]
            db.session.add_all(ref_answers)
            cases_added_count += 1
            
        db.session.commit()
        flash(f'{cases_added_count} yeni vaka ve referans yanıtları JSON üzerinden yüklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Vakalar kaydedilirken hata: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/export_csv')
@login_required
@admin_required
def export_csv():
    """Tüm yanıt veri setini CSV formatında indirir."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Kapsamlı başlık satırı
    header = [
        'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil', 
        'vaka_id', 'vaka_baslik', 'yanit_suresi_saniye', 'yanit_tarihi',
        'kullanici_tani', 'kullanici_ayirici_tani', 'kullanici_tetkik', 
        'kullanici_ilac_grubu', 'kullanici_etken_madde', 'kullanici_doz_notlari',
        'tani_skoru', 'tetkik_skoru', 'tedavi_skoru', 'doz_skoru', 'final_skor',
        'tani_gerekcesi', 'tetkik_gerekcesi', 'tedavi_gerekcesi', 'doz_gerekcesi',
        'altin_standart_tani', 'altin_standart_tetkik', 'altin_standart_tedavi', 'altin_standart_doz',
        'chatgpt_tani', 'chatgpt_tetkik', 'chatgpt_tedavi', 'chatgpt_doz',
        'gemini_tani', 'gemini_tetkik', 'gemini_tedavi', 'gemini_doz',
        'deepseek_tani', 'deepseek_tetkik', 'deepseek_tedavi', 'deepseek_doz'
    ]
    writer.writerow(header)
    
    for resp in UserResponse.query.all():
        def clean_text(text):
            return text.replace('\n', ' ').replace('\r', '') if text else ''
            
        # Gerekçeleri JSON'dan al
        reasons = resp.score_reasons or {}
        
        # AI Yanıtlarını Case tablosundaki eski JSON string'lerinden al
        chatgpt = parse_json_fields(resp.case.chatgpt_response)
        gemini = parse_json_fields(resp.case.gemini_response)
        deepseek = parse_json_fields(resp.case.deepseek_response)
        
        # Altın Standart yanıtı ReferenceAnswer tablosundan al
        gold_ref = ReferenceAnswer.query.filter_by(case_id=resp.case_id, source='gold').first()
        gold = gold_ref.content if gold_ref else {}
        
        row = [
            resp.id, resp.author.id, resp.author.profession, resp.author.experience,
            resp.case.id, resp.case.title, resp.duration_seconds, resp.created_at.isoformat(),
            clean_text(resp.user_diagnosis), clean_text(resp.user_differential), clean_text(resp.user_tests),
            resp.user_drug_class, resp.user_active_ingredient, clean_text(resp.user_dosage_notes),
            resp.diagnosis_score, resp.investigation_score, resp.treatment_score, resp.dosage_score, resp.final_score,
            clean_text(reasons.get('diagnosis')), clean_text(reasons.get('tests')),
            clean_text(reasons.get('treatment')), clean_text(reasons.get('dosage')),
            gold.get('tanı'), gold.get('tetkik'), gold.get('tedavi_plani'), gold.get('dozaj'),
            chatgpt.get('tanı'), chatgpt.get('tetkik'), chatgpt.get('tedavi_plani'), chatgpt.get('dozaj'),
            gemini.get('tanı'), gemini.get('tetkik'), gemini.get('tedavi_plani'), gemini.get('dozaj'),
            deepseek.get('tanı'), deepseek.get('tetkik'), deepseek.get('tedavi_plani'), deepseek.get('dozaj')
        ]
        writer.writerow(row)
        
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=LLM_Research_Dataset_Final.csv"})

# --- 10. VERİTABANI BAŞLATMA (SEEDING) ---

def seed_database():
    """Uygulama ilk çalıştığında veritabanı boşsa başlangıç verilerini ekler."""
    if Case.query.first() is not None:
        print("Veritabanı zaten veri içeriyor, seeding atlandı.")
        return

    print("Veritabanı boş, başlangıç vakaları ekleniyor...")
    initial_cases_data = [
        {
            "title": "Vaka 1: Huzursuz Bebek",
            "anamnesis": {"Hasta": "18 aylık, erkek.", "Şikayet": "Huzursuzluk, ateş ve sol kulağını çekiştirme."},
            "physical_exam": {"Bulgu": "Sol kulak zarında hiperemi ve bombeleşme."},
            "gold_standard_response": {"tanı": "Akut Otitis Media", "tetkik": "Ek tetkik gerekmez", "tedavi_plani": "Antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
            "chatgpt_response": {"tanı": "Akut Otitis Media", "tetkik": "Gerekli değil", "tedavi_plani": "Amoksisilin", "dozaj": "90 mg/kg/gün"},
            "gemini_response": {"tanı": "Bakteriyel AOM", "tetkik": "Endike değil", "tedavi_plani": "Amoksisilin-Klavulanat", "dozaj": "Standart doz"},
            "deepseek_response": {"tanı": "Sol Akut Otitis Media", "tetkik": "İstenmez", "tedavi_plani": "Antibiyotik", "dozaj": "Amoksisilin tedavisi"}
        },
        {
            "title": "Vaka 2: Öksüren Çocuk",
            "anamnesis": {"Hasta": "4 yaşında, kız.", "Şikayet": "3 gündür ateş, öksürük ve hızlı nefes alma."},
            "physical_exam": {"Bulgu": "Sağ akciğer alt zonda krepitan raller."},
            "gold_standard_response": {"tanı": "Toplum Kökenli Pnömoni", "tetkik": "Akciğer Grafisi", "tedavi_plani": "Oral antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
            "chatgpt_response": {"tanı": "Pnömoni", "tetkik": "Akciğer grafisi, TKS", "tedavi_plani": "Amoksisilin", "dozaj": "80-100 mg/kg/gün"},
            "gemini_response": {"tanı": "Sağ Alt Lob Pnömonisi", "tetkik": "Akciğer Röntgeni", "tedavi_plani": "Destekleyici bakım", "dozaj": "Oral amoksisilin"},
            "deepseek_response": {"tanı": "Pnömoni", "tetkik": "Göğüs X-ray", "tedavi_plani": "Antibiyotik", "dozaj": "Uygun antibiyotik"}
        }
    ]
    
    try:
        for case_data in initial_cases_data:
            # Önce Case'i oluştur
            new_case = Case(
                title=case_data.get("title"),
                anamnesis=json.dumps(case_data.get("anamnesis", {})),
                physical_exam=json.dumps(case_data.get("physical_exam", {})),
                chatgpt_response=json.dumps(case_data.get("chatgpt_response", {})),
                gemini_response=json.dumps(case_data.get("gemini_response", {})),
                deepseek_response=json.dumps(case_data.get("deepseek_response", {}))
            )
            db.session.add(new_case)
            db.session.commit() # ID alması için
            
            # Sonra ilişkili ReferenceAnswer'ları oluştur
            ref_answers = [
                ReferenceAnswer(case_id=new_case.id, source='gold', content=case_data.get('gold_standard_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='chatgpt', content=case_data.get('chatgpt_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='gemini', content=case_data.get('gemini_response', {})),
                ReferenceAnswer(case_id=new_case.id, source='deepseek', content=case_data.get('deepseek_response', {}))
            ]
            db.session.add_all(ref_answers)
            
        db.session.commit()
        print(f"{len(initial_cases_data)} başlangıç vakası ve referansları eklendi.")
    except Exception as e:
        db.session.rollback()
        print(f"Seeding sırasında hata: {e}")

# --- 11. UYGULAMAYI ÇALIŞTIRMA ---
if __name__ == '__main__':
    # 'python app.py' ile çalıştırıldığında yerel (SQLite) veritabanını oluşturur.
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
