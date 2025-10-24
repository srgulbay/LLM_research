# init_db.py (MCQ Araştırması ve Yapay Verileri de Oluşturur + ID Yazdırır)

import random
import json
import os
from faker import Faker
from app import app, db
from app import User, Research, Case, LLM, UserResponse, ReferenceAnswer # ReferenceAnswer eklendi
from werkzeug.security import generate_password_hash
from sqlalchemy.orm.attributes import flag_modified # JSON güncellemesi için

# Sahte veri üretimi için Faker kütüphanesini başlat
fake = Faker('tr_TR')

# Hedef MCQ araştırmasının JSON dosya adı
MCQ_JSON_FILE = "pediatric_mcq_research.json"
# Hedef MCQ araştırmasının başlığı (JSON içindekiyle aynı olmalı)
MCQ_RESEARCH_TITLE = "Pediatrik Enfeksiyonlarda Tanı ve Tedavi Yaklaşımları (Çoktan Seçmeli)"

def create_initial_data():
    """Temel başlangıç verilerini (yönetici, kullanıcılar, LLM'ler) oluşturur."""
    with app.app_context():
        # --- 1. YÖNETİCİ OLUŞTURMA ---
        admin_email = "srgulbay@gmail.com"
        if not User.query.filter_by(email=admin_email).first():
            hashed_password = generate_password_hash("14531453", method='pbkdf2:sha256')
            admin_user = User(email=admin_email, password_hash=hashed_password, is_admin=True,
                              has_consented=True, profession="Admin", experience=10)
            db.session.add(admin_user)
            print(f"'{admin_email}' yönetici hesabı oluşturuldu.")

        # --- 2. 10 SANAL KULLANICI OLUŞTURMA ---
        professions = ["Pratisyen Hekim", "Aile Hekimi Uzmanı", "Çocuk Sağlığı ve Hastalıkları Uzmanı", "Tıp Öğrencisi", "Diğer Hekim"]
        users_created = 0
        if User.query.count() <= 1: # Sadece admin varsa kullanıcıları oluştur
            users = []
            for i in range(10):
                user = User(email=f"kullanici{i+1}@ornek.com", profession=random.choice(professions),
                            experience=random.randint(0, 15), has_consented=True)
                users.append(user)
            db.session.add_all(users)
            users_created = len(users)
            print(f"{users_created} sanal kullanıcı oluşturuldu.")

        # --- 3. LLM MODELLERİNİ OLUŞTURMA ---
        llm_names = ['GPT-4', 'Gemini-Pro', 'Llama3', 'Claude-3']
        llms_created = 0
        if LLM.query.count() == 0:
            for name in llm_names:
                db.session.add(LLM(name=name))
                llms_created += 1
            print(f"{len(llm_names)} LLM modeli eklendi.") # Düzeltme: llm_names uzunluğu

        # Değişiklikleri kaydet (sonraki adımlar için kullanıcılar/LLM'ler gerekli)
        if users_created > 0 or llms_created > 0:
             try:
                 db.session.commit()
                 print("Temel veriler (kullanıcılar, LLM'ler) kaydedildi.")
             except Exception as e:
                 db.session.rollback()
                 print(f"Temel veriler kaydedilirken HATA: {e}")
                 return False # Hata varsa devam etme
        return True # Temel veri oluşturma başarılı

