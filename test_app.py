# test_app.py

import pytest
import json
from app import app, db, User, Research, Case, LLM, UserResponse

@pytest.fixture(scope='session')
def test_client():
    """
    Tüm test oturumu için TEK BİR test istemcisi ve temiz bir veritabanı oluşturur.
    """
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Hafızada çalışan DB
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "SECRET_KEY": "test-secret-key" # Testler için gizli anahtar
    })

    with app.app_context():
        db.create_all()
        
        # Testler boyunca kullanılacak temel bir yönetici oluşturalım
        from werkzeug.security import generate_password_hash
        if not User.query.filter_by(email='admin@test.com').first():
            admin = User(
                email='admin@test.com', 
                is_admin=True, 
                password_hash=generate_password_hash('123456'), 
                has_consented=True, 
                profession="Admin"
            )
            db.session.add(admin)
            db.session.commit()
        
        # yield, test istemcisini test fonksiyonuna gönderir
        yield app.test_client()
        
        # Testler bittikten sonra veritabanını temizle
        db.drop_all()

# --- TESTLER ---

def test_ana_sayfa_yonlendirmesi(test_client):
    """1. Test: Giriş yapmamış bir kullanıcı ana sayfaya gittiğinde giriş sayfasına yönlendirilir mi?"""
    response = test_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Artık 'giris.html' dosyasını arıyoruz
    assert 'Giriş Yap veya Hesap Oluştur' in response.data.decode('utf-8')

def test_kullanici_kayit_ve_onboarding_sureci(test_client):
    """2. Test: Yeni bir kullanıcı kaydolup onam ve demografi adımlarını tamamlayabilir mi?"""
    # Benzersiz email kullan
    email = 'onboarding@test.com'
    response = test_client.post('/giris', data={'email': email}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Araştırma Katılım Onayı' in response.data.decode('utf-8')

    response = test_client.post('/consent', follow_redirects=True)
    assert response.status_code == 200
    assert 'Katılımcı Bilgileri' in response.data.decode('utf-8')

    response = test_client.post('/demographics', data={'profession': 'Pratisyen Hekim', 'experience': 5}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Mevcut Araştırmalar' in response.data.decode('utf-8')

    user = User.query.filter_by(email=email).first()
    assert user is not None
    assert user.has_consented is True
    assert user.profession == 'Pratisyen Hekim'

def test_yonetici_giris_ve_panel_erisim(test_client):
    """3. Test: Yönetici doğru şifreyle giriş yapıp yönetici paneline erişebilir mi?"""
    response = test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Yönetici Ana Paneli' in response.data.decode('utf-8')

def test_yonetici_arastirma_yukleme_ve_yonetme(test_client):
    """4. Test: Yönetici yeni bir araştırmayı JSON ile yükleyebilir ve yönetebilir mi?"""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    # LLM ekle (Araştırma yüklemesi LLM'lere bağlı olabilir)
    response = test_client.post('/admin/llm/ekle', data={'name': 'GPT-4'})
    llm = LLM.query.filter_by(name='GPT-4').first()
    assert llm is not None

    # Araştırma yükle
    research_json = {
        "research_title": "Test Araştırması", 
        "research_description": "Bu bir test araştırmasıdır.",
        "cases": [
            {
                "title": "Test Vaka 1", 
                "sections": [{"title": "Anamnez", "content": "Test"}],
                "questions": [{"id": "q1", "type": "open-ended", "label": "Test Soru?"}],
                "gold_standard": {"q1": "Test Cevap"},
                "llm_responses": {}
            }
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
    # Kullanıcı giriş yap
    test_client.post('/giris', data={'email': 'user@test.com'})
    
    # Onam ve demografiye geç
    test_client.post('/consent')
    test_client.post('/demographics', data={'profession': 'Pratisyen Hekim', 'experience': 3})
    
    research = Research.query.filter_by(title='Test Araştırması').first()
    assert research is not None
    
    response = test_client.get(f'/arastirma/{research.id}', follow_redirects=True)
    assert response.status_code == 200

    case = research.cases[0]
    response = test_client.get(f'/case/{case.id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'Test Vaka 1' in response.data.decode('utf-8')

    # Vakayı cevapla
    response = test_client.post(
        f'/case/{case.id}', 
        data={
            'q1': 'Kullanıcı Cevabı', 
            'confidence_score': 80,
            'clinical_rationale': 'Test gerekçesi',
            'duration_seconds': 120 # Bu artık formdan gelmiyor, sunucu hesaplıyor
        }, 
        follow_redirects=True
    )
    assert response.status_code == 200
    # Araştırma bittiği için final raporuna yönlenmeli
    assert 'Araştırmayı Tamamladınız!' in response.data.decode('utf-8')

    # Yanıtın kaydedildiğini kontrol et
    user = User.query.filter_by(email='user@test.com').first()
    user_response = UserResponse.query.filter_by(author=user, case_id=case.id).first()
    assert user_response is not None
    assert user_response.answers['q1'] == 'Kullanıcı Cevabı'
    assert user_response.confidence_score == 80
    assert user_response.clinical_rationale == 'Test gerekçesi'


def test_yonetici_vaka_analiz_ekrani(test_client):
    """6. Test: Yönetici bir vaka için analiz ekranına erişebilir mi?"""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    research = Research.query.filter_by(title='Test Araştırması').first()
    case = research.cases[0]

    response = test_client.get(f'/admin/case/{case.id}/review')
    assert response.status_code == 200
    assert 'Vaka Analiz Ekranı' in response.data.decode('utf-8')

def test_yonetici_bilimsel_analiz(test_client):
    """7. Test: Yönetici bilimsel analiz paneline erişebilir mi?"""
    # Admin giriş yap
    test_client.post('/admin/login', data={'email': 'admin@test.com', 'password': '123456'})

    research = Research.query.filter_by(title='Test Araştırması').first()
    
    # Analiz sayfası veri olmadan da açılmalı (henüz veri yok uyarısı ile)
    response = test_client.get(f'/admin/research/{research.id}/analytics')
    assert response.status_code == 200
    assert 'Bilimsel Analiz Paneli' in response.data.decode('utf-8')
