# test_app.py

import pytest
import json
from app import app, db, User, Research, Case, LLM, UserResponse

@pytest.fixture(scope='session')
def test_client():
    """Tüm test oturumu için TEK BİR test istemcisi ve temiz bir veritabanı oluşturur."""
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

    # Test için temel bir yönetici ve kullanıcı oluştur
    from werkzeug.security import generate_password_hash
    admin = User(
        email='admin@test.com',
        is_admin=True,
        password_hash=generate_password_hash('123456'),
        has_consented=True,
        profession="Admin"
    )
    user = User(
        email='test@kullanici.com',
        has_consented=True,
        profession="Test User",
        experience=5
    )
    db.session.add_all([admin, user])
    db.session.commit()

    yield testing_client

    db.session.remove()
    db.drop_all()
    ctx.pop()

# Dosya başına ekle

def create_test_case_content(title="Test Vaka", questions=None):
    """Test amaçlı uygun yapıda case content oluşturur."""
    if questions is None:
        questions = [{"id": "q1", "label": "Test Soru?"}]
    
    return {
        "title": title,
        "questions": questions,
        "sections": [
            {"title": "Anamnez", "content": ""},
            {"title": "Fizik Muayene", "content": ""}
        ],
        "gold_standard": {
            q.get("id"): "Doğru Cevap" for q in questions
        },
        "llm_responses": {}
    }

# --- 1. Temel Giriş Testi ---

def test_ana_sayfa_yonlendirmesi(test_client):
    """Ana sayfa doğru şekilde yöneltilip yönlendirilmediğini test eder."""
    response = test_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert 'Giriş Yap veya Hesap Oluştur' in response.data.decode('utf-8')

# --- 2. Kullanıcı Kayıt ve Onboarding ---

def test_kullanici_kayit_ve_onboarding_sureci(test_client):
    """Yeni kullanıcının kayıt ve onboarding sürecini test eder."""
    # --- DEĞİŞİKLİK BURADA ---
    # E-postayı, fixture'da oluşturulandan farklı, benzersiz bir e-posta yapıyoruz.
    email = 'onboarding@test.com'
    response = test_client.post('/giris', data={'email': email}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Araştırma Katılım Onayı' in response.data.decode('utf-8') or 'Onam' in response.data.decode('utf-8')

    response = test_client.post('/consent', follow_redirects=True)
    assert response.status_code == 200
    assert 'Katılımcı Bilgileri' in response.data.decode('utf-8') or 'Demografi' in response.data.decode('utf-8')

    response = test_client.post('/demographics', data={'profession': 'Pratisyen Hekim', 'experience': 5}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Mevcut Araştırmalar' in response.data.decode('utf-8') or 'Araştırma' in response.data.decode('utf-8')

    user = User.query.filter_by(email=email).first()
    assert user is not None
    assert user.has_consented is True
    assert user.profession == 'Pratisyen Hekim'

# --- 3. Yönetici Girişi ---

def test_yonetici_giris_ve_panel_erisim(test_client):
    """Yönetici doğru şifreyle giriş yapıp yönetici paneline erişebilir mi?"""
    response = test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Yönetici Ana Paneli' in response.data.decode('utf-8') or 'admin' in response.data.decode('utf-8').lower()

# --- 4. Kullanıcı Vaka Çözüm Akışı ---

def test_kullanici_vaka_cozum_akisi(test_client):
    """Kullanıcı bir araştırmayı baştan sona tamamlayıp final raporunu görebilir mi?"""
    # Önce test araştırması ve vakaları oluştur
    with app.app_context():
        if not Research.query.filter_by(title='Test Araştırması').first():
            research = Research(
                title='Test Araştırması',
                description='Bu bir test araştırmasıdır.',
                is_active=True
            )
            db.session.add(research)
            db.session.flush()

            case = Case(
                research_id=research.id,
                content={
                    "title": "Test Vaka 1",
                    "questions": [{"id": "q1", "label": "Test Soru?"}],
                    # --- EKLENECEK ALANLAR ---
                    "gold_standard": {
                        "q1": "Doğru Cevap"
                    },
                    "llm_responses": {}
                    # ---
                }
            )
            db.session.add(case)
            db.session.commit()

    # Kullanıcı girişi yap
    test_client.post('/giris', data={'email': 'test@kullanici.com'})

    research = Research.query.filter_by(title='Test Araştırması').first()
    response = test_client.get(f'/arastirma/{research.id}', follow_redirects=True)
    assert response.status_code == 200

    case = research.cases[0]
    response = test_client.get(f'/case/{case.id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'Test Vaka 1' in response.data.decode('utf-8')

    response = test_client.post(
        f'/case/{case.id}',
        data={'q1': 'Kullanıcı Cevabı', 'duration_seconds': 120},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert 'Araştırmayı başarıyla tamamladınız!' in response.data.decode('utf-8') or 'final' in response.data.decode('utf-8').lower()

    user_response = UserResponse.query.first()
    assert user_response is not None
    assert user_response.case_id == case.id
    assert user_response.answers['q1'] == 'Kullanıcı Cevabı'

# --- 5. YÖNETİCİ TESTLERİ ---

def test_admin_llm_management(test_client):
    """Yöneticinin LLM ekleyip listeleyebildiğini test eder."""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    # LLM ekleme sayfasına git
    response = test_client.get('/admin/llms', follow_redirects=True)
    assert response.status_code == 200

    # Yeni LLM ekle
    response = test_client.post(
        '/admin/llm/ekle',
        data={'name': 'Test Model X', 'description': 'Test açıklaması'},
        follow_redirects=True
    )
    assert response.status_code == 200

    # Veritabanında kontrol et
    llm = LLM.query.filter_by(name='Test Model X').first()
    assert llm is not None

def test_admin_full_research_and_case_flow(test_client):
    """Yöneticinin baştan sona bir araştırma ve vaka oluşturma akışını test eder."""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    # Adım 1: JSON ile yeni bir araştırma yükle
    research_json = {
        "research_title": "Admin Test Araştırması",
        "research_description": "Bu bir admin test araştırmasıdır.",
        "cases": [
            {
                "title": "Admin Test Vaka 1",
                "questions": [{"id": "q1", "label": "Admin Soru 1"}]
            }
        ]
    }
    response = test_client.post(
        '/admin/upload_json',
        data={'json_text': json.dumps(research_json)},
        follow_redirects=True
    )
    assert response.status_code == 200

    # Adım 2: Araştırma oluşturuldu mu kontrol et
    research = Research.query.filter_by(title='Admin Test Araştırması').first()
    assert research is not None
    assert len(research.cases) == 1

    # Adım 3: Araştırma yönetim paneline git
    response = test_client.get(f'/admin/research/{research.id}/dashboard')
    assert response.status_code == 200

    # Adım 4: Vaka analiz ekranına git
    case = research.cases[0]
    response = test_client.get(f'/admin/case/{case.id}/review')
    assert response.status_code == 200

def test_admin_export_csv(test_client):
    """Yöneticinin CSV verisi dışa aktarabildiğini test eder."""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    # CSV dışa aktarma endpoint'ine erişim
    response = test_client.get('/admin/export_csv')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type or 'attachment' in response.headers.get('Content-Disposition', '')