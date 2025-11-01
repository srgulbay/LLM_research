# 🔬 Research Case Generator - Kullanım Kılavuzu

## 🎯 Genel Bakış

**Research Case Generator**, araştırma odaklı tıbbi vaka setleri oluşturan gelişmiş bir AI aracıdır. Yönetici direktiflerine göre sentetik vakalar ve **altın standart yanıtlar** üretir.

---

## ✨ Temel Farklar (Normal Case Generator'dan)

| Özellik | Normal Generator | Research Generator |
|---------|------------------|-------------------|
| **Amaç** | Tek vaka oluşturma | Araştırma seti oluşturma |
| **Yöntem** | Tekli üretim | Toplu (batch) üretim |
| **Direktifler** | Genel parametreler | Araştırma odaklı direktifler |
| **Yanıtlar** | Basit açıklama | Altın standart + kanıt düzeyi |
| **Puanlama** | Standart | Özel scoring criteria |
| **Referanslar** | Genel | Kılavuz ve kanıt bazlı |
| **Hedef** | Eğitim/pratik | Akademik araştırma |

---

## 🚀 Hızlı Başlangıç

### 1. Script'i Çalıştır

```bash
python research_case_generator.py
```

veya

```bash
./research_case_generator.py
```

### 2. Araştırma Şablonu Seç

**Hazır Şablonlar:**
1. **Akılcı Antibiyotik Kullanımı** (Aile Hekimleri)
2. **Acil Servis Triyajı** (Acil Tıp)
3. **Pediatrik Tanı** (Pediatristler)
0. **Özel Direktifler** (Manuel giriş)

### 3. Parametreleri Belirle

- Vaka sayısı (1-20)
- Soru sayısı/vaka (3-10)
- Zorluk dağılımı (kolay, orta, zor, karışık)
- Ek direktifler

### 4. Toplu Üretim

Generator tüm vakaları otomatik oluşturur ve size sunar.

---

## 📋 Örnek: Akılcı Antibiyotik Kullanımı Araştırması

### Senaryo

> **Araştırma Sorusu:** Aile hekimliği uzmanları akılcı antibiyotik kullanımı konusunda doğru kararlar veriyor mu?
> 
> **Hedef:** 10 vaka, her biri 5 soru (toplam 50 soru)
> 
> **Odak Alanları:**
> - Gereksiz antibiyotik reçetesi
> - Doğru antibiyotik seçimi
> - Antibiyotik dozajı
> - Tedavi süresi
> - Yan etki yönetimi
> - Hasta eğitimi

### Kullanım Adımları

