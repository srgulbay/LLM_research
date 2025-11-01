# 🏥 LLM Research Platform v3.0

Modern, chat-tabanlı tıbbi vaka araştırma platformu.

---

## 🚀 Hızlı Başlangıç

```bash
# Kurulum
pip install -r requirements.txt
python init_db.py
python load_pediatric_research.py

# Çalıştır
python app.py
```

**Erişim:**
- Uygulama: http://localhost:8080
- Admin Panel: http://localhost:8080/admin
- Login: `admin@llm.com` / `admin123`

---

## ✨ Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| 💬 **Chat Arayüzü** | CLI benzeri modern vaka değerlendirme |
| 🕵️ **Anonim Sistem** | Email gerektirmeden katılım |
| 🤖 **Gemini AI** | Otomatik puanlama ve analiz |
| 🎯 **Case Generator** | AI ile vaka soruları oluştur |
| � **Research Generator** | 🆕 Araştırma odaklı vaka setleri + altın standart |
| �📊 **Gelişmiş Analitik** | Plotly, regresyon, korelasyon |
| 🌐 **RESTful API** | JWT auth ile 12 endpoint |
| 🔧 **Bakım Modu** | Admin kontrollü sistem bakımı |
| 📦 **Multi-Export** | CSV, JSON, Excel formatları |
| 📈 **Research Findings** | Akademik format PDF export |

---

## 📚 Dokümantasyon

### 📖 Kullanıcı Rehberleri
- **[Dokümantasyon İndeksi](docs/INDEX.md)** - Tüm dökümanlar için başlangıç noktası
- **[Detaylı Kılavuz](docs/README_FULL.md)** - Kapsamlı kurulum ve kullanım
- **[Admin Kılavuzu](docs/README_ADMIN.md)** - Yönetici paneli kullanımı
- **[Bakım Modu](docs/README_MAINTENANCE.md)** - Sistem bakım yönetimi
- **[Case Generator](docs/CASE_GENERATOR.md)** - AI ile tekli vaka oluşturma
- **[Research Generator](docs/RESEARCH_CASE_GENERATOR.md)** - 🆕 Araştırma seti + altın standart
- **[Admin Case Generator](docs/ADMIN_CASE_GENERATOR.md)** - 🆕 Admin panel vaka oluşturucu

### 🔧 Geliştirici Dokümantasyonu
- **[Proje Mimarisi](docs/PROJECT_SUMMARY.md)** - Teknik detaylar ve mimari
- **[Dosya Standardı](docs/README_NAMING.md)** - İsimlendirme kuralları
- **[Değişiklik Listesi](docs/CHANGELOG.md)** - Versiyon geçmişi
- **[API Örnekleri](examples/api_usage.py)** - REST API kullanım kodu

---

## 🛠️ Teknoloji Stack

**Backend:** Flask 3.1.2, SQLAlchemy 2.0.38, Google Gemini API  
**Frontend:** Tailwind CSS, HTMX, Vanilla JavaScript  
**Analytics:** Pandas, Plotly, scikit-learn  
**Infrastructure:** Redis + RQ, SQLite/PostgreSQL, JWT Auth

---

## 📊 Proje Yapısı

```
├── app.py                    # Ana Flask uygulaması
├── api_routes.py             # RESTful API
├── gemini_service.py         # Gemini AI
├── advanced_analytics.py     # İstatistiksel analiz
├── tasks.py                  # Background jobs
├── templates/                # Jinja2 templates
├── static/                   # Assets
├── tests/                    # PyTest suite
└── docs/                     # 📚 Dokümantasyon
    ├── INDEX.md             # Rehber
    ├── README_FULL.md       # Detaylı kılavuz
    ├── README_ADMIN.md      # Admin
    ├── README_MAINTENANCE.md # Bakım
    ├── PROJECT_SUMMARY.md   # Teknik
    └── CHANGELOG.md         # Değişiklikler
```

---

## 🎯 Hızlı Linkler

**Kullanıcılar:** [Kurulum](docs/README_FULL.md#installation) | [İlk Kullanım](docs/README_FULL.md#quick-start) | [Sorun Giderme](docs/README_FULL.md#troubleshooting)  
**Yöneticiler:** [Admin Paneli](docs/README_ADMIN.md) | [Araştırma Yükleme](docs/README_ADMIN.md#research-upload) | [Bakım Modu](docs/README_MAINTENANCE.md)  
**Geliştiriciler:** [API Docs](docs/README_FULL.md#api) | [Mimari](docs/PROJECT_SUMMARY.md) | [Örnekler](examples/)

---

## 📄 Lisans

MIT License

---

**Versiyon:** 3.0 | **Güncelleme:** 2025-11-01 | **Team:** LLM Research
