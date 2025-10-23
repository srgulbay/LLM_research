import os
import json
from redis import Redis
from rq import Queue, get_current_job
from app import app, db, get_semantic_score, UserResponse, ReferenceAnswer

# app.py'de tanımlanan Redis bağlantısını ve kuyruğu al
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
    if not conn:
        print(f"HATA: Redis bağlantısı yok. Görev {response_id} çalıştırılamadı.")
        return

    job = get_current_job(conn)
    if not job: 
        print(f"HATA: Job context bulunamadı (Response ID: {response_id}).")
        # Job context olmadan devam etmeyi deneyebiliriz ancak meta güncellenemez
    
    def update_job_status(status):
        if job:
            job.meta['status'] = status
            job.save_meta()
        print(f"[Job {response_id}]: {status}")

    with app.app_context():
        try:
            update_job_status('Başlatılıyor...')
            
            ur = db.session.get(UserResponse, response_id)
            if not ur:
                app.logger.warning("UserResponse bulunamadı: %s", response_id)
                return

            if not ur.case or not ur.case.content:
                app.logger.error("Vaka (Case) veya vaka içeriği bulunamadı (Response ID: %s)", response_id)
                return

            case_content = ur.case.content
            gold_standard_data = case_content.get('gold_standard', {})
            if not gold_standard_data:
                app.logger.error("Altın Standart yanıt bulunamadı (Case ID: %s)", ur.case_id)
                ur.scores = {"error": "Altın Standart yanıt bulunamadı."}
                db.session.commit()
                return
            
            user_answers = ur.answers or {}
            
            scores = {}
            reasons = {}
            llm_raw = {}
            
            # Puanlanacak soruları bul (Altın standartta olanlar)
            questions_to_score = [q for q in (case_content.get('questions', [])) if q.get('id') in gold_standard_data]

            if not questions_to_score:
                 app.logger.warning("Puanlanacak soru bulunamadı (Case ID: %s)", ur.case_id)
                 ur.scores = {"error": "Altın standartta puanlanacak soru bulunamadı."}
                 db.session.commit()
                 return

            total_score = 0
            score_count = 0
            
            for i, question in enumerate(questions_to_score):
                q_id = question.get('id')
                q_label = question.get('label', q_id)
                
                update_job_status(f'{i+1}/{len(questions_to_score)}: "{q_label}" puanlanıyor...')

                user_answer = user_answers.get(q_id, "")
                gold_answer = gold_standard_data.get(q_id, "")
                
                if not user_answer or not gold_answer:
                    score = 0.0
                    reason = "Kullanıcı yanıtı veya altın standart yanıt boş."
                    raw_response = None
                else:
                    # 'Kategori' olarak sorunun etiketini (label) kullan
                    score, raw_data = get_semantic_score(user_answer, gold_answer, q_label)
                    score = float(score)
                    reason = raw_data.get('reason')
                    raw_response = raw_data.get('raw')

                scores[q_id] = score
                reasons[q_id] = reason
                llm_raw[q_id] = raw_response
                
                total_score += score
                score_count += 1

            # Final Skoru Hesapla ve Kaydet
            final_score = round(total_score / max(1, score_count), 2)
            
            ur.scores = {
                "final_score": final_score,
                "question_scores": scores,
                "reasons": reasons
            }
            # Ham LLM yanıtlarını ayrı bir sütunda saklamak daha iyi olabilir
            # ama şimdilik 'scores' içine gömüyoruz:
            ur.scores["llm_raw"] = llm_raw
            
            db.session.add(ur)
            db.session.commit()
            
            update_job_status('Tamamlandı')
            app.logger.info("Puanlama tamamlandı: Response ID %s, Final Skor: %s", response_id, final_score)

        except Exception as e:
            app.logger.exception("score_and_store_response hatası")
            db.session.rollback()
            if job:
                update_job_status(f'Hata: {e}')

