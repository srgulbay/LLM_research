# init_db.py (10 Sanal Kullanıcı ve 200 Yanıt Üreten Kapsamlı Sürüm)

import random
import json
from faker import Faker
from app import app, db
from app import User, Research, Case, LLM, UserResponse
from werkzeug.security import generate_password_hash

# Sahte veri üretimi için Faker kütüphanesini başlat
fake = Faker('tr_TR')

def create_initial_data():
    """Tüm başlangıç verilerini (yönetici, kullanıcılar, LLM'ler, araştırmalar, vakalar ve yanıtlar) oluşturur."""
    with app.app_context():
        # --- 1. YÖNETİCİ OLUŞTURMA ---
        admin_email = "srgulbay@gmail.com"
        if not User.query.filter_by(email=admin_email).first():
            hashed_password = generate_password_hash("14531453", method='pbkdf2:sha256')
            admin_user = User(
                email=admin_email, password_hash=hashed_password, is_admin=True,
                has_consented=True, profession="Admin", experience=10
            )
            db.session.add(admin_user)
            print(f"'{admin_email}' yönetici hesabı oluşturuldu.")

        # --- 2. 10 SANAL KULLANICI OLUŞTURMA ---
        professions = ["Pratisyen Hekim", "Aile Hekimi Uzmanı", "Çocuk Sağlığı ve Hastalıkları Uzmanı", "Tıp Öğrencisi", "Diğer Hekim"]
        users = []
        if User.query.count() <= 1: # Sadece admin varsa kullanıcıları oluştur
            for i in range(10):
                user = User(
                    email=f"kullanici{i+1}@ornek.com",
                    profession=random.choice(professions),
                    experience=random.randint(0, 15),
                    has_consented=True
                )
                users.append(user)
            db.session.add_all(users)
            print(f"{len(users)} sanal kullanıcı oluşturuldu.")

        # --- 3. LLM MODELLERİNİ OLUŞTURMA ---
        llm_names = ['GPT-4', 'Gemini-Pro', 'Llama3', 'Claude-3']
        if LLM.query.count() == 0:
            for name in llm_names:
                db.session.add(LLM(name=name))
            print(f"{len(llm_names)} LLM modeli eklendi.")

        # --- 4. ARAŞTIRMALARI VE VAKALARI OLUŞTURMA ---
        researches = []
        if Research.query.count() == 0:
            research_titles = [
                "Pediatrik Pnömoni Tanısında Hekim ve LLM Karşılaştırması",
                "Akut Otitis Media Yönetiminde Tanısal Yaklaşımlar",
                "Gastroenterit Vakalarında Dehidratasyon Değerlendirmesi",
                "Febril Konvülsiyon Geçiren Çocukta Ayırıcı Tanı Süreçleri"
            ]
            for i, title in enumerate(research_titles):
                research = Research(title=title, description=f"Bu, '{title}' üzerine odaklanan bir test araştırmasıdır.", is_active=True)
                researches.append(research)
                db.session.add(research)
                db.session.flush() # ID'nin atanması için

                for j in range(5): # Her araştırma için 5 vaka
                    case_content = {
                        "title": f"Vaka #{j + 1}: {title.split(' ')[1]}",
                        "sections": [{"title": "Anamnez", "content": f"{j+1}. vakanın anamnez özeti..."}, {"title": "Fizik Muayene", "content": "Bulgular..."}],
                        "questions": [
                            {"id": f"q1_r{i}c{j}", "type": "open-ended", "label": "1. Ön tanınız nedir?"},
                            {"id": f"q2_r{i}c{j}", "type": "multiple-choice", "label": "2. Hangi tetkiki istersiniz?", "options": ["Kan Sayımı", "Akciğer Grafisi", "Boğaz Kültürü", "İdrar Tahlili"]}
                        ],
                        "gold_standard": {f"q1_r{i}c{j}": f"Doğru Tanı {j+1}", f"q2_r{i}c{j}": random.choice(["Kan Sayımı", "Akciğer Grafisi"])},
                        "llm_responses": {
                            "GPT-4": f"GPT-4'ün Vaka {j+1} için örnek yanıtı.",
                            "Gemini-Pro": f"Gemini-Pro'nun Vaka {j+1} için örnek yanıtı."
                        }
                    }
                    case = Case(research_id=research.id, content=case_content)
                    db.session.add(case)
            print(f"{len(researches)} araştırma ve {len(researches) * 5} vaka oluşturuldu.")
        
        db.session.commit() # Buraya kadar olan her şeyi kaydet

        # --- 5. SANAL YANITLARI OLUŞTURMA ---
        if UserResponse.query.count() == 0:
            all_users = User.query.filter_by(is_admin=False).all()
            all_cases = Case.query.all()
            responses = []
            for user in all_users:
                for case in all_cases:
                    answers = {}
                    for q in case.content.get('questions', []):
                        if q['type'] == 'multiple-choice':
                            answers[q['id']] = random.choice(q['options'])
                        else:
                            answers[q['id']] = f"{user.profession} tarafından verilen örnek tanı."
                    
                    response = UserResponse(
                        user_id=user.id,
                        case_id=case.id,
                        answers=answers,
                        duration_seconds=random.randint(60, 300)
                    )
                    responses.append(response)
            
            db.session.add_all(responses)
            print(f"{len(responses)} adet sanal kullanıcı yanıtı oluşturuldu.")

        db.session.commit()


# --- Ana Çalışma Bloğu ---
if __name__ == "__main__":
    with app.app_context():
        print("Veritabanı tabloları oluşturuluyor...")
        db.create_all()
        print("Tablolar başarıyla oluşturuldu.")
        
        # Eğer `faker` kütüphanesi kurulu değilse, bu script hata verecektir.
        try:
            Faker
        except NameError:
            print("\nUYARI: 'Faker' kütüphanesi bulunamadı. Lütfen 'pip install Faker' komutuyla kurun.\n")
            exit()

        create_initial_data()

    print("\nVeritabanı başlatma ve doldurma işlemi tamamlandı.")