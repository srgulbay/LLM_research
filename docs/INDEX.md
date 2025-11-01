# 📚 Dokümantasyon İndeksi

LLM Research Platform v3.0 için tüm dokümantasyon dosyaları.

---

## 📖 Kullanıcı Dokümantasyonu

### 🚀 Başlangıç
- **[Ana README](../README.md)** - Projeye hızlı giriş ve temel bilgiler
- **[Detaylı Kılavuz](README_FULL.md)** - Kapsamlı kurulum ve kullanım rehberi

### 👤 Kullanım Kılavuzları
- **[Admin Kılavuzu](README_ADMIN.md)** - Yönetici paneli kullanımı
  - Admin kullanıcı oluşturma
  - Araştırma yönetimi
  - Kullanıcı yönetimi
  - LLM konfigürasyonu
  - İstatistik ve raporlar

- **[Bakım Modu](README_MAINTENANCE.md)** - Sistem bakım yönetimi
  - Bakım modunu açma/kapatma
  - CLI kullanımı
  - Admin panel kontrolü
  - Özelleştirilmiş mesajlar

- **[Case Generator](CASE_GENERATOR.md)** - 🆕 AI ile vaka oluşturma
  - Gemini AI entegrasyonu
  - İnteraktif CLI arayüzü
  - 8 tıp branşı, 4 zorluk seviyesi
  - Önizleme ve düzenleme
  - JSON export ve DB import

- **[Research Case Generator](RESEARCH_CASE_GENERATOR.md)** - 🆕 Araştırma odaklı vaka setleri
  - Yönetici direktifleri ile üretim
  - Altın standart yanıtlar + kanıt düzeyi
  - Toplu (batch) üretim (1-20 vaka)
  - Scoring criteria tanımlama
  - Araştırma şablonları
  - Akademik format çıktı

- **[Admin Case Generator](ADMIN_CASE_GENERATOR.md)** - 🆕 Yönetici panel entegrasyonu
  - Web arayüzü ile vaka oluşturma
  - 3 hazır şablon + özel direktifler
  - Form validasyonu ve önizleme
  - Otomatik veritabanı kaydı
  - CLI ve web erişimi
  - Adım adım kullanım kılavuzu

---

## 🔧 Teknik Dokümantasyon

### 📐 Mimari ve Tasarım
- **[Proje Özeti](PROJECT_SUMMARY.md)** - Sistem mimarisi ve teknolojiler
  - Database modelleri (8 tablo)
  - API endpoint'leri (12 route)
  - Gemini AI entegrasyonu
  - Background job sistemi
  - Analitik modülleri

### 🎨 Kodlama Standartları
- **[Dosya İsimlendirme](README_NAMING.md)** - İsimlendirme kuralları
  - Python dosyaları: `lowercase_with_underscores.py`
  - Markdown dosyaları: `UPPERCASE_WITH_UNDERSCORES.md`
  - JSON dosyaları: `lowercase_with_underscores.json`
  - Klasörler: `lowercase`

### 🔄 Geliştirme Geçmişi
- **[Değişiklikler](CHANGELOG.md)** - Versiyon geçmişi
  - v3.0: Anonim kullanıcılar, gelişmiş analitik, API
  - v2.x: Temel özellikler
  - v1.x: İlk versiyon

- **[Reorganizasyon Raporu](REORGANIZATION_REPORT.md)** - Son düzenleme detayları
  - Dosya standardizasyonu
  - Cleanup işlemleri
  - Yeni klasör yapısı

---

## 📊 Dosya Kategorileri

| Kategori | Dosyalar | Amaç | Hedef Kitle |
|----------|----------|------|-------------|
| **Başlangıç** | `README.md`, `README_FULL.md` | Projeye hızlı başlangıç | Yeni kullanıcılar |
| **Yönetim** | `README_ADMIN.md`, `README_MAINTENANCE.md` | Admin işlemleri | Yöneticiler |
| **Teknik** | `PROJECT_SUMMARY.md`, `README_NAMING.md` | Geliştirici bilgileri | Geliştiriciler |
| **Geçmiş** | `CHANGELOG.md`, `REORGANIZATION_REPORT.md` | Versiyon ve değişiklikler | Tüm kullanıcılar |

---

## 🔍 Hızlı Arama

### Kurulum ve Çalıştırma

