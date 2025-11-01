#!/usr/bin/env python3
"""
🔬 LLM Research-Focused Case Generator
Araştırma odaklı vaka setleri oluşturma modülü

Özellikler:
- Araştırma direktifleri ile vaka üretimi
- Altın standart yanıtlar
- Batch generation
- Scoring criteria
- Research metadata
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from colorama import init, Fore, Style, Back

# .env dosyasını yükle
load_dotenv()

# Colorama başlat
init(autoreset=True)

# Gemini API yapılandırması
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print(f"{Fore.RED}❌ GEMINI_API_KEY ortam değişkeni bulunamadı!")
    print(f"{Fore.YELLOW}💡 Lütfen .env dosyasında tanımlayın:")
    print(f"   GEMINI_API_KEY=your-api-key")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)


class ResearchCaseGenerator:
    """Araştırma odaklı vaka oluşturucu"""
    
    def __init__(self, model_name='gemini-pro-latest'):
        """Generator'ı başlat
        
        Args:
            model_name: Kullanılacak Gemini model ismi (örn: 'gemini-pro-latest', 'gemini-2.5-pro')
        """
        # Model ismini tam formata çevir
        if not model_name.startswith('models/'):
            model_name = f'models/{model_name}'
        
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.generation_config = {
            'temperature': 0.9,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        
        # Araştırma şablonları
        self.research_templates = {
            'antibiotic_stewardship': {
                'title': 'Akılcı Antibiyotik Kullanımı',
                'description': 'Aile hekimliği uzmanlarının akılcı antibiyotik kullanımı konusunda karar verme yeteneklerini değerlendirme',
                'target_group': 'Aile Hekimleri',
                'focus_areas': [
                    'Gereksiz antibiyotik reçetesi',
                    'Doğru antibiyotik seçimi',
                    'Antibiyotik dozajı',
                    'Tedavi süresi',
                    'Yan etki yönetimi',
                    'Hasta eğitimi'
                ]
            },
            'emergency_triage': {
                'title': 'Acil Servis Triyajı',
                'description': 'Acil serviste doğru önceliklendirme ve ilk müdahale becerilerini değerlendirme',
                'target_group': 'Acil Tıp Uzmanları',
                'focus_areas': [
                    'Triyaj kararları',
                    'İlk stabilizasyon',
                    'Kritik müdahale',
                    'Kaynak yönetimi'
                ]
            },
            'pediatric_diagnosis': {
                'title': 'Pediatrik Tanı',
                'description': 'Çocuklarda yaygın hastalıkların tanı ve tedavi yönetimi',
                'target_group': 'Pediatristler',
                'focus_areas': [
                    'Gelişimsel değerlendirme',
                    'Enfeksiyon yönetimi',
                    'Aşılama',
                    'Beslenme',
                    'Büyüme izlemi'
                ]
            }
        }
    
    def print_header(self, text: str):
        """Başlık yazdır"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}{Back.BLUE} {text} {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}\n")
    
    def print_success(self, text: str):
        """Başarı mesajı"""
        print(f"{Fore.GREEN}✓ {text}")
    
    def print_error(self, text: str):
        """Hata mesajı"""
        print(f"{Fore.RED}✗ {text}")
    
    def print_warning(self, text: str):
        """Uyarı mesajı"""
        print(f"{Fore.YELLOW}⚠ {text}")
    
    def print_info(self, text: str):
        """Bilgi mesajı"""
        print(f"{Fore.BLUE}ℹ {text}")
    
    def get_research_directives(self) -> Dict:
        """Araştırma direktiflerini al"""
        self.print_header("🔬 ARAŞTIRMA DİREKTİFLERİ")
        
        # Template seçimi
        print(f"{Fore.YELLOW}📋 Araştırma Şablonu Seçin (veya özel):")
        print("  0. Özel araştırma direktifleri (manuel giriş)")
        for i, (key, template) in enumerate(self.research_templates.items(), 1):
            print(f"  {i}. {template['title']}")
            print(f"     Hedef: {template['target_group']}")
            print()
        
        while True:
            try:
                choice = input(f"\n{Fore.GREEN}Seçim (0-{len(self.research_templates)}): ")
                choice_idx = int(choice)
                if choice_idx == 0:
                    return self.get_custom_directives()
                elif 1 <= choice_idx <= len(self.research_templates):
                    template_key = list(self.research_templates.keys())[choice_idx - 1]
                    return self.get_template_directives(template_key)
                else:
                    self.print_error(f"Lütfen 0-{len(self.research_templates)} arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
    
    def get_template_directives(self, template_key: str) -> Dict:
        """Template'den direktifleri al"""
        template = self.research_templates[template_key]
        
        print(f"\n{Fore.CYAN}📋 Araştırma: {template['title']}")
        print(f"{Fore.CYAN}🎯 Hedef Grup: {template['target_group']}")
        print(f"\n{Fore.YELLOW}Odak Alanları:")
        for area in template['focus_areas']:
            print(f"  • {area}")
        
        # Vaka sayısı
        while True:
            try:
                num_cases = int(input(f"\n{Fore.GREEN}Kaç vaka oluşturulsun? (1-20): "))
                if 1 <= num_cases <= 20:
                    break
                self.print_error("1-20 arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
        
        # Her vakada kaç soru
        while True:
            try:
                questions_per_case = int(input(f"{Fore.GREEN}Her vakada kaç soru? (3-10): "))
                if 3 <= questions_per_case <= 10:
                    break
                self.print_error("3-10 arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
        
        # Ek direktifler
        print(f"\n{Fore.CYAN}Ek direktifler eklemek ister misiniz? (opsiyonel)")
        additional = input(f"{Fore.GREEN}Ek direktifler: ").strip()
        
        # Zorluk dağılımı
        print(f"\n{Fore.YELLOW}Zorluk dağılımı:")
        print("  1. Tümü kolay")
        print("  2. Tümü orta")
        print("  3. Tümü zor")
        print("  4. Karışık (kolay-orta-zor)")
        
        difficulty_dist = input(f"\n{Fore.GREEN}Seçim (1-4, varsayılan=4): ").strip()
        difficulty_map = {
            '1': 'easy',
            '2': 'medium',
            '3': 'hard',
            '4': 'mixed'
        }
        difficulty = difficulty_map.get(difficulty_dist, 'mixed')
        
        return {
            'template_key': template_key,
            'title': template['title'],
            'description': template['description'],
            'target_group': template['target_group'],
            'focus_areas': template['focus_areas'],
            'num_cases': num_cases,
            'questions_per_case': questions_per_case,
            'difficulty': difficulty,
            'additional_directives': additional
        }
    
    def get_custom_directives(self) -> Dict:
        """Özel direktifleri al"""
        print(f"\n{Fore.CYAN}📝 ÖZEL ARAŞTIRMA DİREKTİFLERİ")
        
        title = input(f"\n{Fore.GREEN}Araştırma başlığı: ").strip()
        description = input(f"{Fore.GREEN}Araştırma açıklaması: ").strip()
        target_group = input(f"{Fore.GREEN}Hedef grup (örn: Aile Hekimleri): ").strip()
        
        print(f"\n{Fore.YELLOW}Odak alanları (her satıra bir alan, boş satır ile bitir):")
        focus_areas = []
        while True:
            area = input(f"{Fore.GREEN}Odak alanı: ").strip()
            if not area:
                break
            focus_areas.append(area)
        
        while True:
            try:
                num_cases = int(input(f"\n{Fore.GREEN}Kaç vaka? (1-20): "))
                if 1 <= num_cases <= 20:
                    break
            except ValueError:
                pass
        
        while True:
            try:
                questions_per_case = int(input(f"{Fore.GREEN}Her vakada kaç soru? (3-10): "))
                if 3 <= questions_per_case <= 10:
                    break
            except ValueError:
                pass
        
        return {
            'template_key': 'custom',
            'title': title,
            'description': description,
            'target_group': target_group,
            'focus_areas': focus_areas,
            'num_cases': num_cases,
            'questions_per_case': questions_per_case,
            'difficulty': 'mixed',
            'additional_directives': ''
        }
    
    def build_research_prompt(self, directives: Dict, case_num: int) -> str:
        """Araştırma odaklı prompt oluştur"""
        
        difficulty_text = {
            'easy': 'kolay (tıp öğrencisi seviyesi)',
            'medium': 'orta (asistan seviyesi)',
            'hard': 'zor (uzman seviyesi)',
            'mixed': 'karışık zorluk seviyesi (kolay, orta ve zor)'
        }
        
        prompt = f"""Sen deneyimli bir tıp eğitimcisi ve araştırmacısısın. Şu araştırma için sentetik tıbbi vaka soruları oluşturuyorsun:

**ARAŞTIRMA BİLGİLERİ:**
Başlık: {directives['title']}
Açıklama: {directives['description']}
Hedef Grup: {directives['target_group']}

**ODAK ALANLARI:**
{chr(10).join([f"• {area}" for area in directives['focus_areas']])}

{f"**EK DİREKTİFLER:**{chr(10)}{directives['additional_directives']}" if directives['additional_directives'] else ""}

**VAKA GEREKSİNİMLERİ:**
• Bu {directives['num_cases']} vakalık setin {case_num}. vakası
• Zorluk: {difficulty_text[directives['difficulty']]}
• {directives['questions_per_case']} soru içermeli
• Gerçekçi klinik senaryo
• Hedef grubun yetkinliğini değerlendirmeli

**ÖNEMLİ: ALTIN STANDART YANITLAR**
Her soru için:
1. Doğru cevabı belirle
2. Neden bu cevabın altın standart olduğunu açıkla
3. Diğer seçeneklerin neden yanlış/optimal olmadığını açıkla
4. Scoring criteria tanımla (0-100 arası nasıl puanlanacak)

**JSON FORMAT (ZORUNLU):**
```json
{{
  "research_info": {{
    "title": "{directives['title']}",
    "target_group": "{directives['target_group']}",
    "case_number": {case_num},
    "total_cases": {directives['num_cases']}
  }},
  "case": {{
    "title": "Vaka başlığı (kısa ve açıklayıcı)",
    "difficulty": "easy|medium|hard",
    "patient_age": "Yaş aralığı",
    "case_description": "Detaylı hasta hikayesi...",
    "learning_objectives": [
      "Bu vakayla değerlendirilecek yetkinlik 1",
      "Bu vakayla değerlendirilecek yetkinlik 2"
    ],
    "focus_areas": {directives['focus_areas']},
    "questions": [
      {{
        "question_number": 1,
        "question_text": "Soru metni?",
        "question_type": "diagnosis|treatment|management|knowledge",
        "options": [
          {{"key": "A", "text": "Seçenek A"}},
          {{"key": "B", "text": "Seçenek B"}},
          {{"key": "C", "text": "Seçenek C"}},
          {{"key": "D", "text": "Seçenek D"}}
        ],
        "correct_answer": "A",
        "gold_standard": {{
          "answer": "A",
          "rationale": "Neden bu cevap altın standart? Kanıt düzeyi nedir?",
          "why_others_wrong": {{
            "B": "B seçeneği neden yanlış/suboptimal",
            "C": "C seçeneği neden yanlış/suboptimal",
            "D": "D seçeneği neden yanlış/suboptimal"
          }},
          "evidence_level": "1A|1B|2A|2B|3|4|5",
          "references": [
            "İlgili kılavuz/kaynak 1",
            "İlgili kılavuz/kaynak 2"
          ]
        }},
        "scoring_criteria": {{
          "correct_answer": 100,
          "partial_credit": {{
            "B": 0,
            "C": 0,
            "D": 0
          }},
          "explanation": "Doğru cevap 100 puan. Diğerleri 0 puan çünkü..."
        }},
        "competency_assessed": "Değerlendirilen yetkinlik (örn: Tanı koyma, Tedavi planı, vb.)"
      }}
    ]
  }}
}}
```

ÖNEMLİ: 
1. Sadece JSON formatında yanıt ver
2. Altın standart açıklamalarını çok detaylı yaz
3. Kanıt düzeylerini belirt (1A en güçlü kanıt)
4. Scoring criteria'yı net tanımla
5. Gerçek kılavuz ve kaynaklara referans ver
"""
        return prompt
    
    def generate_research_case(self, directives: Dict, case_num: int) -> Optional[Dict]:
        """Araştırma odaklı vaka oluştur"""
        prompt = self.build_research_prompt(directives, case_num)
        
        try:
            self.print_info(f"Vaka {case_num}/{directives['num_cases']} oluşturuluyor...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # JSON'ı parse et
            json_text = response.text.strip()
            
            # Markdown kod bloklarını temizle
            if json_text.startswith('```'):
                json_text = json_text.split('```')[1]
                if json_text.startswith('json'):
                    json_text = json_text[4:]
                json_text = json_text.strip()
            
            case_data = json.loads(json_text)
            
            self.print_success(f"Vaka {case_num} oluşturuldu!")
            return case_data
            
        except json.JSONDecodeError as e:
            self.print_error(f"JSON parse hatası: {e}")
            return None
        except Exception as e:
            self.print_error(f"Vaka oluşturma hatası: {e}")
            return None
    
    def preview_research_case(self, case_data: Dict):
        """Araştırma vakasını önizle"""
        self.print_header("👁️  VAKA ÖNİZLEME")
        
        research = case_data['research_info']
        case = case_data['case']
        
        print(f"{Fore.MAGENTA}🔬 Araştırma: {Fore.WHITE}{research['title']}")
        print(f"{Fore.MAGENTA}👥 Hedef Grup: {Fore.WHITE}{research['target_group']}")
        print(f"{Fore.MAGENTA}📊 Vaka: {Fore.WHITE}{research['case_number']}/{research['total_cases']}")
        print()
        
        print(f"{Fore.CYAN}📋 Başlık: {Fore.WHITE}{case['title']}")
        print(f"{Fore.CYAN}📊 Zorluk: {Fore.WHITE}{case['difficulty']}")
        print(f"{Fore.CYAN}👤 Yaş: {Fore.WHITE}{case['patient_age']}")
        
        print(f"\n{Fore.YELLOW}{'─'*70}")
        print(f"{Fore.GREEN}📝 VAKA HİKAYESİ:")
        print(f"{Fore.WHITE}{case['case_description']}")
        print(f"{Fore.YELLOW}{'─'*70}\n")
        
        print(f"{Fore.CYAN}🎯 Öğrenme Hedefleri:")
        for obj in case['learning_objectives']:
            print(f"  • {obj}")
        print()
        
        for i, q in enumerate(case['questions'], 1):
            print(f"{Fore.MAGENTA}❓ Soru {i}: {Fore.WHITE}{q['question_text']}")
            print(f"{Fore.CYAN}   Tip: {q['question_type']}")
            print(f"{Fore.CYAN}   Yetkinlik: {q['competency_assessed']}")
            print()
            
            for opt in q['options']:
                color = Fore.GREEN if opt['key'] == q['correct_answer'] else Fore.WHITE
                marker = "⭐" if opt['key'] == q['correct_answer'] else "  "
                print(f"  {color}{marker} {opt['key']}) {opt['text']}")
            
            gold = q['gold_standard']
            print(f"\n{Fore.GREEN}⭐ ALTIN STANDART:")
            print(f"{Fore.YELLOW}   Cevap: {gold['answer']}")
            print(f"{Fore.WHITE}   Gerekçe: {gold['rationale']}")
            print(f"{Fore.CYAN}   Kanıt Düzeyi: {gold['evidence_level']}")
            
            print(f"\n{Fore.RED}❌ Diğer Seçenekler Neden Yanlış:")
            for key, reason in gold['why_others_wrong'].items():
                if key != gold['answer']:
                    print(f"{Fore.YELLOW}   {key}: {Fore.WHITE}{reason}")
            
            scoring = q['scoring_criteria']
            print(f"\n{Fore.BLUE}📊 Puanlama:")
            print(f"{Fore.WHITE}   Doğru: {scoring['correct_answer']} puan")
            print(f"{Fore.WHITE}   {scoring['explanation']}")
            
            print(f"\n{Fore.CYAN}📚 Kaynaklar:")
            for ref in gold['references']:
                print(f"   • {ref}")
            
            print(f"{Fore.YELLOW}{'─'*70}\n")
    
    def generate_batch(self, directives: Dict) -> List[Dict]:
        """Toplu vaka oluştur"""
        self.print_header(f"🚀 TOPLU VAKA ÜRETİMİ ({directives['num_cases']} vaka)")
        
        cases = []
        for i in range(1, directives['num_cases'] + 1):
            case_data = self.generate_research_case(directives, i)
            if case_data:
                cases.append(case_data)
            else:
                self.print_warning(f"Vaka {i} oluşturulamadı, atlanıyor...")
        
        self.print_success(f"{len(cases)}/{directives['num_cases']} vaka başarıyla oluşturuldu!")
        return cases
    
    def save_research(self, directives: Dict, cases: List[Dict]) -> str:
        """Araştırma setini kaydet"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"research_{directives['template_key']}_{timestamp}.json"
        
        research_data = {
            'metadata': {
                'title': directives['title'],
                'description': directives['description'],
                'target_group': directives['target_group'],
                'focus_areas': directives['focus_areas'],
                'created_at': timestamp,
                'total_cases': len(cases),
                'questions_per_case': directives['questions_per_case']
            },
            'cases': cases
        }
        
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(research_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def load_to_database(self, directives: Dict, cases: List[Dict]) -> bool:
        """Araştırmayı veritabanına yükle"""
        try:
            from app import app, db, Research, Case, ReferenceAnswer
            
            with app.app_context():
                # Research oluştur
                research = Research(
                    title=directives['title'],
                    description=directives['description'],
                    start_date=datetime.now(),
                    is_active=True
                )
                db.session.add(research)
                db.session.commit()
                
                # Her vakayı ekle
                for order_num, case_data in enumerate(cases, 1):
                    case = case_data['case']
                    
                    # Case oluştur
                    db_case = Case(
                        research_id=research.id,
                        case_text=case['case_description'],
                        questions=case['questions'],
                        order_num=order_num
                    )
                    db.session.add(db_case)
                    db.session.commit()
                    
                    # Reference answers oluştur
                    for q in case['questions']:
                        ref_answer = ReferenceAnswer(
                            case_id=db_case.id,
                            question_number=q['question_number'],
                            reference_answer=q['correct_answer'],
                            explanation=q['gold_standard']['rationale'],
                            evidence_level=q['gold_standard'].get('evidence_level', ''),
                            references=json.dumps(q['gold_standard'].get('references', []))
                        )
                        db.session.add(ref_answer)
                
                db.session.commit()
                
                self.print_success(f"Araştırma veritabanına yüklendi!")
                self.print_info(f"Research ID: {research.id}")
                self.print_info(f"Toplam {len(cases)} vaka, {len(cases) * directives['questions_per_case']} soru")
                return True
                
        except Exception as e:
            self.print_error(f"Veritabanına yükleme hatası: {e}")
            return False
    
    def run(self):
        """Ana program döngüsü"""
        self.print_header("🔬 LLM RESEARCH CASE GENERATOR")
        
        print(f"{Fore.GREEN}Araştırma odaklı tıbbi vaka setleri oluşturun!")
        print(f"{Fore.YELLOW}Yönetici direktiflerine göre sentetik vakalar ve altın standart yanıtlar.\n")
        
        # Direktifleri al
        directives = self.get_research_directives()
        
        # Özet göster
        self.print_header("📋 ARAŞTIRMA ÖZETİ")
        print(f"{Fore.CYAN}Başlık: {Fore.WHITE}{directives['title']}")
        print(f"{Fore.CYAN}Hedef: {Fore.WHITE}{directives['target_group']}")
        print(f"{Fore.CYAN}Vaka Sayısı: {Fore.WHITE}{directives['num_cases']}")
        print(f"{Fore.CYAN}Soru/Vaka: {Fore.WHITE}{directives['questions_per_case']}")
        print(f"{Fore.CYAN}Toplam Soru: {Fore.WHITE}{directives['num_cases'] * directives['questions_per_case']}")
        
        confirm = input(f"\n{Fore.GREEN}Devam etmek istiyor musunuz? (e/h): ").lower()
        if confirm != 'e':
            self.print_warning("İşlem iptal edildi")
            return
        
        # Toplu üretim
        cases = self.generate_batch(directives)
        
        if not cases:
            self.print_error("Hiç vaka oluşturulamadı!")
            return
        
        # Önizleme (ilk vaka)
        print(f"\n{Fore.YELLOW}İlk vakayı önizliyorsunuz...")
        self.preview_research_case(cases[0])
        
        # Kaydetme seçenekleri
        while True:
            print(f"\n{Fore.CYAN}{'='*70}")
            print(f"{Fore.YELLOW}Ne yapmak istersiniz?")
            print("1. ✓ Tüm setı kaydet (JSON)")
            print("2. 📤 Veritabanına yükle")
            print("3. 👁️  Diğer vakaları önizle")
            print("4. 🔄 Tüm seti yeniden oluştur")
            print("0. ❌ Çıkış")
            
            choice = input(f"\n{Fore.GREEN}Seçim (0-4): ").strip()
            
            if choice == '1':
                filepath = self.save_research(directives, cases)
                self.print_success(f"Kaydedildi: {filepath}")
                
            elif choice == '2':
                if self.load_to_database(directives, cases):
                    print(f"{Fore.GREEN}✓ Araştırma veritabanına yüklendi!")
                    print(f"{Fore.CYAN}Admin panelinden görüntüleyin:")
                    print(f"  http://localhost:8080/admin")
                
            elif choice == '3':
                case_num = int(input(f"{Fore.CYAN}Hangi vakayı önizlemek istersiniz? (1-{len(cases)}): ")) - 1
                if 0 <= case_num < len(cases):
                    self.preview_research_case(cases[case_num])
                
            elif choice == '4':
                self.print_warning("Tüm set yeniden oluşturuluyor...")
                cases = self.generate_batch(directives)
                if cases:
                    self.preview_research_case(cases[0])
                
            elif choice == '0':
                self.print_info("Güle güle!")
                return


def main():
    """Ana fonksiyon"""
    try:
        generator = ResearchCaseGenerator()
        generator.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Program kullanıcı tarafından durduruldu.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
