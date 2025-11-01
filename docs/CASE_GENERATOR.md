# 🏥 Case Generator - Kullanım Kılavuzu

## 🎯 Genel Bakış

**Case Generator**, Gemini AI kullanarak tıbbi vaka soruları oluşturan interaktif bir CLI aracıdır.

---

## ✨ Özellikler

- ✅ **8 Tıp Branşı:** Pediatri, İç Hastalıkları, Cerrahi, Acil, Aile Hekimliği, Nöroloji, Kardiyoloji, Psikiyatri
- ✅ **4 Zorluk Seviyesi:** Kolay, Orta, Zor, Uzman
- ✅ **Özelleştirilebilir:** Yaş aralığı, soru sayısı, özel gereksinimler
- ✅ **Önizleme:** Oluşturulan vakayı görüntüle
- ✅ **Düzenleme:** İstediğin alanı değiştir
- ✅ **Yeniden Üretme:** Beğenmezsen yeniden oluştur
- ✅ **JSON Export:** Dosya olarak kaydet
- ✅ **DB Import:** Doğrudan veritabanına yükle
- ✅ **Renkli CLI:** Kullanıcı dostu arayüz

---

## 🚀 Hızlı Başlangıç

### 1. Script'i Çalıştır

```bash
python case_generator.py
```

veya

```bash
./case_generator.py
```

### 2. Parametreleri Seç

Script sırayla şunları soracak:

1. **Tıp Branşı** (1-8)
   - Pediatri, İç Hastalıkları, vb.

2. **Zorluk Seviyesi** (1-4)
   - Kolay, Orta, Zor, Uzman

3. **Hasta Yaş Aralığı**
   - Örnek: `5-10`, `20-40`, `60-80`

4. **Soru Sayısı** (3-10)
   - Vakada kaç soru olacak

5. **Özel Gereksinimler** (opsiyonel)
   - Örnek: "Kardiyak arrest senaryosu", "Zehirlenme vakası"

### 3. Vakayı İncele

Gemini AI vakayı oluşturduktan sonra:

- 📋 Vaka başlığı
- 🏥 Branş ve zorluk
- 📝 Hasta hikayesi
- ❓ Sorular ve seçenekler
- ✓ Doğru cevaplar (yeşil renkte)
- 💡 Açıklamalar
- 🎯 Öğrenme hedefleri
- 📚 Kaynaklar

### 4. İşlem Seç

```
1. ✓ Vakayı kaydet (JSON)
2. 📤 Veritabanına yükle
3. ✏️  Düzenle
4. 🔄 Yeniden oluştur
5. 🗑️  İptal et
0. ❌ Çıkış
```

---

## 📋 Kullanım Örnekleri

### Örnek 1: Pediatrik Vaka (Kolay)

```bash
$ python case_generator.py

Tıp Branşı: 1 (Pediatri)
Zorluk: 1 (Kolay)
Yaş Aralığı: 2-5
Soru Sayısı: 5
Özel Gereksinimler: Üst solunum yolu enfeksiyonu

→ Vaka oluşturuldu
→ Önizle
→ Kaydet: pediatric_case_20251101_143022.json
```

### Örnek 2: Acil Tıp (Zor)

```bash
$ python case_generator.py

Tıp Branşı: 4 (Acil Tıp)
Zorluk: 3 (Zor)
Yaş Aralığı: 45-60
Soru Sayısı: 7
Özel Gereksinimler: STEMI, kardiyak arrest

→ Vaka oluşturuldu
→ Önizle
→ Düzenle (soru 3'ü değiştir)
→ Veritabanına yükle
```

### Örnek 3: Nöroloji (Uzman)

```bash
$ python case_generator.py

Tıp Branşı: 6 (Nöroloji)
Zorluk: 4 (Uzman)
Yaş Aralığı: 30-50
Soru Sayısı: 8
Özel Gereksinimler: Multiple sclerosis, relaps

→ Vaka oluşturuldu
→ Beğenmedim, yeniden oluştur
→ Yeni vaka oluşturuldu
→ Kaydet + Veritabanına yükle
```

---

## ✏️ Düzenleme Özellikleri

Vakayı oluşturduktan sonra şunları düzenleyebilirsin:

1. **Başlık** - Vaka başlığını değiştir
2. **Vaka Hikayesi** - Hasta hikayesini yeniden yaz
3. **Soru Metni** - Belirli bir soruyu düzenle
4. **Seçenekler** - A, B, C, D, E seçeneklerini değiştir
5. **Doğru Cevap** - Doğru seçeneği değiştir
6. **Açıklama** - Açıklama metnini düzenle

**Örnek Düzenleme Akışı:**

```
Düzenle → 3 (Soru metni)
Hangi soru? 2
Yeni soru metni: Hastaya ilk yapılması gereken tetkik nedir?
✓ Soru metni güncellendi

Düzenle → 5 (Doğru cevap)
Hangi soru? 2
Yeni doğru cevap: C
✓ Doğru cevap güncellendi
```

---

## 💾 Kaydetme Seçenekleri

### Option 1: JSON Dosyası

```bash
Seçim: 1 (Kaydet)
Dosya adı: my_case.json
✓ Kaydedildi: /workspaces/LLM_research/my_case.json
```

