import os
import json
from redis import Redis
from rq import Queue, Connection, Worker
from app import app, db, get_semantic_score, UserResponse, ReferenceAnswer

redis_url = os.getenv("REDIS_URL") or os.getenv("RAILWAY_REDIS_URL")
conn = Redis.from_url(redis_url) if redis_url else None
queue = Queue("default", connection=conn) if conn else None

def score_and_store_response(response_id):
    with app.app_context():
        try:
            ur = UserResponse.query.get(response_id)
            if not ur:
                app.logger.warning("UserResponse yok: %s", response_id)
                return
            gold = ReferenceAnswer.query.filter_by(case_id=ur.case_id, source='gold').first()
            gold_content = gold.content if gold else {}
            reasons = {}
            llm_raw = {}
            # diagnosis
            diag_score, diag_raw = get_semantic_score(ur.diagnosis, gold_content.get('diagnosis', ''), 'diagnosis')
            ur.diagnosis_score = diag_score
            reasons['diagnosis'] = diag_raw.get('reason') if isinstance(diag_raw, dict) else None
            llm_raw['diagnosis'] = diag_raw.get('raw') if isinstance(diag_raw, dict) else None
            # conditional tests
            if diag_score >= 70:
                tests_score, tests_raw = get_semantic_score(ur.tests, gold_content.get('tests', ''), 'tests')
                ur.tests_score = tests_score
                reasons['tests'] = tests_raw.get('reason')
                llm_raw['tests'] = tests_raw.get('raw')
            else:
                ur.tests_score = 0.0
                reasons['tests'] = "Tanı yetersiz; tests atlandı"
            # treatment
            treat_text = f"{ur.treatment_group} || {ur.treatment_agent}"
            treat_score, treat_raw = get_semantic_score(treat_text, gold_content.get('treatment_plan', ''), 'treatment')
            ur.treatment_score = treat_score
            reasons['treatment'] = treat_raw.get('reason')
            llm_raw['treatment'] = treat_raw.get('raw')
            # dosage conditional
            if treat_score >= 70:
                dosage_score, dosage_raw = get_semantic_score(ur.dosage, gold_content.get('dosage', ''), 'dosage')
                ur.dosage_score = dosage_score
                reasons['dosage'] = dosage_raw.get('reason')
                llm_raw['dosage'] = dosage_raw.get('raw')
            else:
                ur.dosage_score = 0.0
                reasons['dosage'] = "Tedavi hatalı; dozaj atlandı"
            scores = [s for s in [ur.diagnosis_score, ur.tests_score, ur.treatment_score, ur.dosage_score] if s is not None]
            ur.final_score = round(sum(scores)/max(1,len(scores)),2)
            ur.score_reasons = reasons
            ur.llm_raw = llm_raw
            db.session.add(ur)
            db.session.commit()
            app.logger.info("Scoring tamamlandı for response %s", response_id)
        except Exception:
            app.logger.exception("score_and_store_response hata")
            db.session.rollback()