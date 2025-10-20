# -*- coding: utf-8 -*-
"""
LLM_Research - Bilimsel Veri Toplama Platformu
Bu Flask uygulaması, hekimlerin pediatrik vaka senaryolarına verdiği yanıtları toplar,
bu yanıtları Google Gemini API kullanarak anlamsal olarak puanlar ve
bilimsel bir makale için analiz edilebilir bir veri seti oluşturur.
"""

# Gerekli kütüphanelerin import edilmesi
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
import google.generativeai as genai  # <-- EKSİK OLAN VE EKLENEN KRİTİK SATIR

# --- 1. UYGULAMA KURULUMU VE YAPILANDIRMA ---

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nihai-arastirma-icin-gizli-anahtar-tam-versiyon'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'giris'
login_manager.login_message = "Bu araştırma platformunu kullanmak için lütfen giriş yapın."
login_manager.login_message_category = "info"

# --- 2. GEMINI API YAPILANDIRMASI ---

model = None
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    print("Gemini API (gemini-2.5-flash) başarıyla yapılandırıldı.")
except Exception as e:
    print(f"HATA: Gemini API yapılandırılamadı: {e}")

# --- 3. VERİTABANI MODELLERİ ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profession = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    has_consented = db.Column(db.Boolean, default=False)
    responses = db.relationship('UserResponse', backref='author', lazy=True)

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    anamnesis = db.Column(db.Text, nullable=False)
    physical_exam = db.Column(db.Text, nullable=False)
    gold_standard_response = db.Column(db.Text, nullable=False)
    chatgpt_response = db.Column(db.Text, nullable=False)
    gemini_response = db.Column(db.Text, nullable=False)
    deepseek_response = db.Column(db.Text, nullable=False)
    responses = db.relationship('UserResponse', backref='case', lazy=True)

class UserResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_diagnosis = db.Column(db.Text, nullable=False)
    user_differential = db.Column(db.Text, nullable=False)
    user_tests = db.Column(db.Text, nullable=False)
    user_drug_class = db.Column(db.String(100), nullable=True)
    user_active_ingredient = db.Column(db.String(200), nullable=True)
    user_dosage_notes = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    diagnosis_score = db.Column(db.Integer, default=0)
    investigation_score = db.Column(db.Integer, default=0)
    treatment_score = db.Column(db.Integer, default=0)
    dosage_score = db.Column(db.Integer, default=0)
    final_score = db.Column(db.Integer, default=0)
    diagnosis_reasoning = db.Column(db.Text, nullable=True)
    investigation_reasoning = db.Column(db.Text, nullable=True)
    treatment_reasoning = db.Column(db.Text, nullable=True)
    dosage_reasoning = db.Column(db.Text, nullable=True)

# --- 4. YARDIMCI FONKSİYONLAR VE DECORATOR'LAR ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def parse_json_fields(data):
    try: return json.loads(data)
    except (json.JSONDecodeError, TypeError): return {}

