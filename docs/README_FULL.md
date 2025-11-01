# LLM Research Platform - Sürüm 3.0

## 🎯 Genel Bakış

LLM Research Platform, tıbbi vaka değerlendirmeleri için kapsamlı bir araştırma ve veri toplama platformudur. Platform, kullanıcı yanıtlarını toplar, Gemini API ile otomatik puanlama yapar ve gelişmiş analitik özellikler sunar.

## ✨ Yeni Özellikler (v3.0)

### 1. 🕵️ Anonim Kullanıcı Sistemi
- Kullanıcılar artık **opsiyonel** olarak kullanıcı adı veya email girebilir
- **Anonim katılım** özelliği ile kimlik bilgisi gerekmeden araştırmaya katılım
- Her anonim kullanıcıya benzersiz ID atanır

### 2. 📊 Gelişmiş Veri Export
- **CSV, JSON, Excel** formatlarında veri indirme
- Tarih aralığı ve meslek filtreleme
- Özet istatistikler içeren Excel sayfaları
- Admin panelinden kolay export

### 3. 📈 İleri Düzey Analitik
- **Korelasyon matrisi** analizi
- **Çoklu doğrusal regresyon** modelleme
- **Dağılım grafikleri** (histogram, box plot, violin plot)
- **İstatistiksel testler** (ANOVA, Pearson korelasyon)
- **Plotly** ile interaktif grafikler

### 4. 📄 Araştırma Bulguları Modülü
- Akademik format halinde bulgular yönetimi
- **Gemini AI** ile otomatik bulgu metni oluşturma
- Tablo, grafik ve metin tipinde bulgular
- **PDF export** özelliği
- Yayınlanan/taslak bulgu ayrımı

### 5. 🤖 Gelişmiş Gemini Entegrasyonu
- **Rate limiting** mekanizması (dakika/gün bazlı)
- **Batch processing** desteği
- **Retry mechanism** ile hata yönetimi
- **Exponential backoff** stratejisi
- Detaylı logging ve error handling

### 6. 🌐 RESTful API
- JWT tabanlı authentication
- CORS desteği
- Kapsamlı endpoint'ler:
  - `/api/v1/auth/login` - Kullanıcı girişi
  - `/api/v1/researches` - Araştırma listesi
  - `/api/v1/research/<id>/stats` - İstatistikler
  - `/api/v1/response` - Yanıt gönderme
  - Ve daha fazlası...

## 🚀 Kurulum

### Gereksinimler
```bash
Python 3.8+
PostgreSQL (production) veya SQLite (development)
Redis (asenkron görevler için)
```

### Adımlar

1. **Depoyu klonlayın**
```bash
git clone <repo-url>
cd LLM_research
```

2. **Sanal ortam oluşturun**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

3. **Bağımlılıkları yükleyin**
```bash
pip install -r requirements.txt
```

4. **Ortam değişkenlerini ayarlayın**
`.env` dosyası oluşturun:
```env
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # veya SQLite
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-jwt-secret
```

5. **Veritabanını başlatın**
```bash
flask db upgrade
```

6. **Uygulamayı çalıştırın**
```bash
python app.py
```

7. **Redis worker'ı başlatın** (ayrı terminal)
```bash
rq worker
```

## 📚 API Dokümantasyonu

### Authentication

**Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",  // Opsiyonel
  "username": "Dr. Ahmet",       // Opsiyonel
  "anonymous": true              // Anonim giriş için
}
```

Response:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "Dr. Ahmet",
    "is_anonymous": false,
    "display_name": "Dr. Ahmet"
  }
}
```

### Araştırmalar

**Araştırma Listesi**
```http
GET /api/v1/researches
```

**Araştırma Detayları**
```http
GET /api/v1/research/<id>
```

**Araştırma İstatistikleri** (Admin)
```http
GET /api/v1/research/<id>/stats
Authorization: Bearer <token>
```

### Yanıtlar

**Yanıt Gönder**
```http
POST /api/v1/response
Authorization: Bearer <token>
Content-Type: application/json

{
  "case_id": 1,
  "answers": {
    "diagnosis": "...",
    "treatment": "...",
    "tests": "..."
  },
  "confidence_score": 85,
  "clinical_rationale": "...",
  "duration_seconds": 120
}
```

**Kullanıcı Yanıtları**
```http
GET /api/v1/user/responses
Authorization: Bearer <token>
```