```bash
$ python research_case_generator.py

╔══════════════════════════════════════════════════════════╗
║          🔬 LLM RESEARCH CASE GENERATOR                  ║
╚══════════════════════════════════════════════════════════╝

Araştırma odaklı tıbbi vaka setleri oluşturun!
Yönetici direktiflerine göre sentetik vakalar ve altın standart yanıtlar.

🔬 ARAŞTIRMA DİREKTİFLERİ
═════════════════════════

📋 Araştırma Şablonu Seçin:
  0. Özel araştırma direktifleri
  1. Akılcı Antibiyotik Kullanımı
     Hedef: Aile Hekimleri
  2. Acil Servis Triyajı
     Hedef: Acil Tıp Uzmanları
  3. Pediatrik Tanı
     Hedef: Pediatristler

Seçim: 1

📋 Araştırma: Akılcı Antibiyotik Kullanımı
🎯 Hedef Grup: Aile Hekimleri

Odak Alanları:
  • Gereksiz antibiyotik reçetesi
  • Doğru antibiyotik seçimi
  • Antibiyotik dozajı
  • Tedavi süresi
  • Yan etki yönetimi
  • Hasta eğitimi

Kaç vaka? 10
Her vakada kaç soru? 5

Ek direktifler:
> Vakalar üst solunum yolu enfeksiyonları, üriner sistem enfeksiyonları
> ve deri-yumuşak doku enfeksiyonlarını kapsasın

Zorluk dağılımı:
  1. Tümü kolay
  2. Tümü orta
  3. Tümü zor
  4. Karışık

Seçim: 4 (Karışık)

═══════════════════════════════════════════════════════════

📋 ARAŞTIRMA ÖZETİ
═════════════════

Başlık: Akılcı Antibiyotik Kullanımı
Hedef: Aile Hekimleri
Vaka Sayısı: 10
Soru/Vaka: 5
Toplam Soru: 50

Devam etmek istiyor musunuz? e

🚀 TOPLU VAKA ÜRETİMİ (10 vaka)
═══════════════════════════════

ℹ Vaka 1/10 oluşturuluyor...
✓ Vaka 1 oluşturuldu!

ℹ Vaka 2/10 oluşturuluyor...
✓ Vaka 2 oluşturuldu!

...

✓ 10/10 vaka başarıyla oluşturuldu!

👁️ VAKA ÖNİZLEME
════════════════

🔬 Araştırma: Akılcı Antibiyotik Kullanımı
👥 Hedef Grup: Aile Hekimleri
📊 Vaka: 1/10

📋 Başlık: 35 Yaşında Akut Farenjit
📊 Zorluk: medium
👤 Yaş: 30-40

────────────────────────────────────────────────────────────
📝 VAKA HİKAYESİ:
35 yaşında kadın hasta, 3 gündür devam eden boğaz ağrısı,
yutma güçlüğü ve hafif ateş şikayetiyle başvurdu. Hastanın
öksürük, burun akıntısı yok. Fizik muayenede farinks hiperemik,
tonsiller hipertrofik, eksüda izlenmiyor. Ateş: 37.8°C
────────────────────────────────────────────────────────────

🎯 Öğrenme Hedefleri:
  • Akut farenjitta antibiyotik endikasyonu değerlendirme
  • Centor skorlaması uygulama
  • Gereksiz antibiyotik kullanımından kaçınma

❓ Soru 1: Bu hastada ilk yapılması gereken değerlendirme?
   Tip: diagnosis
   Yetkinlik: Tanı koyma

  ⭐ A) Centor skoru hesapla ve strep testi yap
     B) Hemen amoksisilin başla
     C) Geniş spektrumlu antibiyotik başla
     D) Viral enfeksiyon kabul et, antibiyotik verme

⭐ ALTIN STANDART:
   Cevap: A
   Gerekçe: Akut farenjitin bakteriyel (Grup A streptokok)
   mi viral mi olduğunu ayırt etmek için Centor skorlaması
   kullanılmalıdır. Centor skoru ≥3 ise strep testi yapılmalı.
   Bu hasta için: Ateş (1 puan), tonsillit (1 puan), öksürük
   yok (1 puan) = 3 puan. Strep testi endikasyonu var.
   
   Kanıt Düzeyi: 1A

❌ Diğer Seçenekler Neden Yanlış:
   B: Tanı konmadan antibiyotik başlamak akılcı değil.
      %50-80 oranında viral.
   C: Geniş spektrumlu antibiyotik gereksiz ve dirençe yol açar.
   D: Centor skoru yüksek, test yapmadan viral kabul etmek
      strep komplikasyonu riskini artırır.

📊 Puanlama:
   Doğru: 100 puan
   Doğru cevap 100 puan. Diğerleri 0 puan çünkü tanı
   algoritması ve kanıta dayalı yaklaşımdan sapıyorlar.

📚 Kaynaklar:
   • IDSA 2012 Grup A Streptokok Farenjit Kılavuzu
   • Centor RM. et al. N Engl J Med. 2013

────────────────────────────────────────────────────────────

Ne yapmak istersiniz?
1. ✓ Tüm setı kaydet (JSON)
2. 📤 Veritabanına yükle
3. 👁️  Diğer vakaları önizle
4. 🔄 Tüm seti yeniden oluştur
0. ❌ Çıkış

Seçim: 2

✓ Araştırma veritabanına yüklendi!
ℹ Research ID: 5
ℹ Toplam 10 vaka, 50 soru

Admin panelinden görüntüleyin:
  http://localhost:8080/admin

Seçim: 1

✓ Kaydedildi: research_antibiotic_stewardship_20251101_150322.json

Seçim: 0

ℹ Güle güle!
```

---

## 🎯 Altın Standart Yanıtlar

Her soru için üretilen bilgiler:

### 1. Doğru Cevap
```json
"correct_answer": "A"
```

### 2. Altın Standart Gerekçe
```json
"gold_standard": {
  "answer": "A",
  "rationale": "Neden bu cevap altın standart? Kanıt nedir?",
  "evidence_level": "1A"
}
```

**Kanıt Düzeyleri:**
- **1A**: Sistemik derleme/meta-analiz (en güçlü)
- **1B**: En az bir randomize kontrollü çalışma
- **2A**: En az bir iyi dizayn edilmiş kontrollü çalışma
- **2B**: En az bir iyi dizayn edilmiş yarı-deneysel çalışma
- **3**: İyi dizayn edilmiş tanımlayıcı çalışmalar
- **4**: Uzman komite raporları
- **5**: Uzman görüşü (en zayıf)

### 3. Diğer Seçenekler Neden Yanlış
```json
"why_others_wrong": {
  "B": "B seçeneği neden yanlış/suboptimal",
  "C": "C seçeneği neden yanlış/suboptimal",
  "D": "D seçeneği neden yanlış/suboptimal"
}
```

