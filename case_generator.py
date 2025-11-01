#!/usr/bin/env python3
"""
🏥 LLM Research Case Generator
Gemini AI ile tıbbi vaka soruları oluşturma modülü

Özellikler:
- İnteraktif CLI arayüzü
- Özelleştirilebilir parametreler
- Önizleme ve düzenleme
- Beğenmezsen yeniden üret
- JSON export ve DB import
- Template sistemli prompt'lar
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
    print(f"\n   veya terminal'de:")
    print(f"   export GEMINI_API_KEY='your-api-key'")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)


class CaseGenerator:
    """Tıbbi vaka soruları oluşturucu"""
    
    def __init__(self):
        """Generator'ı başlat"""
        self.model = genai.GenerativeModel('gemini-pro')
        self.generation_config = {
            'temperature': 0.9,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        
        # Vaka şablonları
        self.templates = {
            'pediatrics': 'pediatrik',
            'internal_medicine': 'iç hastalıkları',
            'surgery': 'cerrahi',
            'emergency': 'acil tıp',
            'family_medicine': 'aile hekimliği',
            'neurology': 'nöroloji',
            'cardiology': 'kardiyoloji',
            'psychiatry': 'psikiyatri'
        }
        
        # Zorluk seviyeleri
        self.difficulty_levels = {
            'easy': 'kolay (tıp öğrencisi seviyesi)',
            'medium': 'orta (asistan seviyesi)',
            'hard': 'zor (uzman seviyesi)',
            'expert': 'çok zor (profesör seviyesi)'
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
    
    def get_case_parameters(self) -> Dict:
        """Kullanıcıdan vaka parametrelerini al"""
        self.print_header("🎯 VAKA PARAMETRELERİ")
        
        # Branş seçimi
        print(f"{Fore.YELLOW}📋 Tıp Branşı Seçin:")
        for i, (key, value) in enumerate(self.templates.items(), 1):
            print(f"  {i}. {value.capitalize()}")
        
        while True:
            try:
                choice = input(f"\n{Fore.GREEN}Seçim (1-{len(self.templates)}): ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(self.templates):
                    specialty = list(self.templates.keys())[choice_idx]
                    break
                else:
                    self.print_error(f"Lütfen 1-{len(self.templates)} arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
        
        # Zorluk seviyesi
        print(f"\n{Fore.YELLOW}📊 Zorluk Seviyesi:")
        for i, (key, value) in enumerate(self.difficulty_levels.items(), 1):
            print(f"  {i}. {value.capitalize()}")
        
        while True:
            try:
                choice = input(f"\n{Fore.GREEN}Seçim (1-{len(self.difficulty_levels)}): ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(self.difficulty_levels):
                    difficulty = list(self.difficulty_levels.keys())[choice_idx]
                    break
                else:
                    self.print_error(f"Lütfen 1-{len(self.difficulty_levels)} arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
        
        # Hasta yaşı
        while True:
            try:
                age = input(f"\n{Fore.GREEN}Hasta yaş aralığı (örn: 5-10, 20-40): ")
                if '-' in age:
                    min_age, max_age = map(int, age.split('-'))
                    if 0 < min_age < max_age < 120:
                        break
                self.print_error("Geçerli bir yaş aralığı girin (örn: 5-10)")
            except ValueError:
                self.print_error("Lütfen geçerli bir format kullanın (örn: 5-10)")
        
        # Soru sayısı
        while True:
            try:
                num_questions = int(input(f"\n{Fore.GREEN}Kaç soru olsun? (3-10): "))
                if 3 <= num_questions <= 10:
                    break
                self.print_error("3-10 arası bir sayı girin")
            except ValueError:
                self.print_error("Lütfen geçerli bir sayı girin")
        
        # Özel gereksinimler
        special_req = input(f"\n{Fore.GREEN}Özel gereksinimler (boş bırakabilirsiniz): ").strip()
        
        return {
            'specialty': specialty,
            'specialty_tr': self.templates[specialty],
            'difficulty': difficulty,
            'difficulty_tr': self.difficulty_levels[difficulty],
            'age_range': age,
            'num_questions': num_questions,
            'special_requirements': special_req
        }
    
    def build_prompt(self, params: Dict) -> str:
        """Gemini için prompt oluştur"""
        prompt = f"""Sen deneyimli bir tıp eğitimcisisin. Tıp öğrencileri ve hekimler için kaliteli vaka soruları oluşturuyorsun.

Aşağıdaki özelliklere sahip bir tıbbi vaka sorusu seti oluştur:

**Branş:** {params['specialty_tr'].upper()}
**Zorluk Seviyesi:** {params['difficulty_tr']}
**Hasta Yaş Aralığı:** {params['age_range']} yaş
**Soru Sayısı:** {params['num_questions']} soru

{f"**Özel Gereksinimler:** {params['special_requirements']}" if params['special_requirements'] else ""}

**FORMAT KURALLARI:**
1. Gerçekçi bir hasta hikayesi oluştur (150-300 kelime)
2. Hasta hikayesinde şunlar olmalı:
   - Başvuru şikayeti
   - Semptomların başlangıcı ve süresi
   - İlgili tıbbi geçmiş
   - Fizik muayene bulguları
   - Varsa laboratuvar/görüntüleme sonuçları

3. Her soru için:
   - Açık ve net soru metni
   - 4-5 seçenek (A, B, C, D, E)
   - Her seçenek gerçekçi ve mantıklı olmalı
   - Sadece bir doğru cevap
   - Detaylı açıklama (neden doğru, neden diğerleri yanlış)

4. Sorular şu konuları kapsamalı:
   - Tanı koyma
   - Ayırıcı tanı
   - Tedavi planı
   - İlk yaklaşım/acil müdahale
   - Prognostik faktörler
   - Komplikasyonlar

**JSON FORMAT (ZORUNLU):**
```json
{{
  "title": "Vaka Başlığı (kısa ve açıklayıcı)",
  "specialty": "{params['specialty']}",
  "difficulty": "{params['difficulty']}",
  "patient_age": "{params['age_range']}",
  "case_description": "Hasta hikayesi buraya...",
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Soru metni?",
      "options": [
        {{"key": "A", "text": "Seçenek A"}},
        {{"key": "B", "text": "Seçenek B"}},
        {{"key": "C", "text": "Seçenek C"}},
        {{"key": "D", "text": "Seçenek D"}}
      ],
      "correct_answer": "A",
      "explanation": "Detaylı açıklama. Neden A doğru, diğerleri neden yanlış...",
      "topic": "Tanı/Tedavi/Ayırıcı Tanı/vb."
    }}
  ],
  "references": [
    "İlgili kaynak 1",
    "İlgili kaynak 2"
  ],
  "learning_objectives": [
    "Öğrenme hedefi 1",
    "Öğrenme hedefi 2"
  ]
}}
```

ÖNEMLİ: Sadece JSON formatında yanıt ver. Başka açıklama ekleme!
"""
        return prompt
    
    def generate_case(self, params: Dict) -> Optional[Dict]:
        """Gemini ile vaka oluştur"""
        self.print_header("🤖 VAKA OLUŞTURULUYOR...")
        
        prompt = self.build_prompt(params)
        
        try:
            self.print_info("Gemini API'ye istek gönderiliyor...")
            
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
            
            self.print_success("Vaka başarıyla oluşturuldu!")
            return case_data
            
        except json.JSONDecodeError as e:
            self.print_error(f"JSON parse hatası: {e}")
            self.print_warning("Gemini'nin yanıtı geçerli JSON formatında değil")
            return None
        except Exception as e:
            self.print_error(f"Vaka oluşturma hatası: {e}")
            return None
    
    def preview_case(self, case_data: Dict):
        """Vakayı önizle"""
        self.print_header("👁️  VAKA ÖNİZLEME")
        
        print(f"{Fore.CYAN}📋 Başlık: {Fore.WHITE}{case_data['title']}")
        print(f"{Fore.CYAN}🏥 Branş: {Fore.WHITE}{case_data['specialty']}")
        print(f"{Fore.CYAN}📊 Zorluk: {Fore.WHITE}{case_data['difficulty']}")
        print(f"{Fore.CYAN}👤 Yaş: {Fore.WHITE}{case_data['patient_age']}")
        
        print(f"\n{Fore.YELLOW}{'─'*70}")
        print(f"{Fore.GREEN}📝 VAKA HİKAYESİ:")
        print(f"{Fore.WHITE}{case_data['case_description']}")
        print(f"{Fore.YELLOW}{'─'*70}\n")
        
        for i, q in enumerate(case_data['questions'], 1):
            print(f"{Fore.MAGENTA}❓ Soru {i}: {Fore.WHITE}{q['question_text']}")
            print()
            
            for opt in q['options']:
                color = Fore.GREEN if opt['key'] == q['correct_answer'] else Fore.WHITE
                marker = "✓" if opt['key'] == q['correct_answer'] else " "
                print(f"  {color}{marker} {opt['key']}) {opt['text']}")
            
            print(f"\n{Fore.CYAN}💡 Açıklama: {Fore.WHITE}{q['explanation']}")
            print(f"{Fore.YELLOW}{'─'*70}\n")
        
        # Öğrenme hedefleri
        if 'learning_objectives' in case_data:
            print(f"{Fore.GREEN}🎯 Öğrenme Hedefleri:")
            for obj in case_data['learning_objectives']:
                print(f"  • {obj}")
            print()
        
        # Kaynaklar
        if 'references' in case_data:
            print(f"{Fore.BLUE}📚 Kaynaklar:")
            for ref in case_data['references']:
                print(f"  • {ref}")
            print()
    
    def edit_case(self, case_data: Dict) -> Dict:
        """Vakayı düzenle"""
        self.print_header("✏️  VAKA DÜZENLEME")
        
        print(f"{Fore.YELLOW}Düzenlenebilir alanlar:")
        print("1. Başlık")
        print("2. Vaka hikayesi")
        print("3. Soru metni")
        print("4. Seçenekler")
        print("5. Doğru cevap")
        print("6. Açıklama")
        print("0. Düzenlemeyi bitir")
        
        while True:
            choice = input(f"\n{Fore.GREEN}Seçim (0-6): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                new_title = input(f"{Fore.CYAN}Yeni başlık: ").strip()
                if new_title:
                    case_data['title'] = new_title
                    self.print_success("Başlık güncellendi")
            elif choice == '2':
                print(f"{Fore.CYAN}Yeni vaka hikayesi (bitirmek için boş satır):")
                lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
                if lines:
                    case_data['case_description'] = '\n'.join(lines)
                    self.print_success("Vaka hikayesi güncellendi")
            elif choice in ['3', '4', '5', '6']:
                q_num = int(input(f"{Fore.CYAN}Hangi soru? (1-{len(case_data['questions'])}): ")) - 1
                if 0 <= q_num < len(case_data['questions']):
                    q = case_data['questions'][q_num]
                    
                    if choice == '3':
                        new_text = input(f"{Fore.CYAN}Yeni soru metni: ").strip()
                        if new_text:
                            q['question_text'] = new_text
                            self.print_success("Soru metni güncellendi")
                    elif choice == '4':
                        opt_key = input(f"{Fore.CYAN}Hangi seçenek? (A-E): ").strip().upper()
                        for opt in q['options']:
                            if opt['key'] == opt_key:
                                new_text = input(f"{Fore.CYAN}Yeni seçenek metni: ").strip()
                                if new_text:
                                    opt['text'] = new_text
                                    self.print_success(f"Seçenek {opt_key} güncellendi")
                                break
                    elif choice == '5':
                        new_answer = input(f"{Fore.CYAN}Yeni doğru cevap (A-E): ").strip().upper()
                        if new_answer in [opt['key'] for opt in q['options']]:
                            q['correct_answer'] = new_answer
                            self.print_success("Doğru cevap güncellendi")
                    elif choice == '6':
                        print(f"{Fore.CYAN}Yeni açıklama (bitirmek için boş satır):")
                        lines = []
                        while True:
                            line = input()
                            if not line:
                                break
                            lines.append(line)
                        if lines:
                            q['explanation'] = '\n'.join(lines)
                            self.print_success("Açıklama güncellendi")
        
        return case_data
    
    def save_to_json(self, case_data: Dict, filename: Optional[str] = None) -> str:
        """JSON dosyasına kaydet"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"case_{case_data['specialty']}_{timestamp}.json"
        
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def load_to_database(self, case_data: Dict) -> bool:
        """Veritabanına yükle"""
        try:
            # app.py'den import et
            from app import app, db, Research, Case
            
            with app.app_context():
                # Research oluştur veya bul
                research = Research.query.filter_by(
                    title=case_data['title']
                ).first()
                
                if not research:
                    research = Research(
                        title=case_data['title'],
                        description=f"{case_data['specialty'].capitalize()} - {case_data['difficulty'].capitalize()}",
                        start_date=datetime.now(),
                        is_active=True
                    )
                    db.session.add(research)
                    db.session.commit()
                
                # Case oluştur
                case = Case(
                    research_id=research.id,
                    case_text=case_data['case_description'],
                    questions=case_data['questions'],
                    order_num=1
                )
                db.session.add(case)
                db.session.commit()
                
                self.print_success(f"Vaka veritabanına yüklendi (Research ID: {research.id}, Case ID: {case.id})")
                return True
                
        except Exception as e:
            self.print_error(f"Veritabanına yükleme hatası: {e}")
            return False
    
    def run(self):
        """Ana program döngüsü"""
        self.print_header("🏥 LLM RESEARCH CASE GENERATOR")
        
        print(f"{Fore.GREEN}Tıbbi vaka soruları oluşturmak için Gemini AI kullanıyoruz!")
        print(f"{Fore.YELLOW}İstediğiniz özelliklere göre vaka setleri oluşturabilirsiniz.\n")
        
        while True:
            # Parametreleri al
            params = self.get_case_parameters()
            
            # Vakayı oluştur
            case_data = self.generate_case(params)
            
            if not case_data:
                retry = input(f"\n{Fore.YELLOW}Tekrar denemek ister misiniz? (e/h): ").lower()
                if retry != 'e':
                    break
                continue
            
            while True:
                # Önizle
                self.preview_case(case_data)
                
                # Kullanıcı seçimi
                print(f"\n{Fore.CYAN}{'='*70}")
                print(f"{Fore.YELLOW}Ne yapmak istersiniz?")
                print("1. ✓ Vakayı kaydet (JSON)")
                print("2. 📤 Veritabanına yükle")
                print("3. ✏️  Düzenle")
                print("4. 🔄 Yeniden oluştur")
                print("5. 🗑️  İptal et")
                print("0. ❌ Çıkış")
                
                choice = input(f"\n{Fore.GREEN}Seçim (0-5): ").strip()
                
                if choice == '1':
                    filename = input(f"{Fore.CYAN}Dosya adı (boş=otomatik): ").strip()
                    filepath = self.save_to_json(case_data, filename if filename else None)
                    self.print_success(f"Kaydedildi: {filepath}")
                    
                elif choice == '2':
                    if self.load_to_database(case_data):
                        print(f"{Fore.GREEN}✓ Vaka veritabanına yüklendi!")
                        print(f"{Fore.CYAN}Admin panelinden görüntüleyebilirsiniz:")
                        print(f"  http://localhost:8080/admin")
                    
                elif choice == '3':
                    case_data = self.edit_case(case_data)
                    continue
                    
                elif choice == '4':
                    print(f"\n{Fore.YELLOW}Yeni vaka oluşturuluyor...")
                    break
                    
                elif choice == '5':
                    self.print_warning("Vaka iptal edildi")
                    break
                    
                elif choice == '0':
                    self.print_info("Güle güle!")
                    return
                
                # Alt menüden çık
                if choice in ['1', '2', '4', '5']:
                    break
            
            # Ana döngüden çık mı?
            if choice == '5':
                continue_gen = input(f"\n{Fore.CYAN}Yeni vaka oluşturmak ister misiniz? (e/h): ").lower()
                if continue_gen != 'e':
                    break


def main():
    """Ana fonksiyon"""
    try:
        generator = CaseGenerator()
        generator.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Program kullanıcı tarafından durduruldu.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Beklenmeyen hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