def get_semantic_score(user_answer, gold_standard_answer, category):
    if not model: return 0, "Hakem LLM modeli yüklenemediği için skorlama yapılamadı."
    prompt = f"""
    Sen, bir hekimin vaka yanıtının '{category}' bölümünü değerlendiren, pragmatik bir klinik uzmansın.
    "Kullanıcı Yanıtı"nın, hastanın doğru tedavi edilmesini sağlayacak kadar YETERLİ olup olmadığını 0-100 arasında puanla.
    Yanıtını SADECE şu JSON formatında ver: {{ "score": <sayı>, "reasoning": "<1 cümlelik gerekçe>" }}
    ---
    Altın Standart Yanıt ({category}): "{gold_standard_answer}"
    ---
    Kullanıcı Yanıtı ({category}): "{user_answer}"
    ---
    """
    try:
        response = model.generate_content(prompt); result = json.loads(response.text)
        return int(result.get("score", 0)), result.get("reasoning", "Gerekçe alınamadı.")
    except Exception as e:
        print(f"Gemini API hatası ({category}): {e}"); return 0, f"API Hatası: {e}"

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger"); return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def research_setup_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_consented: return redirect(url_for('consent'))
        if not current_user.profession or current_user.experience is None: return redirect(url_for('demographics'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def utility_processor(): return dict(parse_json=parse_json_fields)

# --- 5. ANA UYGULAMA ROUTE'LARI (SAYFALAR) ---

@app.route('/')
@login_required
@research_setup_required
def index():
    cases = Case.query.all(); random.shuffle(cases)
    return render_template('index.html', cases=cases)

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
@login_required
@research_setup_required
def case_detail(case_id):
    case = Case.query.get_or_404(case_id)
    if request.method == 'POST':
        diag, diff, tests = request.form['user_diagnosis'], request.form['user_differential'], request.form['user_tests']
        drug_class, ing, notes = request.form.get('user_drug_class', ''), request.form.get('user_active_ingredient', ''), request.form.get('user_dosage_notes', '')
        duration = request.form.get('duration_seconds', 0, type=int)
        gold_data = parse_json_fields(case.gold_standard_response)
        
        diag_score, diag_reason = get_semantic_score(diag, gold_data.get('tanı', ''), "Tanı")
        test_score, test_reason = get_semantic_score(tests, gold_data.get('tetkik', ''), "Tetkik")
        treat_score, treat_reason = get_semantic_score(f"{drug_class} {ing}", gold_data.get('tedavi_plani', ''), "Tedavi Planı")
        dose_score, dose_reason = get_semantic_score(notes, gold_data.get('dozaj', ''), "Dozaj")
        
        final_score = (diag_score + test_score + treat_score + dose_score) // 4
        
        new_response = UserResponse(
            case_id=case.id, author=current_user, user_diagnosis=diag, user_differential=diff, 
            user_tests=tests, user_drug_class=drug_class, user_active_ingredient=ing,
            user_dosage_notes=notes, duration_seconds=duration,
            diagnosis_score=diag_score, investigation_score=test_score, treatment_score=treat_score, dosage_score=dose_score,
            final_score=final_score, diagnosis_reasoning=diag_reason, investigation_reasoning=test_reason,
            treatment_reasoning=treat_reason, dosage_reasoning=dose_reason
        )
        db.session.add(new_response); db.session.commit()
        return redirect(url_for('results', response_id=new_response.id))
    
    return render_template('case.html', case=case)

@app.route('/results/<int:response_id>')
@login_required
def results(response_id):
    user_response = UserResponse.query.get_or_404(response_id)
    return render_template('results.html', user_response=user_response)

# --- 6. KULLANICI YÖNETİMİ VE ARAŞTIRMA AKIŞI ROUTE'LARI ---

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        if not email: flash('Lütfen geçerli bir e-posta adresi girin.', 'danger'); return redirect(url_for('giris'))
        user = User.query.filter_by(email=email).first()
        if not user:
            is_first_user_admin = User.query.count() == 0
            user = User(email=email, is_admin=is_first_user_admin)
            db.session.add(user); db.session.commit()
            flash('Araştırmamıza hoş geldiniz! Lütfen devam edin.', 'success')
        login_user(user, remember=True)
        return redirect(url_for('index'))
    return render_template('giris.html')

@app.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    if current_user.has_consented: return redirect(url_for('demographics'))
    if request.method == 'POST':
        current_user.has_consented = True; db.session.commit()
        return redirect(url_for('demographics'))
    return render_template('consent.html')

@app.route('/demographics', methods=['GET', 'POST'])
@login_required
def demographics():
    if not current_user.has_consented: return redirect(url_for('consent'))
    if current_user.profession: return redirect(url_for('index'))
    if request.method == 'POST':
        current_user.profession = request.form['profession']
        current_user.experience = int(request.form['experience'])
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('demographics.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('giris'))

@app.route('/yanitlarim')
@login_required
def my_responses():
    return render_template('my_responses.html', responses=current_user.responses)

# --- 7. YÖNETİCİ PANELİ ROUTE'LARI ---

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    return render_template('admin.html', user_count=User.query.count(), response_count=UserResponse.query.count(), case_count=Case.query.count())

@app.route('/admin/upload_csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    # ... (Bu fonksiyon aynı kalabilir) ...
    flash('CSV yükleme şimdilik devre dışı, lütfen JSON kullanın.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/upload_json', methods=['POST'])
@login_required
@admin_required
def upload_json():
    # ... (Bu fonksiyon aynı kalabilir) ...
    json_text = request.form.get('json_text'); json_file = request.files.get('json_file'); raw_data = None
    if json_text: raw_data = json_text
    elif json_file and json_file.filename != '':
        try: raw_data = json_file.stream.read().decode("UTF8")
        except Exception as e: flash(f'Dosya okunurken hata: {e}', 'danger'); return redirect(url_for('admin_panel'))
    if not raw_data: flash('Yüklenecek JSON verisi bulunamadı.', 'danger'); return redirect(url_for('admin_panel'))
    try:
        cases_data = json.loads(raw_data)
        if not isinstance(cases_data, list): raise ValueError("JSON bir liste formatında olmalıdır: [...]")
        cases_to_add = []
        for case_obj in cases_data:
            cases_to_add.append(Case(
                title=case_obj.get('title', 'Başlıksız Vaka'), anamnesis=json.dumps(case_obj.get('anamnesis', {})),
                physical_exam=json.dumps(case_obj.get('physical_exam', {})), gold_standard_response=json.dumps(case_obj.get('gold_standard_response', {})),
                chatgpt_response=json.dumps(case_obj.get('chatgpt_response', {})), gemini_response=json.dumps(case_obj.get('gemini_response', {})),
                deepseek_response=json.dumps(case_obj.get('deepseek_response', {})) ))
        db.session.add_all(cases_to_add); db.session.commit()
        flash(f'{len(cases_to_add)} yeni vaka JSON üzerinden yüklendi.', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Vakalar kaydedilirken hata: {e}', 'danger')
    return redirect(url_for('admin_panel'))


@app.route('/admin/export_csv')
@login_required
@admin_required
def export_csv():
    # ... (Bu fonksiyon aynı kalabilir) ...
    output = io.StringIO(); writer = csv.writer(output)
    header = [ 'yanit_id', 'kullanici_id', 'kullanici_unvan', 'kullanici_deneyim_yil', 'vaka_id', 'vaka_baslik', 'yanit_suresi_saniye', 'kullanici_tani', 'kullanici_ayirici_tani', 'kullanici_tetkik', 'kullanici_ilac_grubu', 'kullanici_etken_madde', 'kullanici_doz_notlari', 'tani_skoru', 'tetkik_skoru', 'tedavi_skoru', 'doz_skoru', 'final_skor' ]
    writer.writerow(header)
    for resp in UserResponse.query.all():
        def clean_text(text): return text.replace('\n', ' ').replace('\r', ' ') if text else ''
        row = [ resp.id, resp.author.id, resp.author.profession, resp.author.experience, resp.case.id, resp.case.title, resp.duration_seconds, clean_text(resp.user_diagnosis), clean_text(resp.user_differential), clean_text(resp.user_tests), resp.user_drug_class, resp.user_active_ingredient, clean_text(resp.user_dosage_notes), resp.diagnosis_score, resp.investigation_score, resp.treatment_score, resp.dosage_score, resp.final_score ]
        writer.writerow(row)
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=LLM_Research_Dataset_Final.csv"})

# --- 8. VERİTABANI BAŞLATMA (SEEDING) ---

def seed_database():
    if Case.query.first() is None:
        print("Veritabanı boş, başlangıç vakaları ekleniyor...")
        initial_cases_data = [
            {
                "title": "Vaka 1: Huzursuz Bebek", "anamnesis": {"Hasta": "18 aylık", "Şikayet": "Huzursuzluk, ateş"}, "physical_exam": {"Bulgu": "Sol kulak zarında hiperemi"},
                "gold_standard_response": {"tanı": "Akut Otitis Media", "tetkik": "Ek tetkik gerekmez", "tedavi_plani": "Antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
                "chatgpt_response": {"tanı": "Akut Otitis Media", "tetkik": "Gerekli değil", "tedavi_plani": "Amoksisilin", "dozaj": "90 mg/kg/gün"},
                "gemini_response": {"tanı": "Bakteriyel AOM", "tetkik": "Endike değil", "tedavi_plani": "Amoksisilin-Klavulanat", "dozaj": "Standart doz"},
                "deepseek_response": {"tanı": "Sol Akut Otitis Media", "tetkik": "İstenmez", "tedavi_plani": "Antibiyotik", "dozaj": "Amoksisilin"}
            },
            {
                "title": "Vaka 2: Öksüren Çocuk", "anamnesis": {"Hasta": "4 yaşında", "Şikayet": "Ateş, öksürük"}, "physical_exam": {"Bulgu": "Sağ akciğerde raller"},
                "gold_standard_response": {"tanı": "Toplum Kökenli Pnömoni", "tetkik": "Akciğer Grafisi", "tedavi_plani": "Oral antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
                "chatgpt_response": {"tanı": "Pnömoni", "tetkik": "Akciğer grafisi", "tedavi_plani": "Amoksisilin", "dozaj": "80-100 mg/kg/gün"},
                "gemini_response": {"tanı": "Sağ Alt Lob Pnömonisi", "tetkik": "Akciğer Röntgeni", "tedavi_plani": "Destekleyici bakım", "dozaj": "Oral amoksisilin"},
                "deepseek_response": {"tanı": "Pnömoni", "tetkik": "Göğüs X-ray", "tedavi_plani": "Antibiyotik", "dozaj": "Uygun antibiyotik"}
            }
        ]
        cases_to_add = [Case(**{k: json.dumps(v) if isinstance(v, dict) else v for k, v in case_data.items()}) for case_data in initial_cases_data]
        db.session.add_all(cases_to_add); db.session.commit()
        print(f"{len(cases_to_add)} başlangıç vakası eklendi.")

# --- 9. UYGULAMAYI ÇALIŞTIRMA ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(host='0.0.0.0', port=8080)
