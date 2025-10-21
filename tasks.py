import os
import json
from redis import Redis
from rq import Queue
from app import app, db, get_semantic_score, UserResponse, ReferenceAnswer

# app.py'de tanımlanan Redis bağlantısını ve kuyruğu al
# Bu, worker'ın da aynı bağlantı ayarlarını kullanmasını sağlar.
redis_url = os.getenv('REDIS_URL')
if not redis_url:
    print("HATA: tasks.py REDIS_URL bulamadı. Worker çalışmayacak.")
    conn = None
else:
    conn = Redis.from_url(redis_url)

def score_and_store_response(response_id):
    """
    Bir kullanıcı yanıtını (UserResponse) Gemini API kullanarak puanlar
    ve sonuçları veritabanına kaydeder. Bu fonksiyon RQ worker'ı
    tarafından asenkron olarak çalıştırılır.
    """
    with app.app_context():
        try:
            # 1. Gerekli verileri veritabanından çek
            ur = db.session.get(UserResponse, response_id)
            if not ur:
                app.logger.warning("UserResponse bulunamadı: %s", response_id)
                return

            # Altın standart yanıtı 'ReferenceAnswer' tablosundan al
            gold = ReferenceAnswer.query.filter_by(case_id=ur.case_id, source='gold').first()
            if not gold:
                app.logger.error("Altın Standart yanıt bulunamadı (Case ID: %s)", ur.case_id)
                ur.score_reasons = {"error": "Altın Standart yanıt bulunamadı."}
                db.session.commit()
                return
            
            gold_content = gold.content # Bu zaten bir JSON (dict) olmalı
            
            reasons = {}
            llm_raw = {}

            # 2. Puanlama Aşamaları
            
            # Tanı
            diag_score, diag_raw = get_semantic_score(ur.user_diagnosis, gold_content.get('tanı', ''), 'Tanı')
            ur.diagnosis_score = float(diag_score)
            reasons['diagnosis'] = diag_raw.get('reason')
            llm_raw['diagnosis'] = diag_raw.get('raw')

            # Tetkik (Tanı skoruna koşullu)
            if diag_score >= 70:
                tests_score, tests_raw = get_semantic_score(ur.user_tests, gold_content.get('tetkik', ''), 'Tetkik')
                ur.investigation_score = float(tests_score)
                reasons['tests'] = tests_raw.get('reason')
                llm_raw['tests'] = tests_raw.get('raw')
            else:
                ur.investigation_score = 0.0
                reasons['tests'] = "Tanı yetersiz/hatalı olduğu için tetkik puanlanmadı."
                llm_raw['tests'] = None

            # Tedavi (İlaç seçimi)
            treat_text = f"İlaç Grubu: {ur.user_drug_class}, Etken Madde: {ur.user_active_ingredient}"
            treat_score, treat_raw = get_semantic_score(treat_text, gold_content.get('tedavi_plani', ''), 'Tedavi Planı')
            ur.treatment_score = float(treat_score)
            reasons['treatment'] = treat_raw.get('reason')
            llm_raw['treatment'] = treat_raw.get('raw')

            # Dozaj (Tedavi skoruna koşullu)
            if treat_score >= 70:
                dosage_score, dosage_raw = get_semantic_score(ur.user_dosage_notes, gold_content.get('dozaj', ''), 'Dozaj')
                ur.dosage_score = float(dosage_score)
                reasons['dosage'] = dosage_raw.get('reason')
                llm_raw['dosage'] = dosage_raw.get('raw')
            else:
                ur.dosage_score = 0.0
                reasons['dosage'] = "İlaç seçimi yetersiz/hatalı olduğu için dozaj puanlanmadı."
                llm_raw['dosage'] = None

            # 3. Final Skoru Hesapla ve Kaydet
            scores = [s for s in [ur.diagnosis_score, ur.investigation_score, ur.treatment_score, ur.dosage_score] if s is not None]
            ur.final_score = round(sum(scores) / max(1, len(scores)), 2)
            
            ur.score_reasons = reasons
            ur.llm_raw = llm_raw
            
            db.session.add(ur)
            db.session.commit()
            
            app.logger.info("Puanlama tamamlandı: Response ID %s", response_id)

        except Exception as e:
            app.logger.exception("score_and_store_response hatası")
            db.session.rollback()
