# 🎉 LLM Research Platform v3.0 - Değişiklik Notu

## 📅 Tarih: 30 Ekim 2025

## 🚀 Genel Bakış

Bu sürüm, LLM Research Platform'un en kapsamlı güncellemesidir. Kullanıcı deneyimini iyileştiren, araştırmacılara güçlü analitik araçlar sunan ve geliştiriciler için RESTful API sağlayan birçok yeni özellik içerir.

---

## ✨ Yeni Özellikler

### 1. 🕵️ Anonim Kullanıcı Sistemi

**Ne Değişti:**
- Kullanıcılar artık email veya kullanıcı adı **girmeden** anonim olarak araştırmaya katılabilir
- Email ve kullanıcı adı alanları **opsiyonel** hale getirildi
- Her anonim kullanıcıya benzersiz UUID atanır

**Yeni Veritabanı Alanları:**
- `User.username` (String, nullable)
- `User.anonymous_id` (String, unique, nullable)
- `User.is_anonymous` (Boolean, default=False)
- `User.email` artık nullable

**Kullanım:**
```python
# Anonim kullanıcı
user = User(anonymous_id=str(uuid.uuid4()), is_anonymous=True)

# Email ile kullanıcı
user = User(email="user@example.com", username="Dr. Ahmet")

# Sadece kullanıcı adı ile
user = User(username="Araştırmacı123")
```

**UI Değişiklikleri:**
- `templates/giris.html` yeniden tasarlandı
- "Anonim Olarak Devam Et" butonu eklendi
- Kullanıcı adı ve email alanları opsiyonel

---

### 2. 📊 Gelişmiş Veri Export Sistemi

**Özellikler:**
- **CSV, JSON, Excel** formatlarında export
- Tarih aralığı filtreleme
- Meslek grubu filtreleme
- Excel export'unda özet istatistikler sayfası

**Yeni Endpoint:**
```
GET /admin/research/<id>/export/<format>
  ?start_date=2025-01-01
  &end_date=2025-12-31
  &profession=Hekim
```

**Desteklenen Formatlar:**
- `csv` - UTF-8 BOM ile Türkçe karakter desteği
- `json` - Pretty-printed, force_ascii=False
- `excel` - Çoklu sayfa (Responses + Özet)

**Kod:**
```python
# Excel export ile özet sayfası
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Responses', index=False)
    summary_df.to_excel(writer, sheet_name='Özet', index=False)
```

---

### 3. 📈 İleri Düzey Analitik Modülü

**Yeni Dosya:** `advanced_analytics.py`

**Özellikler:**
- **Korelasyon Matrisi** - Değişkenler arası ilişkiler
- **Çoklu Doğrusal Regresyon** - R² skoru, katsayılar
- **Dağılım Grafikleri** - Histogram, box plot, violin plot
- **İstatistiksel Testler** - ANOVA, Pearson korelasyon
- **Plotly Entegrasyonu** - İnteraktif grafikler

**Fonksiyonlar:**
```python
# Korelasyon matrisi
create_correlation_matrix(df, research_id)

# Regresyon analizi
perform_regression_analysis(df, target_var='user_final_score')

# Dağılım grafikleri
create_distribution_plots(df)

# İstatistiksel testler
perform_statistical_tests(df)

# Tümünü birleştir
create_interactive_dashboard_data(df, research_id)
```

**Yeni Kütüphaneler:**
- `matplotlib` - Statik grafikler
- `seaborn` - İstatistiksel görselleştirme
- `plotly` - İnteraktif grafikler
- `scipy` - İstatistiksel testler
- `scikit-learn` - Regresyon modelleme

---

### 4. 📄 Araştırma Bulguları Modülü

**Yeni Model:** `ResearchFinding`

**Veritabanı Şeması:**
```python
class ResearchFinding(db.Model):
    id = Column(Integer, primary_key=True)
    research_id = Column(Integer, ForeignKey('research.id'))
    title = Column(String(500))
    finding_type = Column(String(50))  # 'text', 'table', 'chart', 'statistical_test'
    content = Column(JSON)
    order_index = Column(Integer)
    is_published = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**Yeni Endpoint'ler:**
```
GET  /admin/research/<id>/findings - Bulguları görüntüle
POST /admin/research/<id>/findings/generate - AI ile oluştur
POST /admin/research/<id>/findings/add - Manuel ekle
POST /admin/research/finding/<id>/delete - Sil
GET  /admin/research/<id>/findings/export-pdf - PDF indir
```

**AI Entegrasyonu:**
- Gemini API ile otomatik bulgu metni oluşturma
- Akademik dilde, bilimsel format
- Araştırma istatistiklerini analiz eder

**PDF Export:**
- ReportLab kullanarak PDF oluşturma
- Başlık, bulgular ve formatlanmış metin
- Akademik makale formatı

---

### 5. 🤖 Gelişmiş Gemini API Servisi

**Yeni Dosya:** `gemini_service.py`

**Özellikler:**
- **Rate Limiting** - Dakikalık ve günlük limit kontrolü
- **Batch Processing** - Toplu işlem desteği
- **Retry Mechanism** - Otomatik yeniden deneme
- **Exponential Backoff** - Akıllı bekleme stratejisi
- **Detaylı Logging** - Her işlem için log

**Kullanım:**
```python
from gemini_service import GeminiService, get_gemini_service

# Servis oluştur
service = GeminiService()