def create_mcq_research_and_data():
    """MCQ araştırmasını JSON'dan oluşturur ve yapay verileri ekler."""
    research_id_created = None # Oluşturulan ID'yi saklamak için
    with app.app_context():
        # --- JSON Dosyasını Oku ---
        if not os.path.exists(MCQ_JSON_FILE):
             print(f"HATA: '{MCQ_JSON_FILE}' dosyası bulunamadı. MCQ araştırması oluşturulamıyor.")
             return None # ID döndüremiyoruz

        try:
             with open(MCQ_JSON_FILE, 'r', encoding='utf-8') as f:
                  data = json.load(f)
             print(f"'{MCQ_JSON_FILE}' dosyası başarıyla okundu.")
        except Exception as e:
             print(f"HATA: '{MCQ_JSON_FILE}' dosyası okunurken/işlenirken hata oluştu: {e}")
             return None

        research_title = data.get('research_title')
        if not research_title or research_title != MCQ_RESEARCH_TITLE:
             print(f"HATA: JSON dosyasındaki 'research_title' ('{research_title}') beklenen başlıkla ('{MCQ_RESEARCH_TITLE}') eşleşmiyor.")
             return None

        # --- Mevcut Araştırmayı Sil (Varsa) ---
        existing_research = Research.query.filter_by(title=research_title).first()
        if existing_research:
            print(f"Mevcut '{research_title}' araştırması ve ilişkili veriler siliniyor...")
            # İlişkili verileri sil (önceki silme koduna benzer)
            cases = Case.query.filter_by(research_id=existing_research.id).all()
            if cases:
                case_ids = [c.id for c in cases]
                UserResponse.query.filter(UserResponse.case_id.in_(case_ids)).delete(synchronize_session=False)
                ReferenceAnswer.query.filter(ReferenceAnswer.case_id.in_(case_ids)).delete(synchronize_session=False)
                for case in cases:
                    db.session.delete(case)
            db.session.delete(existing_research)
            try:
                db.session.commit()
                print("Eski araştırma başarıyla silindi.")
            except Exception as e:
                db.session.rollback()
                print(f"Eski araştırma silinirken HATA: {e}")
                return None

        # --- Yeni Araştırmayı ve Vakaları Oluştur ---
        print(f"Yeni '{research_title}' araştırması oluşturuluyor...")
        new_research = Research(title=research_title, description=data.get('research_description', ''), is_active=True)
        db.session.add(new_research)
        db.session.flush() # ID'yi almak için
        research_id_created = new_research.id # *** YENİ ID'Yİ SAKLA ***

        cases_data = data.get('cases', [])
        new_cases = []
        for case_content in cases_data:
             # JSON'daki llm_responses'ı doğrudan al
             new_case = Case(research_id=new_research.id, content=case_content)
             db.session.add(new_case)
             new_cases.append(new_case)
        print(f"-- {len(new_cases)} vaka oluşturuldu (LLM yanıtları dahil).")

        # --- Sahte Kullanıcı Yanıtları Oluştur ---
        users = User.query.filter_by(is_admin=False).all()

        if not users:
             print("UYARI: Yanıt oluşturacak kullanıcı bulunamadı.")
        else:
             print(f"-- {len(users)} kullanıcı için sahte yanıtlar oluşturuluyor...")
             human_responses_added = 0
             for user in users:
                  for case in new_cases: # Sadece yeni oluşturulan vakalar için
                       answers = {}
                       questions = case.content.get('questions', [])
                       for q in questions:
                            if q.get('type') == 'multiple-choice' and q.get('options'):
                                 answers[q['id']] = random.choice(q['options'])

                       if answers:
                            new_response = UserResponse(user_id=user.id, case_id=case.id, answers=answers,
                                                        confidence_score=random.randint(40, 100),
                                                        clinical_rationale=fake.sentence(nb_words=random.randint(10, 25)),
                                                        duration_seconds=random.randint(30, 180))
                            db.session.add(new_response)
                            human_responses_added += 1
             print(f"---- {human_responses_added} adet sahte kullanıcı yanıtı eklendi.")

        # --- Değişiklikleri Kaydet ---
        try:
            db.session.commit()
            print("MCQ araştırması ve yapay veriler başarıyla kaydedildi.")
        except Exception as e:
            db.session.rollback()
            print(f"MCQ verileri kaydedilirken HATA: {e}")
            return None

        return research_id_created # *** BAŞARILI İSE ID'Yİ DÖNDÜR ***


# --- Ana Çalışma Bloğu ---
if __name__ == "__main__":
    research_id = None # ID'yi tutmak için değişken
    with app.app_context():
        print("Veritabanı tabloları oluşturuluyor (varsa atlanacak)...")
        db.create_all()
        print("Tablolar oluşturuldu/kontrol edildi.")

        try: Faker
        except NameError:
            print("\nUYARI: 'Faker' kütüphanesi bulunamadı. Lütfen 'pip install Faker' komutuyla kurun.\n")
            exit()

        print("\nTemel başlangıç verileri (yönetici, kullanıcılar, LLM'ler) oluşturuluyor...")
        base_data_ok = create_initial_data()

        if base_data_ok:
            print("\nÇoktan seçmeli araştırma ve yapay veriler oluşturuluyor...")
            research_id = create_mcq_research_and_data() # *** DÖNEN ID'Yİ AL ***

    print("\nVeritabanı başlatma/doldurma işlemi tamamlandı.")

    # *** ID'Yİ SONDA TEKRAR YAZDIR ***
    if research_id:
         print("\n" + "="*40)
         print(f"Oluşturulan/Güncellenen MCQ Araştırmasının ID'si: {research_id}")
         print("Puanlamayı başlatmak için bu ID'yi kullanın:")
         print(f"  flask enqueue-scoring --research-id {research_id}")
         print("="*40 + "\n")
    else:
         print("\nMCQ Araştırması oluşturulamadığı için ID alınamadı.")

