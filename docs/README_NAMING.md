# 📝 Dosya İsimlendirme Standardı

## 🎯 Genel Kurallar

### Python Dosyaları (.py)
- **Format:** `lowercase_with_underscores.py`
- **Örnek:** `advanced_analytics.py`, `api_routes.py`

### Markdown Dosyaları (.md)
- **Format:** `UPPERCASE_WITH_UNDERSCORES.md` (dokümantasyon)
- **Örnek:** `README.md`, `CHANGELOG.md`

### JSON Dosyaları (.json)
- **Format:** `lowercase_with_underscores.json`
- **Örnek:** `pediatric_mcq_research.json`

### Script Dosyaları (.sh)
- **Format:** `lowercase_with_underscores.sh`
- **Örnek:** `cleanup_files.sh`

### Klasör İsimleri
- **Format:** `lowercase` (tek kelime) veya `lowercase_with_underscores`
- **Örnek:** `templates`, `static`, `migrations`

## 📋 Düzeltilecek Dosyalar

### Markdown Dosyaları (Tutarlılık için)
1. ✅ `README.md` - Doğru
2. ✅ `CHANGELOG.md` - Doğru
3. ✅ `PROJECT_SUMMARY.md` - Doğru
4. ❌ `ADMIN_CREDENTIALS.md` → `README_ADMIN.md` (daha açıklayıcı)
5. ❌ `MAINTENANCE.md` → `README_MAINTENANCE.md`
6. ❌ `MAINTENANCE_SUMMARY.md` → (silinebilir, MAINTENANCE.md'ye merge)
7. ❌ `CLEANUP_REPORT.md` → (geçici dosya, silinebilir)

### Python Dosyaları
- ✅ Tüm Python dosyaları zaten standart formatında

### JSON Dosyaları
- ✅ `pediatric_mcq_research.json` - Doğru

### Script Dosyaları
- ✅ `cleanup_files.sh` - Doğru

## 🗂️ Önerilen Yeni Yapı

```
/workspaces/LLM_research/
├── README.md                          # Ana dokümantasyon
├── CHANGELOG.md                       # Versiyon geçmişi
├── PROJECT_SUMMARY.md                 # Proje özeti
├── README_ADMIN.md                    # Admin kılavuzu (eski ADMIN_CREDENTIALS)
├── README_MAINTENANCE.md              # Bakım modu kılavuzu
├── requirements.txt
├── Procfile
├── pytest.ini
│
├── app.py                             # Ana uygulama
├── api_routes.py                      # API routes
├── advanced_analytics.py              # Gelişmiş analitik
├── analysis.py                        # Temel analitik
├── gemini_service.py                  # Gemini servis
├── tasks.py                           # Background tasks
│
├── init_db.py                         # DB başlatma
├── migrate_db.py                      # DB migration
├── calculate_scores.py                # Skorlama
├── load_pediatric_research.py         # Veri yükleme
├── seed_mcq_responses.py              # Test data
├── toggle_maintenance.py              # Bakım modu
├── test_app.py                        # Testler
│
├── pediatric_mcq_research.json        # Demo data
├── cleanup_files.sh                   # Temizlik scripti
│
├── templates/                         # Template dosyaları
├── static/                            # Statik dosyalar
├── migrations/                        # DB migrations
├── scripts/                           # Yardımcı scriptler
├── examples/                          # Örnek kullanımlar
└── tests/                             # Test dosyaları
```

## 🔧 Uygulama Planı

1. Markdown dosyalarını yeniden adlandır
2. Gereksiz dosyaları sil
3. .gitignore güncelle
4. Dokümantasyonu birleştir

