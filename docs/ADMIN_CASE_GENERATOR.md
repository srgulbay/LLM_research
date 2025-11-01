# 🔬 Admin Panel - Research Case Generator Kullanım Kılavuzu

## 📖 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Erişim Yöntemleri](#erişim-yöntemleri)
3. [Web Arayüzü Kullanımı](#web-arayüzü-kullanımı)
4. [CLI Kullanımı](#cli-kullanımı)
5. [Örnek Senaryolar](#örnek-senaryolar)
6. [Sık Sorulan Sorular](#sık-sorulan-sorular)

---

## 🎯 Genel Bakış

Research Case Generator, yöneticilerin araştırma odaklı vaka setleri oluşturmasını sağlayan yapay zeka destekli bir araçtır. Bu araç ile:

- ✅ **Araştırma Direktiflerine Uygun** vaka setleri oluşturulur
- ✅ **Altın Standart Yanıtlar** her soru için otomatik üretilir
- ✅ **Kanıt Düzeyi** (1A-5) belirlenir
- ✅ **Batch Generation** - Tek seferde 1-20 vaka
- ✅ **Otomatik Veritabanı Yükleme** - Direkt sisteme aktarım

---

## 🚪 Erişim Yöntemleri

### **1. Web Arayüzü (Önerilen)** 🌐

Admin paneli üzerinden modern web arayüzü ile erişim.

**Adımlar:**
1. Admin paneline giriş yapın: `http://localhost:8080/admin/login`
   - Email: `admin@llm.com`
   - Şifre: `admin123`

2. Sol menüden **"🔬 Vaka Oluşturucu"** seçeneğine tıklayın

3. Alternatif: Direkt URL
   ```
   http://localhost:8080/admin/case-generator
   ```

**Avantajları:**
- ✅ Kullanıcı dostu arayüz
- ✅ Form validasyonu
- ✅ Gerçek zamanlı önizleme
- ✅ Tek tıkla veritabanına kaydetme
- ✅ Hata yönetimi

---

### **2. Komut Satırı (CLI)** 💻

Terminal üzerinden interaktif menü ile erişim.

**Çalıştırma:**
```bash
python research_case_generator.py
```

**Avantajları:**
- ✅ Hızlı erişim
- ✅ Script automation desteği
- ✅ JSON export
- ✅ Detaylı log kayıtları

---

### **3. Hızlı Başlatma Script** 🚀

Otomatik admin kontrolü ile hızlı başlatma.

**Çalıştırma:**
```bash
./quick_case_gen.sh
```

**Ne Yapar:**
- Admin kimlik kontrolü
- Environment doğrulama
- Otomatik log kaydı
- CLI başlatma

---

## 🌐 Web Arayüzü Kullanımı

### Adım 1: Şablon Seçimi

Web formunda 4 seçenek bulunur:

#### **A) Hazır Şablonlar**

##### 1️⃣ Akılcı Antibiyotik Kullanımı
- **Hedef Grup:** Aile Hekimleri
- **Odak Alanları:**
  - Gereksiz antibiyotik reçetesi
  - Doğru antibiyotik seçimi
  - Antibiyotik dozajı
  - Tedavi süresi
  - Yan etki yönetimi
  - Hasta eğitimi

**Kullanım Senaryosu:**
> "Aile hekimlerinin antibiyotik reçeteleme davranışlarını değerlendirmek istiyorum."

---

##### 2️⃣ Acil Servis Triyajı
- **Hedef Grup:** Acil Tıp Uzmanları
- **Odak Alanları:**
  - Triyaj kararları
  - İlk stabilizasyon
  - Kritik müdahale
  - Kaynak yönetimi

**Kullanım Senaryosu:**
> "Acil serviste doğru önceliklendirme becerilerini ölçmek istiyorum."

---

##### 3️⃣ Pediatrik Tanısal Akıl Yürütme
- **Hedef Grup:** Pediatristler
- **Odak Alanları:**
  - Gelişimsel değerlendirme
  - Enfeksiyon yönetimi
  - Aşılama
  - Beslenme
  - Büyüme izlemi

**Kullanım Senaryosu:**
> "Pediatristlerin çocuk hastalıkları tanı süreçlerini değerlendirmek istiyorum."

---

#### **B) Özel Direktifler**

Kendi araştırma hedeflerinizi tanımlayın.

**Gerekli Alanlar:**
- Araştırma Başlığı
- Hedef Grup
- Branş
- Odak Alanları (satır satır)
- Ek Direktifler

**Örnek:**
```
Araştırma Başlığı: Kardiyovasküler Risk Değerlendirmesi
Hedef Grup: İç Hastalıkları Uzmanları
Branş: İç Hastalıkları
Odak Alanları:
  - Hipertansiyon yönetimi
  - Dislipidemi tedavisi
  - Diyabet komplikasyonları
  - Risk faktörü analizi
```

---

### Adım 2: Parametreleri Belirleyin

#### **Vaka Sayısı**
- **Aralık:** 1-20
- **Önerilen:** 5-10 (orta ölçekli araştırma)
- **Not:** Her vaka 1-2 dakika sürer

#### **Soru/Vaka**
- **Aralık:** 3-10
- **Önerilen:** 5 (dengeli)
- **Toplam Soru:** Vaka × Soru/Vaka

#### **Zorluk Seviyesi**
- **Kolay:** Temel bilgi, standart vakalar
- **Orta:** Klinik muhakeme gerektiren
- **Zor:** Karmaşık, atipik vakalar
- **Karışık:** Tüm zorluk seviyelerinden

---

### Adım 3: Oluştur ve Kaydet

**"Vaka Seti Oluştur"** butonuna tıklayın.

**Süreç:**
```
1. Form gönderiliyor... ✓
2. Gemini AI bağlantısı... ✓
3. Vakalar oluşturuluyor... (2-10 dakika)
   [=====>    ] 5/10 vaka
4. Altın standart yanıtlar ekleniyor... ✓
5. Veritabanına kaydediliyor... ✓
6. Research ID: 5 oluşturuldu! ✓
```

**Sonuç:**
- ✅ Vakalar veritabanına kaydedildi
- ✅ Research dashboard'a yönlendirildiniz
- ✅ Katılımcılara atanabilir durumda

---

## 💻 CLI Kullanımı

### Başlatma

```bash
cd /workspaces/LLM_research
python research_case_generator.py
```

### İnteraktif Menü

```
╔═══════════════════════════════════════════════════════╗
║     RESEARCH CASE GENERATOR - Gemini AI              ║
╚═══════════════════════════════════════════════════════╝

📋 ARAŞTIRMA ŞABLONLARı:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 💊 Akılcı Antibiyotik Kullanımı (Aile Hekimleri)
2. 🚨 Acil Servis Triyajı (Acil Tıp)
3. 👶 Pediatrik Tanısal Akıl Yürütme (Pediatristler)
0. ✏️  Özel Direktifler

Şablon seçin (0-3): _
```

### Batch Generation

```bash
# Şablon seç: 1 (Antibiyotik)
Vaka sayısı (1-20): 10
Soru sayısı (3-10): 5
Zorluk (1-4): 4

Ek direktifler girebilirsiniz (boş geçmek için Enter):
> Üst solunum yolu enfeksiyonlarına odaklan

🔬 10 vaka oluşturuluyor...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Vaka 1/10: 35 Yaşında Akut Farenjit
✓ Vaka 2/10: 42 Yaşında Akut Bronşit
✓ Vaka 3/10: 28 Yaşında Üriner Enfeksiyon
...
✓ Vaka 10/10: 55 Yaşında Deri Enfeksiyonu

✅ 10/10 vaka başarıyla oluşturuldu!
```

### İşlem Seçenekleri

```
Ne yapmak istersiniz?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Tüm seti kaydet (JSON)
2. Veritabanına yükle
3. Diğer vakaları önizle
4. Yeniden oluştur
0. Çıkış

Seçim (0-4): _
```

---

## 📋 Örnek Senaryolar

### **Senaryo 1: Hızlı Araştırma**

**Hedef:** 5 vakalık pilot araştırma

**Web Arayüzü:**
```
1. Şablon: Akılcı Antibiyotik Kullanımı
2. Vaka: 5
3. Soru/Vaka: 5
4. Zorluk: Karışık
5. Ek direktif: Boş

→ Toplam: 25 soru, ~5 dakika
```

**Sonuç:**
- Research ID: 5
- 25 soru hazır
- Admin panelinden erişilebilir

---

### **Senaryo 2: Geniş Ölçekli Araştırma**

**Hedef:** Kapsamlı antibiyotik kullanımı araştırması

**CLI:**
```bash
python research_case_generator.py

Şablon: 1 (Antibiyotik)
Vaka: 15
Soru/Vaka: 5
Zorluk: 4 (Karışık)
Ek: Üst solunum yolu, üriner sistem, deri-yumuşak doku

→ Toplam: 75 soru, ~15-20 dakika
```

**Sonuç:**
- 15 vaka, 75 soru
- JSON export: `research_antibiotic_stewardship_20251101_150322.json`
- Veritabanında: Research ID 6

---

### **Senaryo 3: Özel Araştırma**

**Hedef:** Kardiyoloji uzmanlarında AKS yönetimi

**Web Arayüzü:**
```
Şablon: Özel Direktifler

Araştırma Başlığı: Akut Koroner Sendrom Yönetimi
Hedef Grup: Kardiyologlar
Branş: Kardiyoloji
Odak Alanları:
  - STEMI tanı ve tedavisi
  - NSTEMI yönetimi
  - Antiagregan tedavi seçimi
  - Invaziv işlem endikasyonları
  - Komplikasyon yönetimi

Vaka: 10
Soru/Vaka: 6
Zorluk: Zor

→ Toplam: 60 soru, ~10-12 dakika
```

---

## ⭐ Altın Standart Özellikleri

Her soru için otomatik oluşturulur:

### 1. **Doğru Cevap**
```json
"correct_answer": "A"
```

### 2. **Altın Standart Gerekçe**
```json
"gold_standard": {
  "answer": "A",
  "rationale": "Akut farenjit vakalarında Centor skorlaması 
               kullanılmalı. Bu hastada skor 3+ olduğu için 
               boğaz kültürü alınmalı ve sonuca göre antibiyotik 
               başlanmalıdır. Ampirik antibiyotik başlamak 
               gereksiz kullanıma yol açar."
}
```

### 3. **Kanıt Düzeyi**
```json
"evidence_level": "1A"
```

**Skalası:**
- **1A:** Sistemik derleme/meta-analiz (en güçlü)
- **1B:** Randomize kontrollü çalışma
- **2A:** Kontrollü çalışma
- **2B:** Yarı-deneysel çalışma
- **3:** Tanımlayıcı çalışmalar
- **4:** Uzman komite raporları
- **5:** Uzman görüşü (en zayıf)

### 4. **Diğer Seçeneklerin Yanlışlığı**
```json
"why_others_wrong": {
  "B": "Derhal antibiyotik başlamak Centor skorlaması 
        göz ardı eder ve gereksiz kullanıma yol açar.",
  "C": "Sadece semptomatik tedavi yetersiz kalabilir.",
  "D": "OKB profilaksisi bu yaş grubunda endike değildir."
}
```

### 5. **Referanslar**
```json
"references": [
  "IDSA 2012 Strep Throat Guidelines",
  "Centor Scoring System",
  "WHO Essential Medicines List"
]
```

### 6. **Scoring Criteria**
```json
"scoring_criteria": {
  "correct_answer": 100,
  "partial_credit": null,
  "explanation": "Doğru cevap için tam puan. 
                  Kanıta dayalı karar verme yetkinliği."
}
```

### 7. **Yetkinlik Değerlendirmesi**
```json
"competency": "Evidence-based decision making in 
               antibiotic prescribing"
```

---

## 🎯 JSON Çıktı Formatı

```json
{
  "metadata": {
    "title": "Akılcı Antibiyotik Kullanımı Araştırması",
    "description": "Aile hekimlerinde antibiyotik kullanımı yetkinliği",
    "target_group": "Aile Hekimleri",
    "specialty": "Aile Hekimliği",
    "focus_areas": [
      "Gereksiz antibiyotik kullanımı",
      "Doğru antibiyotik seçimi",
      "Antibiyotik dozajı ve süresi"
    ],
    "total_cases": 10,
    "total_questions": 50,
    "questions_per_case": 5,
    "difficulty": "mixed",
    "created_at": "2025-11-01T15:03:22"
  },
  "cases": [
    {
      "case_number": 1,
      "research_info": {
        "title": "...",
        "description": "..."
      },
      "case": {
        "title": "35 Yaşında Akut Farenjit",
        "description": "...",
        "questions": [
          {
            "question_number": 1,
            "question_text": "...",
            "options": {
              "A": "...",
              "B": "...",
              "C": "...",
              "D": "..."
            },
            "correct_answer": "A",
            "gold_standard": {
              "answer": "A",
              "rationale": "...",
              "evidence_level": "1A",
              "why_others_wrong": {...},
              "references": [...]
            },
            "scoring_criteria": {
              "correct_answer": 100,
              "explanation": "..."
            },
            "competency": "..."
          }
        ]
      }
    }
  ]
}
```

---

## ❓ Sık Sorulan Sorular

### **S1: Vaka oluşturma ne kadar sürer?**
**C:** Vaka başına ortalama 1-2 dakika. 10 vaka için ~10-15 dakika.

---

### **S2: Kaç vaka oluşturabilirim?**
**C:** Tek seferde 1-20 vaka. Daha fazla için birden çok batch çalıştırın.

---

### **S3: Hazır şablon yetersiz kalırsa?**
**C:** "Ek Direktifler" alanını kullanın veya "Özel Direktifler" seçeneğini tercih edin.

---

### **S4: Altın standart yanıtlar düzenlenebilir mi?**
**C:** Evet, veritabanına kaydedildikten sonra admin panelinden `ReferenceAnswer` tablosundan düzenleyebilirsiniz.

---

### **S5: JSON export'u nasıl kullanırım?**
**C:** CLI'dan "Tüm seti kaydet" seçeneği ile JSON export alabilirsiniz. Bu dosya başka sistemlere aktarılabilir.

---

### **S6: Gemini API key'i yoksa ne olur?**
**C:** `.env` dosyasında `GEMINI_API_KEY` tanımlı olmalıdır. Yoksa vaka oluşturulamaz.

---

### **S7: Veritabanına yüklenen vakalar nasıl görüntülenir?**
**C:** Admin paneli → Research Dashboard → İlgili Research ID'ye tıklayın.

---

### **S8: Batch generation sırasında hata oluşursa?**
**C:** 
- İnternet bağlantısını kontrol edin
- Gemini API key'ini doğrulayın
- Terminalde hata loglarına bakın
- Vaka sayısını azaltıp tekrar deneyin

---

### **S9: Farklı dillerde vaka oluşturulabilir mi?**
**C:** Şu anda sadece Türkçe destekleniyor. İngilizce için `research_case_generator.py` içindeki prompt'ları düzenleyin.

---

### **S10: Web ve CLI arasındaki fark nedir?**

| Özellik | Web Arayüzü | CLI |
|---------|-------------|-----|
| Kullanım | 🌐 Tarayıcı | 💻 Terminal |
| Arayüz | Form tabanlı | Menü tabanlı |
| Önizleme | ✅ Var | ⚠️ Sınırlı |
| JSON Export | ⚠️ Manuel | ✅ Otomatik |
| Automation | ❌ Yok | ✅ Script desteği |
| Hata Yönetimi | ✅ Flash mesajları | ⚠️ Console log |

**Öneri:** Hızlı kullanım için Web, automation için CLI.

---

## 🔧 Troubleshooting

### Sorun 1: "GEMINI_API_KEY bulunamadı"
```bash
# .env dosyasını kontrol edin
cat .env | grep GEMINI_API_KEY

# Yoksa ekleyin
echo "GEMINI_API_KEY=your_api_key_here" >> .env
```

---

### Sorun 2: "Import Error: ResearchCaseGenerator"
```bash
# Script'in varlığını kontrol edin
ls -la research_case_generator.py

# Executable yetkisi verin
chmod +x research_case_generator.py
```

---

### Sorun 3: Web arayüzünde "404 Not Found"
```bash
# Flask uygulamasının çalıştığını kontrol edin
curl http://localhost:8080/admin/case-generator

# Çalışmıyorsa başlatın
python app.py
```

---

### Sorun 4: "Database Error"
```bash
# Migration'ları çalıştırın
flask db upgrade

# Veritabanını kontrol edin
python -c "from app import db; print(db.engine.url)"
```

---

## 📚 İlgili Dökümanlar

- **[Research Case Generator](RESEARCH_CASE_GENERATOR.md)** - Detaylı teknik döküman
- **[Case Generator](CASE_GENERATOR.md)** - Normal vaka oluşturucu
- **[README_ADMIN.md](README_ADMIN.md)** - Admin paneli genel kullanım
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Proje mimarisi

---

## 🎉 Özet

Research Case Generator ile:

✅ **3 hazır şablon** veya özel direktifler  
✅ **1-20 vaka** toplu üretim  
✅ **Altın standart** yanıtlar + kanıt düzeyi  
✅ **Web arayüzü** veya CLI erişim  
✅ **Otomatik veritabanı** entegrasyonu  
✅ **JSON export** desteği  

**Artık akademik kalitede araştırma vakaları oluşturabilirsiniz! 🔬**

---

**Son Güncelleme:** 1 Kasım 2025  
**Versiyon:** 1.0  
**Katkıda Bulunanlar:** LLM Research Team
