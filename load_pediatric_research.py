#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pediatrik MCQ araştırma verisini sisteme yükler
"""

import json
from app import app, db, Research, Case, ReferenceAnswer, UserResponse, User, LLM

def load_pediatric_research():
    """JSON dosyasından pediatrik araştırma verisini yükler"""
    
    with app.app_context():
        # JSON dosyasını oku
        with open('pediatric_mcq_research.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Araştırmanın zaten yüklü olup olmadığını kontrol et
        existing = Research.query.filter_by(title=data['research_title']).first()
        if existing:
            print(f"⚠️  '{data['research_title']}' zaten mevcut. Siliniyor ve yeniden yükleniyor...")
            db.session.delete(existing)
            db.session.commit()
        
        # Yeni araştırma oluştur
        research = Research(
            title=data['research_title'],
            description=data['research_description'],
            is_active=True
        )
        db.session.add(research)
        db.session.flush()  # ID'yi al
        
        print(f"✓ Araştırma oluşturuldu: {research.title}")
        
        # Her vaka için
        for case_data in data['cases']:
            # Vaka içeriğini oluştur
            case_content = {
                "title": case_data['title'],
                "sections": case_data['sections'],
                "questions": case_data['questions']
            }
            
            # Vaka oluştur
            case = Case(
                research_id=research.id,
                content=case_content,
                llm_scores={}
            )
            db.session.add(case)
            db.session.flush()
            
            print(f"  ✓ Vaka eklendi: {case_data['title']}")
            
            # Gold standard cevapları kaydet
            if case_data.get('gold_standard'):
                ref_answer = ReferenceAnswer(
                    case_id=case.id,
                    source='gold_standard',
                    content=case_data['gold_standard']
                )
                db.session.add(ref_answer)
                print(f"    ✓ {len(case_data['gold_standard'])} referans cevap eklendi")
            
            # LLM yanıtları varsa ekle
            if 'llm_responses' in case_data:
                for llm_name, llm_data in case_data['llm_responses'].items():
                    # LLM kaydını bul veya oluştur
                    llm = LLM.query.filter_by(name=llm_name).first()
                    if not llm:
                        llm = LLM(
                            name=llm_name,
                            description=f"LLM Model: {llm_name}"
                        )
                        db.session.add(llm)
                        db.session.flush()
                        print(f"    ✓ Yeni LLM eklendi: {llm_name}")
                    
                    # LLM için dummy user oluştur veya bul
                    llm_user_email = f"llm_{llm_name.lower().replace('-', '_')}@system.ai"
                    llm_user = User.query.filter_by(email=llm_user_email).first()
                    if not llm_user:
                        llm_user = User(
                            email=llm_user_email,
                            username=f"LLM: {llm_name}",
                            is_anonymous=False
                        )
                        db.session.add(llm_user)
                        db.session.flush()
                    
                    # LLM yanıtını kaydet
                    llm_response = UserResponse(
                        case_id=case.id,
                        user_id=llm_user.id,
                        answers=llm_data['answers'],
                        confidence_score=llm_data.get('confidence_score'),
                        clinical_rationale=llm_data.get('rationale', ''),
                        scores={}  # Skorlar sonra hesaplanacak
                    )
                    db.session.add(llm_response)
                
                print(f"    ✓ {len(case_data['llm_responses'])} LLM yanıtı eklendi")
        
        # Değişiklikleri kaydet
        db.session.commit()
        
        # Skorları hesapla
        print("\n🔄 Skorlar hesaplanıyor...")
        scored_count = 0
        for response in UserResponse.query.join(Case).filter(Case.research_id == research.id).all():
            # Referans cevabı bul
            ref_answer = ReferenceAnswer.query.filter_by(
                case_id=response.case_id,
                source='gold_standard'
            ).first()
            
            if not ref_answer:
                continue
            
            # Skorları hesapla
            scores = {}
            correct_count = 0
            total_questions = 0
            
            for question_id, user_answer in response.answers.items():
                total_questions += 1
                gold_answer = ref_answer.content.get(question_id)
                
                if gold_answer:
                    is_correct = (user_answer == gold_answer)
                    scores[question_id] = {
                        'user_answer': user_answer,
                        'gold_answer': gold_answer,
                        'is_correct': is_correct,
                        'score': 1 if is_correct else 0
                    }
                    
                    if is_correct:
                        correct_count += 1
            
            # Genel skor ekle
            if total_questions > 0:
                accuracy = (correct_count / total_questions) * 100
                scores['_summary'] = {
                    'total_questions': total_questions,
                    'correct_answers': correct_count,
                    'accuracy_percentage': round(accuracy, 2)
                }
            
            response.scores = scores
            scored_count += 1
        
        db.session.commit()
        print(f"✓ {scored_count} yanıt için skorlama tamamlandı")
        
        # Özet bilgi
        total_cases = Case.query.filter_by(research_id=research.id).count()
        total_questions = sum(len(c['questions']) for c in data['cases'])
        total_llm_responses = UserResponse.query.join(Case).filter(Case.research_id == research.id).count()
        
        print("\n" + "="*60)
        print("✅ Pediatrik MCQ Araştırması Başarıyla Yüklendi!")
        print("="*60)
        print(f"📊 Araştırma: {research.title}")
        print(f"📁 Vaka Sayısı: {total_cases}")
        print(f"❓ Toplam Soru Sayısı: {total_questions}")
        print(f"🤖 LLM Yanıt Sayısı: {total_llm_responses}")
        print(f"🆔 Araştırma ID: {research.id}")
        print("="*60)
        print(f"\n🌐 Araştırma URL: http://localhost:8080/select_research")
        print(f"📝 İlk Vaka URL: http://localhost:8080/case/{Case.query.filter_by(research_id=research.id).first().id}")
        print(f"👨‍💼 Admin Panel: http://localhost:8080/admin/dashboard")
        
        return research

if __name__ == '__main__':
    print("🔄 Pediatrik MCQ araştırması yükleniyor...\n")
    load_pediatric_research()