### Bulgular

**Araştırma Bulguları**
```http
GET /api/v1/research/<id>/findings?published_only=true
```

## 🗂️ Proje Yapısı

```
LLM_research/
├── app.py                      # Ana uygulama
├── api_routes.py               # RESTful API endpoints
├── gemini_service.py           # Gemini API servisi
├── advanced_analytics.py       # İleri analitik fonksiyonları
├── analysis.py                 # Temel analiz fonksiyonları
├── tasks.py                    # Asenkron görevler
├── requirements.txt            # Python bağımlılıkları
├── .env                        # Ortam değişkenleri
├── migrations/                 # Veritabanı migration'ları
├── static/                     # Statik dosyalar
├── templates/                  # HTML şablonları
│   ├── admin/                  # Admin paneli şablonları
│   │   ├── research_findings.html
│   │   └── ...
│   ├── giris.html             # Yeni giriş formu
│   └── ...
└── tests/                      # Test dosyaları
```

## 🔧 Kullanım Örnekleri

### Python API Client Örneği

```python
import requests

BASE_URL = "http://localhost:8080/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "researcher@example.com"
})
token = response.json()["token"]

# Araştırma listesi
headers = {"Authorization": f"Bearer {token}"}
researches = requests.get(f"{BASE_URL}/researches").json()

# Yanıt gönder
response_data = {
    "case_id": 1,
    "answers": {"diagnosis": "Acute appendicitis"},
    "confidence_score": 90
}
result = requests.post(
    f"{BASE_URL}/response",
    headers=headers,
    json=response_data
)
```

### JavaScript/Fetch Örneği

```javascript
// Login
const login = async () => {
  const response = await fetch('http://localhost:8080/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous: true })
  });
  const data = await response.json();
  return data.token;
};

// Araştırma listesi
const getResearches = async (token) => {
  const response = await fetch('http://localhost:8080/api/v1/researches');
  return await response.json();
};

// Yanıt gönder
const submitResponse = async (token, responseData) => {
  const response = await fetch('http://localhost:8080/api/v1/response', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(responseData)
  });
  return await response.json();
};
```

## 📊 Admin Panel Özellikleri

### Veri Export
1. Admin dashboard'a giriş yapın
2. Araştırma seçin
3. "Export" butonuna tıklayın
4. Format seçin (CSV/JSON/Excel)
5. İsteğe bağlı filtreler uygulayın:
   - Tarih aralığı
   - Meslek grubu
   - Deneyim seviyesi

### Araştırma Bulguları Yönetimi
1. Araştırma dashboard'ından "Bulgular" sekmesine gidin
2. **AI ile Oluştur**: Gemini otomatik bulgular oluşturur
3. **Manuel Ekle**: Kendi bulgularınızı ekleyin
4. **PDF Export**: Tüm bulguları PDF olarak indirin

### Gelişmiş Analitik
- Korelasyon matrisleri görüntüleme
- Regresyon analizi sonuçları
- Interaktif Plotly grafikleri
- İstatistiksel test sonuçları

## 🔒 Güvenlik

- JWT tabanlı authentication
- CORS yapılandırması
- SQL injection koruması (SQLAlchemy ORM)
- XSS koruması
- Rate limiting (API istekleri için)
- Secure password hashing (admin kullanıcılar için)

## 🐛 Hata Ayıklama

### Gemini API Hataları
```bash
# .env dosyasını kontrol edin
cat .env | grep GEMINI_API_KEY

# Loglara bakın
tail -f app.log
```

### Veritabanı Hataları
```bash
# Migration durumunu kontrol edin
flask db current

# Migration oluşturun
flask db migrate -m "description"

# Migration uygulayın
flask db upgrade
```

### Redis Bağlantı Hataları
```bash
# Redis'in çalıştığını kontrol edin
redis-cli ping
# PONG dönmeli

# Worker'ı başlatın
rq worker
```

## 📝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

MIT License

## 👥 İletişim

Proje Sahibi: [srgulbay](https://github.com/srgulbay)

## 🙏 Teşekkürler

- Google Gemini AI
- Flask Framework
- Plotly & Matplotlib
- Tüm katkıda bulunanlara

---
**v3.0** - Anonim kullanıcılar, gelişmiş analitik, RESTful API ve daha fazlası!