### 4. Scoring Criteria
```json
"scoring_criteria": {
  "correct_answer": 100,
  "partial_credit": {
    "B": 0,
    "C": 0,
    "D": 0
  },
  "explanation": "Puanlama mantığı..."
}
```

### 5. Referanslar
```json
"references": [
  "IDSA 2012 Grup A Streptokok Farenjit Kılavuzu",
  "Centor RM. et al. N Engl J Med. 2013"
]
```

---

## 📊 JSON Çıktı Formatı

```json
{
  "metadata": {
    "title": "Akılcı Antibiyotik Kullanımı",
    "description": "...",
    "target_group": "Aile Hekimleri",
    "focus_areas": [...],
    "created_at": "20251101_150322",
    "total_cases": 10,
    "questions_per_case": 5
  },
  "cases": [
    {
      "research_info": {
        "title": "Akılcı Antibiyotik Kullanımı",
        "target_group": "Aile Hekimleri",
        "case_number": 1,
        "total_cases": 10
      },
      "case": {
        "title": "35 Yaşında Akut Farenjit",
        "difficulty": "medium",
        "patient_age": "30-40",
        "case_description": "...",
        "learning_objectives": [...],
        "focus_areas": [...],
        "questions": [
          {
            "question_number": 1,
            "question_text": "...",
            "question_type": "diagnosis",
            "options": [...],
            "correct_answer": "A",
            "gold_standard": {
              "answer": "A",
              "rationale": "...",
              "why_others_wrong": {...},
              "evidence_level": "1A",
              "references": [...]
            },
            "scoring_criteria": {...},
            "competency_assessed": "..."
          }
        ]
      }
    }
  ]
}
```

---

## 🔧 Özel Araştırma Direktifleri

Hazır şablon yerine kendi direktiflerinizi girebilirsiniz:

```bash
Seçim: 0 (Özel)

📝 ÖZEL ARAŞTIRMA DİREKTİFLERİ

Araştırma başlığı: 
> Obezite Yönetiminde Davranışsal Müdahaleler

Araştırma açıklaması:
> İç hastalıkları ve aile hekimliği uzmanlarının obez hastalarda
> davranışsal müdahale ve yaşam tarzı değişikliği önerme becerilerini
> değerlendirme

Hedef grup:
> Aile Hekimleri ve İç Hastalıkları Uzmanları

Odak alanları (boş satır ile bitir):
Odak alanı: Motivasyonel görüşme teknikleri
Odak alanı: Diyet ve egzersiz planı
Odak alanı: Davranış değişikliği stratejileri
Odak alanı: Farmakoterapiye geçiş kararı
Odak alanı: Multidisipliner yaklaşım
Odak alanı: 
(boş satır - bitti)

Kaç vaka? 8
Her vakada kaç soru? 6

→ Toplam 48 soru oluşturulacak
```

---

## 🎨 Araştırma Şablonları

### 1. Akılcı Antibiyotik Kullanımı

**Hedef Grup:** Aile Hekimleri

**Odak Alanları:**
- Gereksiz antibiyotik reçetesi önleme
- Doğru antibiyotik seçimi
- Antibiyotik dozajı
- Tedavi süresi
- Yan etki yönetimi
- Hasta eğitimi

**Örnek Vakalar:**
- Üst solunum yolu enfeksiyonları
- Üriner sistem enfeksiyonları
- Deri-yumuşak doku enfeksiyonları
- Akut bronşit
- Sinüzit

### 2. Acil Servis Triyajı

**Hedef Grup:** Acil Tıp Uzmanları

**Odak Alanları:**
- Triyaj kararları (kırmızı, sarı, yeşil)
- İlk stabilizasyon
- Kritik müdahale (ABC)
- Kaynak yönetimi

**Örnek Vakalar:**
- Travma
- Göğüs ağrısı
- Dispne
- Bilinç bulanıklığı
- Zehirlenme

### 3. Pediatrik Tanı

**Hedef Grup:** Pediatristler

**Odak Alanları:**
- Gelişimsel değerlendirme
- Enfeksiyon yönetimi
- Aşılama
- Beslenme sorunları
- Büyüme izlemi

**Örnek Vakalar:**
- Ateş yönetimi
- Büyüme geriliği
- Beslenme sorunları
- Gelişimsel gerilik
- Çocukluk çağı enfeksiyonları

---

## 💡 En İyi Uygulamalar

### 1. Araştırma Tasarımı

✅ **İyi:**
- Spesifik araştırma sorusu tanımla
- Net hedef grup belirle
- Odak alanlarını sınırla (4-6 alan)
- Yeterli vaka sayısı (8-15)
- Sorularımın dengeli dağılımı

❌ **Kötü:**
- Belirsiz araştırma sorusu
- Çok geniş hedef grup
- Çok fazla odak alanı
- Az vaka (<5) veya çok fazla (>20)