**Q: Projeyi nasıl kurulum yapabilirim?**  
→ [`README_FULL.md` - Kurulum](README_FULL.md#kurulum)

**Q: Gemini API nasıl yapılandırılır?**  
→ [`README_FULL.md` - Gemini API](README_FULL.md#gemini-api-configuration)

**Q: Database'i nasıl başlatırım?**  
→ [`README_FULL.md` - Database](README_FULL.md#database-setup)

### Admin İşlemleri

**Q: Admin kullanıcı nasıl oluşturulur?**  
→ [`README_ADMIN.md` - Admin Oluşturma](README_ADMIN.md#admin-user-creation)

**Q: Araştırma nasıl yüklenir?**  
→ [`README_ADMIN.md` - Araştırma Yükleme](README_ADMIN.md#research-upload)

**Q: LLM puanlaması nasıl yapılır?**  
→ [`README_ADMIN.md` - LLM Skorlama](README_ADMIN.md#llm-scoring)

### Bakım ve Yönetim

**Q: Bakım modunu nasıl açarım?**  
→ [`README_MAINTENANCE.md` - Kullanım](README_MAINTENANCE.md#usage)

**Q: Bakım mesajı nasıl özelleştirilir?**  
→ [`README_MAINTENANCE.md` - Mesaj Şablonları](README_MAINTENANCE.md#message-templates)

### API ve Entegrasyon

**Q: API'yi nasıl kullanırım?**  
→ [`../examples/api_usage.py`](../examples/api_usage.py)

**Q: JWT token nasıl alınır?**  
→ [`README_FULL.md` - API Authentication](README_FULL.md#api-authentication)

### Analitik ve Raporlama

**Q: Veri export nasıl yapılır?**  
→ [`README_FULL.md` - Export Özelliği](README_FULL.md#data-export)

**Q: Gelişmiş analitik nasıl kullanılır?**  
→ [`PROJECT_SUMMARY.md` - Advanced Analytics](PROJECT_SUMMARY.md#advanced-analytics)

**Q: Araştırma bulguları nasıl oluşturulur?**  
→ [`README_ADMIN.md` - Research Findings](README_ADMIN.md#research-findings)

### Sorun Giderme

**Q: Hata aldım, ne yapmalıyım?**  
→ [`README_FULL.md` - Troubleshooting](README_FULL.md#troubleshooting)

**Q: Gemini API hata veriyor**  
→ [`README_FULL.md` - Gemini Errors](README_FULL.md#gemini-api-errors)

**Q: Database migration hatası**  
→ [`README_FULL.md` - Migration Issues](README_FULL.md#migration-issues)

---

## 📁 Klasör Yapısı

```
docs/
├── INDEX.md                     # 📍 Bu dosya - Dokümantasyon rehberi
├── README_FULL.md               # 📖 Detaylı kurulum ve kullanım kılavuzu
├── README_ADMIN.md              # 👨‍💼 Yönetici paneli kılavuzu
├── README_MAINTENANCE.md        # 🔧 Bakım modu yönetimi
├── README_NAMING.md             # 📝 Dosya isimlendirme standardı
├── PROJECT_SUMMARY.md           # 🏗️ Proje mimarisi ve teknik detaylar
├── CHANGELOG.md                 # 📅 Versiyon geçmişi
└── REORGANIZATION_REPORT.md     # 📊 Dosya düzenleme raporu
```

---

## 🎯 Dokümantasyon Okuma Sırası

### Yeni Kullanıcılar İçin
1. [`../README.md`](../README.md) - Projeye giriş
2. [`README_FULL.md`](README_FULL.md) - Detaylı kurulum
3. [`README_ADMIN.md`](README_ADMIN.md) - Admin işlemleri (eğer admin iseniz)

### Geliştiriciler İçin
1. [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) - Teknik mimari
2. [`README_NAMING.md`](README_NAMING.md) - Kodlama standartları
3. [`CHANGELOG.md`](CHANGELOG.md) - Versiyon geçmişi
4. [`../examples/`](../examples/) - Kod örnekleri

### Sistem Yöneticileri İçin
1. [`README_MAINTENANCE.md`](README_MAINTENANCE.md) - Bakım yönetimi
2. [`README_ADMIN.md`](README_ADMIN.md) - Admin paneli
3. [`README_FULL.md`](README_FULL.md#troubleshooting) - Sorun giderme

---

## 📞 Yardım ve Destek

- **Issues:** GitHub Issues sayfası
- **Email:** llm-research-support@example.com
- **Dokümantasyon:** Bu dosya ve bağlantılı sayfalar

---

**Son Güncelleme:** 2025-11-01  
**Versiyon:** 3.0  
**Düzenleyen:** LLM Research Team