# Tek içerik üret
result = service.generate_content("Prompt")

# Batch işlem
results = service.batch_generate(["Prompt1", "Prompt2"])

# Yanıt puanla
score_result = service.score_answer(user_answer, gold_answer, category)

# Araştırma özeti oluştur
summary = service.generate_research_summary(research_data)
```

**Rate Limiter:**
```python
class RateLimiter:
    max_calls_per_minute = 60
    max_calls_per_day = 1500
    
    def wait_if_needed(self):
        # Gerekirse bekler
```

---

### 6. 🌐 RESTful API

**Yeni Dosya:** `api_routes.py`

**Güvenlik:**
- JWT Authentication
- Token bazlı yetkilendirme
- CORS desteği

**Endpoint'ler:**

**Authentication:**
```
POST /api/v1/auth/login
```

**Araştırmalar:**
```
GET /api/v1/researches
GET /api/v1/research/<id>
GET /api/v1/research/<id>/stats (Admin)
```

**Yanıtlar:**
```
POST /api/v1/response
GET  /api/v1/user/responses
```

**Bulgular:**
```
GET /api/v1/research/<id>/findings
```

**Sağlık Kontrolü:**
```
GET /api/v1/health
```

**Örnek Kullanım:**
```python
# Login
response = requests.post('http://localhost:8080/api/v1/auth/login', 
                        json={'anonymous': True})
token = response.json()['token']

# Yanıt gönder
headers = {'Authorization': f'Bearer {token}'}
requests.post('http://localhost:8080/api/v1/response',
             headers=headers,
             json={'case_id': 1, 'answers': {...}})
```

---

## 🔧 Teknik Geliştirmeler

### Yeni Bağımlılıklar

```txt
flask-cors==5.0.0
PyJWT==2.10.1
matplotlib==3.10.1
seaborn==0.13.2
plotly==5.26.1
scikit-learn==1.6.1
reportlab==4.2.5
openpyxl==3.1.5
xlsxwriter==3.2.0
```

### Veritabanı Değişiklikleri

**User Tablosu:**
- ✅ `username` eklendi (nullable)
- ✅ `anonymous_id` eklendi (unique, nullable)
- ✅ `is_anonymous` eklendi (Boolean)
- ✅ `email` nullable yapıldı
- ✅ `get_display_name()` metodu eklendi

**Yeni Tablo:**
- ✅ `ResearchFinding` modeli

### Dosya Yapısı

```
LLM_research/
├── advanced_analytics.py     [YENİ] İleri analitik
├── gemini_service.py         [YENİ] Gemini API servisi
├── api_routes.py             [YENİ] RESTful API
├── migrate_db.py             [YENİ] Migration yardımcısı
├── examples/
│   └── api_usage.py          [YENİ] API kullanım örnekleri
├── scripts/
│   └── migrate_v3.sh         [YENİ] Migration scripti
├── templates/
│   ├── giris.html            [GÜNCELLENDI] Anonim giriş
│   └── admin/
│       └── research_findings.html [YENİ] Bulgular sayfası
└── README.md                 [GÜNCELLENDI] Kapsamlı dokümantasyon
```

---

## 📊 İstatistikler

- **Eklenen Dosyalar:** 7
- **Güncellenen Dosyalar:** 5
- **Yeni Endpoint'ler:** 12
- **Yeni Veritabanı Alanları:** 4
- **Yeni Model:** 1 (ResearchFinding)
- **Yeni Kütüphaneler:** 9
- **Toplam Kod Satırı:** ~2000+

---

## 🚀 Yükseltme Talimatları

### 1. Bağımlılıkları Güncelleyin

```bash
pip install -r requirements.txt
```

### 2. Veritabanını Migrate Edin

```bash
# Otomatik script ile
bash scripts/migrate_v3.sh

# VEYA manuel olarak
flask db migrate -m "v3.0 updates"
flask db upgrade
```

### 3. .env Dosyasını Güncelleyin

```env
# Mevcut ayarlar
SECRET_KEY=...
GEMINI_API_KEY=...
DATABASE_URL=...
REDIS_URL=...

# Yeni ekleyin
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### 4. Uygulamayı Yeniden Başlatın

```bash
python app.py
```

---

## ⚠️ Breaking Changes

### Veritabanı Şeması
- `User.email` artık nullable (mevcut data için migration gerekli)
- Yeni `ResearchFinding` tablosu eklendi

### API Değişiklikleri
- Giriş endpoint'i yeni parametreler kabul ediyor
- `anonymous`, `username` parametreleri eklendi

---

## 🐛 Bilinen Sorunlar

Şu an için bilinen sorun yok.

---

## 📝 Gelecek Sürümler İçin Planlar

- [ ] WebSocket entegrasyonu (gerçek zamanlı bildirimler)
- [ ] Email bildirimleri
- [ ] Gelişmiş dashboard widget'ları
- [ ] Çoklu dil desteği
- [ ] Export'a PowerPoint desteği
- [ ] GraphQL API

---

## 🙏 Katkıda Bulunanlar

- **Geliştirici:** LLM Research Team
- **AI Desteği:** GitHub Copilot
- **Test:** Research Team

---

## 📞 Destek

Sorunlarınız için:
- GitHub Issues açın
- Dokümantasyona bakın: `README.md`
- API örneklerine bakın: `examples/api_usage.py`

---

**Keyifli Kullanımlar! 🎉**
