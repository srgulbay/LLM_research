import random
import json
from faker import Faker
from app import app, db, User, Research, Case, UserResponse, LLM

# Sahte veri için Faker'ı başlat
fake = Faker('tr_TR')

# Hedef araştırmanın başlığı
TARGET_RESEARCH_TITLE = "Pediatrik Enfeksiyonlarda Tanı ve Tedavi Yaklaşımları (Çoktan Seçmeli)"

def generate_data():
    """Belirtilen araştırma için sahte kullanıcı yanıtları ve sahte LLM yanıtları oluşturur."""
    with app.app_context():
        # --- Veritabanından Gerekli Bilgileri Al ---
        
        research = Research.query.filter_by(title=TARGET_RESEARCH_TITLE).first()
        if not research:
            print(f"HATA: '{TARGET_RESEARCH_TITLE}' başlıklı araştırma bulunamadı.")
            return

        cases = Case.query.filter_by(research_id=research.id).all()
        if not cases:
            print(f"HATA: '{research.title}' araştırması için vaka bulunamadı.")
            return
            
        users = User.query.filter_by(is_admin=False).all()
        if not users:
            print("HATA: Sisteme yanıt ekleyecek kullanıcı bulunamadı.")
            # init_db.py çalıştırılmamış olabilir
            return

        llms = LLM.query.all()
        if not llms:
            print("HATA: Sistemde tanımlı LLM bulunamadı.")
            # LLM'ler admin panelinden eklenmemiş olabilir
            return
            
        print(f"'{research.title}' araştırması bulundu (ID: {research.id}).")
        print(f"{len(cases)} vaka, {len(users)} kullanıcı, {len(llms)} LLM modeli mevcut.")

        # --- 1. Sahte Kullanıcı Yanıtları Oluşturma ---
        print("\nSahte kullanıcı yanıtları oluşturuluyor...")
        human_responses_added = 0
        for user in users:
            for case in cases:
                existing_response = UserResponse.query.filter_by(user_id=user.id, case_id=case.id).first()
                if existing_response:
                    continue # Yanıt zaten varsa atla

                answers = {}
                questions = case.content.get('questions', [])
                
                for q in questions:
                    if q.get('type') == 'multiple-choice' and q.get('options'):
                        answers[q['id']] = random.choice(q['options'])
                
                if answers: # Sadece cevap varsa ekle
                    new_response = UserResponse(
                        user_id=user.id,
                        case_id=case.id,
                        answers=answers,
                        confidence_score=random.randint(40, 100), 
                        clinical_rationale=fake.sentence(nb_words=random.randint(10, 25)), 
                        duration_seconds=random.randint(30, 180) 
                    )
                    db.session.add(new_response)
                    human_responses_added += 1
        
        if human_responses_added > 0:
             print(f"-- {human_responses_added} adet yeni kullanıcı yanıtı eklendi (henüz commit edilmedi).")
        else:
             print("-- Eklenecek yeni kullanıcı yanıtı yok (zaten mevcut olabilir).")


        # --- 2. Sahte LLM Yanıtları Oluşturma (Case objesi içine) ---
        print("\nSahte LLM yanıtları oluşturuluyor (vaka içeriklerine)...")
        cases_updated_with_llm = 0
        for case in cases:
            if not case.content: # İçerik yoksa atla
                 print(f"UYARI: Vaka ID {case.id} için içerik bulunamadı, LLM yanıtı eklenemiyor.")
                 continue
                 
            # Case.content bir dict değilse, onu dict yap
            if not isinstance(case.content, dict):
                 try:
                      case.content = json.loads(str(case.content)) # String'den JSON'a dönüştürmeyi dene
                 except:
                      case.content = {} # Başarısız olursa boş dict ata

            case.content.setdefault('llm_responses', {}) # llm_responses anahtarı yoksa ekle
            
            llm_responses_for_case = {} # Bu vaka için yeni LLM yanıtlarını tut
            questions = case.content.get('questions', [])
            
            needs_update = False
            for llm in llms:
                # Eğer bu LLM için zaten yanıt yoksa oluştur
                # if llm.name not in case.content['llm_responses']: # Sadece eksikleri eklemek için
                
                llm_answers = {}
                for q in questions:
                    if q.get('type') == 'multiple-choice' and q.get('options'):
                        llm_answers[q['id']] = random.choice(q['options'])

                if llm_answers: # Sadece cevap varsa ekle
                    llm_data = {
                        "answers": llm_answers,
                        "confidence_score": random.randint(70, 100), # LLM'ler genelde daha "emin" olur :)
                        "rationale": f"{llm.name} tarafından oluşturulan sahte gerekçe: {fake.sentence(nb_words=random.randint(8, 20))}"
                    }
                    # case.content['llm_responses'][llm.name] = llm_data # Doğrudan content'i değiştir
                    llm_responses_for_case[llm.name] = llm_data
                    needs_update = True # Güncelleme gerektiğini işaretle

            # Eğer bu vaka için yeni LLM yanıtları oluşturulduysa, case.content'i güncelle
            if needs_update:
                # case.content['llm_responses'] = llm_responses_for_case # Eski yanıtları tamamen siler
                case.content['llm_responses'].update(llm_responses_for_case) # Mevcutları korur, yenileri ekler/günceller
                
                # SQLAlchemy'ye JSON alanının değiştiğini bildirmek için
                # db.session.add(case) # Obje zaten session'da ise tekrar add gerekmez
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(case, "content") # JSON alanının değiştiğini işaretle
                
                cases_updated_with_llm += 1

        if cases_updated_with_llm > 0:
             print(f"-- {cases_updated_with_llm} adet vakanın LLM yanıtları güncellendi/eklendi (henüz commit edilmedi).")
        else:
             print("-- Güncellenecek/eklenecek yeni LLM yanıtı yok.")

        # --- Değişiklikleri Kaydet ---
        if human_responses_added > 0 or cases_updated_with_llm > 0:
            try:
                db.session.commit()
                print("\nTüm değişiklikler veritabanına başarıyla kaydedildi.")
            except Exception as e:
                db.session.rollback()
                print(f"\nVeritabanına kaydederken hata oluştu: {e}")
        else:
            print("\nVeritabanında yapılacak bir değişiklik yok.")


# Ana Çalışma Bloğu
if __name__ == "__main__":
    try:
        Faker
    except NameError:
        print("\nUYARI: 'Faker' kütüphanesi bulunamadı. Lütfen 'pip install Faker' komutuyla kurun.\n")
        exit()
        
    generate_data()

