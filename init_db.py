from app import app, db
from app import User, Case, ReferenceAnswer # Modelleri import et
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
    """Başlangıç verilerini (vakaları) ekler."""
    with app.app_context():
        if Case.query.first() is not None:
            print("Veritabanı zaten veri içeriyor, seeding atlandı.")
            return

        print("Veritabanı boş, başlangıç vakaları ekleniyor...")
        initial_cases_data = [
             {
                "title": "Vaka 1: Huzursuz Bebek", "anamnesis": {"Hasta": "18 aylık, erkek.", "Şikayet": "Huzursuzluk, ateş ve sol kulağını çekiştirme."},
                "physical_exam": {"Bulgu": "Sol kulak zarında hiperemi ve bombeleşme."},
                "gold_standard_response": {"tanı": "Akut Otitis Media", "tetkik": "Ek tetkik gerekmez", "tedavi_plani": "Antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
                "chatgpt_response": {"tanı": "Akut Otitis Media", "tetkik": "Gerekli değil", "tedavi_plani": "Amoksisilin", "dozaj": "90 mg/kg/gün"},
                "gemini_response": {"tanı": "Bakteriyel AOM", "tetkik": "Endike değil", "tedavi_plani": "Amoksisilin-Klavulanat", "dozaj": "Standart doz"},
                "deepseek_response": {"tanı": "Sol Akut Otitis Media", "tetkik": "İstenmez", "tedavi_plani": "Antibiyotik", "dozaj": "Amoksisilin tedavisi"}
            },
            {
                "title": "Vaka 2: Öksüren Çocuk", "anamnesis": {"Hasta": "4 yaşında, kız.", "Şikayet": "3 gündür ateş, öksürük ve hızlı nefes alma."},
                "physical_exam": {"Bulgu": "Sağ akciğer alt zonda krepitan raller."},
                "gold_standard_response": {"tanı": "Toplum Kökenli Pnömoni", "tetkik": "Akciğer Grafisi", "tedavi_plani": "Oral antibiyoterapi", "dozaj": "Yüksek doz Amoksisilin"},
                "chatgpt_response": {"tanı": "Pnömoni", "tetkik": "Akciğer grafisi, TKS", "tedavi_plani": "Amoksisilin", "dozaj": "80-100 mg/kg/gün"},
                "gemini_response": {"tanı": "Sağ Alt Lob Pnömonisi", "tetkik": "Akciğer Röntgeni", "tedavi_plani": "Destekleyici bakım", "dozaj": "Oral amoksisilin"},
                "deepseek_response": {"tanı": "Pnömoni", "tetkik": "Göğüs X-ray", "tedavi_plani": "Antibiyotik", "dozaj": "Uygun antibiyotik"}
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
                db.session.flush() # ID'nin atanmasını sağla

                ref_answer = ReferenceAnswer(case_id=new_case.id, source='gold', content=case_data.get('gold_standard_response', {}))
                db.session.add(ref_answer)

            db.session.commit()
            print(f"{len(initial_cases_data)} başlangıç vakası eklendi.")
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