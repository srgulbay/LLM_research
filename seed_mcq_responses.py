import random
from faker import Faker
from app import app, db, User, Research, Case, UserResponse

# Sahte veri için Faker'ı başlat
fake = Faker('tr_TR')

# Hedef araştırmanın başlığı
TARGET_RESEARCH_TITLE = "Pediatrik Enfeksiyonlarda Tanı ve Tedavi Yaklaşımları (Çoktan Seçmeli)"

def create_mcq_responses():
    """Belirtilen araştırma için mevcut kullanıcılara sahte çoktan seçmeli yanıtlar ekler."""
    with app.app_context():
        # Hedef araştırmayı bul
        research = Research.query.filter_by(title=TARGET_RESEARCH_TITLE).first()
        if not research:
            print(f"HATA: '{TARGET_RESEARCH_TITLE}' başlıklı araştırma bulunamadı.")
            return

        # Araştırmaya ait vakaları al
        cases = Case.query.filter_by(research_id=research.id).all()
        if not cases:
            print(f"HATA: '{research.title}' araştırması için vaka bulunamadı.")
            return
            
        # Yönetici olmayan kullanıcıları al
        users = User.query.filter_by(is_admin=False).all()
        if not users:
            print("HATA: Sisteme yanıt ekleyecek kullanıcı bulunamadı.")
            return

        print(f"'{research.title}' araştırmasındaki {len(cases)} vaka için {len(users)} kullanıcıya yanıt ekleniyor...")
        
        responses_added = 0
        for user in users:
            for case in cases:
                # Kullanıcının bu vakaya zaten yanıt verip vermediğini kontrol et (opsiyonel)
                existing_response = UserResponse.query.filter_by(user_id=user.id, case_id=case.id).first()
                if existing_response:
                    # print(f"Atlandı: Kullanıcı {user.id}, Vaka {case.id} için zaten yanıt var.")
                    continue

                answers = {}
                questions = case.content.get('questions', [])
                
                # Sadece çoktan seçmeli soruları yanıtla
                for q in questions:
                    if q.get('type') == 'multiple-choice' and q.get('options'):
                        answers[q['id']] = random.choice(q['options'])
                    # Diğer tipler için boş bırakabilir veya sahte metin ekleyebiliriz
                    # else:
                    #     answers[q['id']] = fake.sentence()

                # Yanıtları boş olmayan vakalar için ekle
                if answers:
                    new_response = UserResponse(
                        user_id=user.id,
                        case_id=case.id,
                        answers=answers,
                        confidence_score=random.randint(40, 100), # Biraz daha gerçekçi aralık
                        clinical_rationale=fake.sentence(nb_words=random.randint(10, 25)), # Daha uzun gerekçe
                        duration_seconds=random.randint(30, 180) # MCQ için daha kısa süreler
                    )
                    db.session.add(new_response)
                    responses_added += 1

        if responses_added > 0:
            try:
                db.session.commit()
                print(f"Başarıyla {responses_added} adet yeni yanıt eklendi.")
            except Exception as e:
                db.session.rollback()
                print(f"Yanıtlar eklenirken hata oluştu: {e}")
        else:
            print("Eklenecek yeni yanıt bulunamadı (Tüm kullanıcılar bu vakaları zaten yanıtlamış olabilir).")


# Ana Çalışma Bloğu
if __name__ == "__main__":
    try:
        Faker
    except NameError:
        print("\nUYARI: 'Faker' kütüphanesi bulunamadı. Lütfen 'pip install Faker' komutuyla kurun.\n")
        exit()
        
    create_mcq_responses()