### 2. Vaka Sayısı

- **Pilot çalışma:** 5-8 vaka
- **Ana çalışma:** 10-15 vaka
- **Geniş çalışma:** 15-20 vaka

### 3. Soru Sayısı

- **Kısa vaka:** 3-4 soru
- **Orta vaka:** 5-6 soru
- **Uzun vaka:** 7-10 soru

### 4. Zorluk Dağılımı

**Karışık (Önerilen):**
- 30% kolay
- 40% orta
- 30% zor

### 5. Ek Direktifler

Spesifik ol:

✅ **İyi:**
```
"Vakalar sadece birinci basamak sağlık hizmetlerinde karşılaşılan
durumları içersin. Laboratuvar ve görüntüleme tetkiklerine erişim
sınırlı olsun. Hasta eğitimi ve takip kararları vurgulansın."
```

❌ **Kötü:**
```
"İyi vakalar olsun"
```

---

## 🔍 Kalite Kontrol

### Kontrol Listesi

Her vaka için kontrol edin:

- [ ] Vaka hikayesi gerçekçi mi?
- [ ] Sorular araştırma sorusuna uygun mu?
- [ ] Altın standart yanıt net mi?
- [ ] Kanıt düzeyi belirtilmiş mi?
- [ ] Referanslar gerçek mi?
- [ ] Diğer seçeneklerin yanlışlığı açıklanmış mı?
- [ ] Scoring criteria mantıklı mı?
- [ ] Yetkinlik değerlendirmesi uygun mu?

---

## 📤 Veritabanına Yükleme

Araştırma setini veritabanına yüklediğinizde:

1. **Research** kaydı oluşturulur
2. Her vaka için **Case** kaydı oluşturulur
3. Her soru için **ReferenceAnswer** kaydı oluşturulur

**ReferenceAnswer** tablosunda saklananlar:
- Doğru cevap
- Altın standart gerekçe
- Kanıt düzeyi
- Referanslar (JSON)

**Admin Panelinden:**
- Vakaları görüntüle
- Katılımcı yanıtlarını topla
- Altın standart ile karşılaştır
- Otomatik puanlama (Gemini AI)
- Analiz ve raporlar

---

## 🎯 Kullanım Senaryoları

### Senaryo 1: Uzmanlık Eğitimi Değerlendirmesi

**Durum:** Aile hekimliği asistan eğitiminde akılcı antibiyotik kullanımı yetkinliğini ölçmek istiyorsunuz.

**Adımlar:**
1. Template 1'i seç (Akılcı Antibiyotik)
2. 10 vaka, 5 soru/vaka
3. Karışık zorluk
4. Veritabanına yükle
5. Asistanlara gönder
6. Sonuçları analiz et

### Senaryo 2: Kılavuz Uyum Araştırması

**Durum:** Kardiyologların ESC kalp yetersizliği kılavuzuna uyumunu araştırıyorsunuz.

**Adımlar:**
1. Özel direktifler gir
2. Araştırma: "Kalp Yetersizliği Kılavuz Uyumu"
3. Odak: Tanı, tedavi başlangıcı, titrasyonu, takip
4. 12 vaka, 6 soru/vaka
5. Sadece ESC 2021 kılavuzuna referans ver

### Senaryo 3: Çok Merkezli Çalışma

**Durum:** 5 farklı hastanede acil servis triyaj becerilerini karşılaştırıyorsunuz.

**Adımlar:**
1. Template 2'yi seç (Acil Triyaj)
2. 15 vaka, standardize edilmiş
3. Tüm merkezlere aynı vaka setini gönder
4. Sonuçları merkezler arası karşılaştır

---

## 📚 Ek Kaynaklar

- **Case Generator:** [case_generator.py](../case_generator.py) - Tekli vaka oluşturma
- **CASE_GENERATOR.md:** Normal generator kılavuzu
- **README.md:** Proje ana sayfası
- **Admin Kılavuzu:** [docs/README_ADMIN.md](README_ADMIN.md)

---

## 🐛 Sorun Giderme

### Hata: "JSON parse hatası"

**Çözüm:**
- Gemini bazen hatalı JSON üretebilir
- "Tüm seti yeniden oluştur" seçeneğini dene
- Vaka sayısını azalt (örn: 10 yerine 5)

### Hata: "Veritabanına yüklenemedi"

**Çözüm:**
```bash
python init_db.py
python app.py
```

### Önizleme sorunları

**Çözüm:**
- Terminal genişliğini artır
- Renkler görünmüyorsa: `pip install colorama`

---

**Versiyon:** 1.0  
**Son Güncelleme:** 2025-11-01  
**Geliştirici:** LLM Research Team