**JSON formatı:**

```json
{
  "title": "5 Yaşında Öksürük ve Ateş",
  "specialty": "pediatrics",
  "difficulty": "easy",
  "patient_age": "2-5",
  "case_description": "...",
  "questions": [...],
  "references": [...],
  "learning_objectives": [...]
}
```

### Option 2: Veritabanına Yükle

```bash
Seçim: 2 (Veritabanına yükle)
✓ Vaka veritabanına yüklendi (Research ID: 12, Case ID: 34)

Admin panelinden görüntüle:
http://localhost:8080/admin
```

---

## 🎨 Renk Kodları

Script renkli çıktı kullanır:

- 🟢 **Yeşil** - Başarılı işlemler, doğru cevaplar
- 🔵 **Mavi** - Bilgilendirme mesajları
- 🟡 **Sarı** - Uyarılar, kullanıcı seçimleri
- 🔴 **Kırmızı** - Hatalar
- 🟣 **Magenta** - Sorular
- 🔷 **Cyan** - Başlıklar, etiketler

---

## ⚙️ Gelişmiş Özellikler

### 1. Özel Gereksinimler

Gemini'ye özel talimatlar verebilirsin:

```
Özel gereksinimler:
- "Kardiyak arrest senaryosu"
- "Çocuk istismarı belirtileri içersin"
- "Elektrolit bozukluğu ve EKG bulguları"
- "Akut böbrek yetmezliği, diyaliz kararı"
- "Nörolojik muayene bulguları detaylı olsun"
```

### 2. Batch Generation (Gelecek Özellik)

Tek seferde birden fazla vaka oluştur:

```bash
python case_generator.py --batch 10 --specialty pediatrics
```

### 3. Template Kullanımı (Gelecek Özellik)

Kendi şablonunu oluştur:

```bash
python case_generator.py --template my_template.json
```

---

## 🐛 Sorun Giderme

### Hata: GEMINI_API_KEY bulunamadı

**Çözüm:**

```bash
export GEMINI_API_KEY='your-api-key-here'
```

veya `.env` dosyasına ekle:

```
GEMINI_API_KEY=your-api-key-here
```

### Hata: JSON parse hatası

**Neden:** Gemini bazen markdown formatında yanıt verebilir.

**Çözüm:** Script otomatik temizler, ama yine de hata alıyorsan:
- Yeniden dene (Option 4)
- Farklı parametreler kullan

### Hata: Veritabanına yüklenemedi

**Çözüm:**

```bash
# Veritabanını başlat
python init_db.py

# Flask app'in çalıştığından emin ol
python app.py
```

---

## 📊 Vaka Kalite Kriterleri

Generator şu kriterlere uygun vakalar oluşturur:

### Vaka Hikayesi
- ✅ 150-300 kelime
- ✅ Başvuru şikayeti net
- ✅ Semptom süresi belirtilmiş
- ✅ İlgili tıbbi geçmiş
- ✅ Fizik muayene bulguları
- ✅ Lab/görüntüleme sonuçları (gerekiyorsa)

### Sorular
- ✅ Açık ve net
- ✅ 4-5 mantıklı seçenek
- ✅ Tek doğru cevap
- ✅ Detaylı açıklama
- ✅ Farklı konuları kapsıyor:
  - Tanı
  - Ayırıcı tanı
  - Tedavi
  - İlk yaklaşım
  - Prognostik faktörler
  - Komplikasyonlar

---

## 🎯 İpuçları

1. **Spesifik Ol:** Özel gereksinimlerde detaylı ol
   - ❌ "Kardiyoloji vakası"
   - ✅ "STEMI, anterior duvar MI, tromboliz endikasyonları"

2. **Uygun Zorluk:** Hedef kitlene göre seç
   - Tıp öğrencisi → Kolay
   - Asistan → Orta
   - Uzman → Zor
   - Profesör → Uzman

3. **Yaş Aralığı:** Branşa uygun yaş seç
   - Pediatri: 0-18
   - Geriatri: 65+
   - İç Hastalıkları: 20-80

4. **Soru Sayısı:** Vakaya göre ayarla
   - Basit vaka: 3-5 soru
   - Komplex vaka: 6-10 soru

5. **Önce Önizle:** Hemen kaydetme, önce incele
   - Önizle → Düzenle → Kaydet

---

## 📚 Ek Kaynaklar

- **Ana Dokümantasyon:** [docs/README_FULL.md](../docs/README_FULL.md)
- **Admin Kılavuzu:** [docs/README_ADMIN.md](../docs/README_ADMIN.md)
- **Gemini API:** [https://ai.google.dev/](https://ai.google.dev/)
- **Proje Mimarisi:** [docs/PROJECT_SUMMARY.md](../docs/PROJECT_SUMMARY.md)

---

## 🤝 Katkıda Bulunma

Yeni özellikler eklemek için:

1. `case_generator.py` dosyasını düzenle
2. Template'lere yeni branş ekle
3. Prompt'u geliştir
4. Test et

---

**Versiyon:** 1.0  
**Son Güncelleme:** 2025-11-01  
**Geliştirici:** LLM Research Team
