#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tüm yanıtlar için skorlama yapar
"""

from app import app, db, UserResponse, ReferenceAnswer

def calculate_scores():
    """Tüm kullanıcı yanıtları için skorları hesaplar"""
    
    with app.app_context():
        responses = UserResponse.query.all()
        
        if not responses:
            print("❌ Hiç yanıt bulunamadı!")
            return
        
        print(f"🔄 {len(responses)} yanıt için skorlama yapılıyor...\n")
        
        scored_count = 0
        already_scored = 0
        
        for response in responses:
            # Referans cevabı bul
            ref_answer = ReferenceAnswer.query.filter_by(
                case_id=response.case_id,
                source='gold_standard'
            ).first()
            
            if not ref_answer:
                print(f"⚠️  Vaka {response.case_id} için referans cevap yok, atlanıyor...")
                continue
            
            # Eğer zaten skorlanmışsa atla
            if response.scores and len(response.scores) > 0:
                already_scored += 1
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
            
            # Skoru kaydet
            response.scores = scores
            scored_count += 1
            
            print(f"✓ {response.author.username} - Vaka {response.case_id}: {correct_count}/{total_questions} doğru ({round(accuracy, 1)}%)")
        
        # Değişiklikleri kaydet
        db.session.commit()
        
        print("\n" + "="*60)
        print("✅ Skorlama Tamamlandı!")
        print("="*60)
        print(f"📊 Yeni skorlanan: {scored_count}")
        print(f"⏭️  Zaten skorlanmış: {already_scored}")
        print(f"📈 Toplam: {len(responses)}")
        print("="*60)

if __name__ == '__main__':
    calculate_scores()
