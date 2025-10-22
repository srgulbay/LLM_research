from app import app, db
from app import User, Case, ReferenceAnswer, Research # Modelleri import et
from werkzeug.security import generate_password_hash
import json
import datetime # Eklendi

def create_initial_admin():
    """İlk yönetici hesabını oluşturur veya günceller."""
    with app.app_context():
        admin_email = "srgulbay@gmail.com"
        admin_user = User.query.filter_by(email=admin_email).first()

        # Güvenli şifre hash'ini oluştur
        hashed_password = generate_password_hash("14531453", method='pbkdf2:sha256')

        if not admin_user:
            # Kullanıcı yoksa, yeni bir tane oluştur
            admin_user = User(
                email=admin_email,
                password_hash=hashed_password,
                is_admin=True,
                # Adminin onam veya demografi doldurması gerekmez
                has_consented=True,
                profession="Admin",
                experience=0
            )
            db.session.add(admin_user)
            print(f"'{admin_email}' yönetici hesabı oluşturuldu.")
        else:
            # Kullanıcı varsa, şifresini ve admin durumunu güncelle
            admin_user.password_hash = hashed_password
            admin_user.is_admin = True
            # Adminin diğer bilgilerini de güncelleyelim (isteğe bağlı)
            admin_user.has_consented=True
            admin_user.profession="Admin"
            admin_user.experience=0
            print(f"'{admin_email}' yönetici hesabı güncellendi.")

        db.session.commit()

def seed_database():
    """Başlangıç verilerini (araştırma ve vakaları) ekler."""
    with app.app_context():
        # Eğer zaten bir vaka varsa, işlemi atla
        if Case.query.first() is not None:
            print("Veritabanı zaten veri içeriyor, seeding atlandı.")
            return

        print("Veritabanı boş, başlangıç verileri ekleniyor...")

        try:
            # 1. Yeni bir Araştırma oluştur
            new_research = Research(
                title="Primer İmmün Yetmezlikler Erken Tanısı LLM-İnsan Araştırması",
                description="Bu araştırma, sık enfeksiyon geçiren çocuklarda PİY erken tanısına yönelik hekim ve LLM performansını karşılaştırmaktadır.",
                is_active=True
            )
            db.session.add(new_research)
            # ID'nin bu aşamada atanmasını sağlamak için flush() kullanıyoruz
            db.session.flush()
            print(f"Araştırma oluşturuldu: {new_research.title}")

            # 2. Yeni JSON formatında bir Vaka içeriği tanımla
            case_content_data = {
                "case_id": "PIY_Vaka_01",
                "title": "Vaka 1: Tekrarlayan Akciğer Enfeksiyonu",
                "sections": [
                    { "title": "Anamnez", "content": "2 yaşında erkek hasta, son 6 ayda 4 kez zatürre tanısı almış..." },
                    { "title": "Fizik Muayene", "content": "Solunum sesleri bilateral kaba, ral duyulmadı..." }
                ],
                "questions": [
                    { "id": "q1_tani", "type": "open-ended", "label": "1. Bu hastadaki en olası ön tanınız nedir?" },
                    { "id": "q2_tetkik", "type": "multiple-choice", "label": "2. Hangi tetkiki ilk istersiniz?", "options": ["Akciğer Grafisi", "Tam Kan Sayımı", "İmmünglobulin Düzeyleri (IgG, IgA, IgM)", "Ter Testi"] },
                    { "id": "q3_ek_not", "type": "textarea", "label": "3. Eklemek istediğiniz notlar var mı?" }
                ],
                "gold_standard": {
                    "q1_tani": "Primer İmmün Yetmezlik şüphesi",
                    "q2_tetkik": "İmmünglobulin Düzeyleri (IgG, IgA, IgM)",
                    "q3_ek_not": "Hastanın aile öyküsü sorgulanmalı ve lenfosit alt grup analizi planlanmalıdır."
                }
            }

            # 3. Vakayı oluştur ve Araştırmaya bağla. content alanına tüm JSON'ı ata.
            new_case = Case(
                research_id=new_research.id,
                content=case_content_data
            )
            db.session.add(new_case)
            print(f"Vaka oluşturuldu: {case_content_data['title']}")

            db.session.commit()
            print("Başlangıç verileri başarıyla eklendi.")
        except Exception as e:
            db.session.rollback()
            print(f"Seeding sırasında hata: {e}")


print("Veritabanı başlatma script'i (init_db.py) çalışıyor...")

with app.app_context():
    # Önce tüm tabloları oluştur
    db.create_all()
    print("Tablolar başarıyla oluşturuldu.")

    # Sonra yöneticiyi oluştur/güncelle
    create_initial_admin()

    # Son olarak başlangıç vakalarını ekle
    seed_database()

print("Veritabanı başlatma tamamlandı.")