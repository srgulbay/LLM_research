# 🔧 Bakım Modu Özelliği

## 📋 Genel Bakış

Bakım modu, sistem güncellemeleri, veri tabanı bakımı veya acil durumlar için platformu geçici olarak kapatmanıza olanak tanır. Bakım modu aktifken:

- ✅ **Yöneticiler**: Sisteme tam erişim sağlar
- ❌ **Normal Kullanıcılar**: Özel bakım modu sayfasını görür
- 🔒 **Güvenlik**: Veriler korunur ve sistem stabil kalır

---

## 🎯 Özellikler

### 1. **Kolay Yönetim**
- Web tabanlı kontrol paneli
- Tek tıkla açma/kapatma
- Özelleştirilebilir bakım mesajı

### 2. **Güvenli Erişim**
- Sadece yöneticiler bakım modunu kontrol edebilir
- Admin panelinden `/admin/maintenance` üzerinden erişim
- Yöneticiler bakım modunda bile sistemi kullanabilir

### 3. **Kullanıcı Dostu**
- Modern ve animasyonlu bakım modu sayfası
- Bilgilendirici mesajlar
- Yönetici giriş linki (acil durum erişimi için)

---

## 🚀 Kullanım

### Web Arayüzü Üzerinden

#### Bakım Modunu Açma:

1. Admin paneline giriş yapın: http://localhost:8080/admin/login
2. Sol menüden **"Bakım Modu"** seçeneğine tıklayın
3. Toggle switch'i **AÇIK** konuma getirin
4. İsteğe bağlı özel mesaj yazın veya hazır şablonlardan birini seçin
5. **"Değişiklikleri Kaydet"** butonuna tıklayın

#### Bakım Modunu Kapatma:

1. Admin panelindeki Bakım Modu sayfasını açın
2. Toggle switch'i **KAPALI** konuma getirin
3. **"Değişiklikleri Kaydet"** butonuna tıklayın

### Komut Satırı Üzerinden

Alternatif olarak, `toggle_maintenance.py` scriptini kullanabilirsiniz:

```bash
# İnteraktif mod
python toggle_maintenance.py

# Menüden seçim yapın:
# 1. Bakım modunu AÇ
# 2. Bakım modunu KAPAT
# 3. Mevcut durumu GÖSTER
```

---

## 💬 Hazır Mesaj Şablonları

Admin panelinde şu hazır mesajlar mevcuttur:

1. 🔧 **"Sistem bakımda. Lütfen daha sonra tekrar deneyin."**
2. ⏰ **"Planlı bakım yapılıyor. Yakında tekrar açılacak."**
3. 🔄 **"Sistem güncellemesi yapılıyor. 1-2 saat içinde hizmet verilecektir."**
4. 🚨 **"Acil bakım çalışması devam ediyor. En kısa sürede geri döneceğiz."**

Veya kendi özel mesajınızı yazabilirsiniz!

---

## 🎨 Bakım Modu Sayfası

Kullanıcılar bakım modunda şu sayfayı görür:

```
┌─────────────────────────────────────────┐
│         🔧 Bakım Modu                   │
│    Sistem Geçici Olarak Devre Dışı     │
│                                         │
│  [Özelleştirilebilir Mesaj Burada]     │
│                                         │
│  ⏱️ Kısa Sürecek  ✓ Güvenli  ⚡ Güncel │
│                                         │
│  📧 support@llm-research.com            │
│  🔒 Yönetici Girişi                     │
└─────────────────────────────────────────┘
```

**Özellikler:**
- Animasyonlu dişli ikonu
- Gradient arkaplan
- Responsive tasarım (mobil uyumlu)
- Dark mode desteği
- Bilgi kartları

---

## 🔐 Güvenlik Notları

### Yönetici Erişimi

Bakım modu **sadece yöneticiler tarafından** kontrol edilebilir. Normal kullanıcılar:
- Bakım modu ayarlarını göremez
- Açma/kapatma yetkisine sahip değildir
- Admin paneline erişemez

### Yönetici Bypass

Yöneticiler bakım modunda bile:
- ✅ Sisteme tam erişim sağlar
- ✅ Tüm admin fonksiyonlarını kullanabilir
- ✅ Bakım modunu kapatabilir
- ✅ Veri yönetimi yapabilir

---

## 🧪 Test Senaryoları

### Senaryo 1: Planlı Bakım

```bash
# 1. Bakım modunu aç
python toggle_maintenance.py
# Seçim: 1
# Mesaj: "Sistem güncellemesi yapılıyor. 18:00'da tekrar açılacak."

# 2. Kullanıcı olarak ana sayfayı ziyaret et
# http://localhost:8080/
# Sonuç: Bakım modu sayfasını görür

# 3. Yönetici olarak giriş yap
# http://localhost:8080/admin/login
# Sonuç: Sisteme normal erişim

# 4. Bakım işlemini tamamla
# http://localhost:8080/admin/maintenance
# Toggle'ı KAPAT

# 5. Kullanıcılar artık erişebilir
```

### Senaryo 2: Acil Bakım

```bash
# Hızlı açma
echo -e "1\nAcil bakım! 30 dakika içinde geri döneceğiz." | python toggle_maintenance.py

# İşlem tamamlandı
echo "2" | python toggle_maintenance.py
```

---

## 📊 Veritabanı

Bakım modu ayarları `system_settings` tablosunda saklanır:

| key                  | value                           | description         |
|----------------------|---------------------------------|---------------------|
| maintenance_mode     | "true" veya "false"             | Bakım modu durumu   |
| maintenance_message  | "Özel mesaj buraya..."          | Bakım modu mesajı   |

---

## 🛠️ Teknik Detaylar

### Backend (Flask)

```python
# Bakım modu kontrolü (her request öncesi)
@app.before_request
def check_maintenance_mode():
    if is_maintenance_mode():
        if not current_user.is_authenticated or not current_user.is_admin:
            return render_template('maintenance.html', ...), 503
```

### Model

```python
class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, ...)
```

### Route

```python
@app.route('/admin/maintenance', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_maintenance():
    # Bakım modu yönetim sayfası
```

---

## 🔗 İlgili Dosyalar

- `app.py` - Bakım modu mantığı ve route'lar
- `templates/maintenance.html` - Kullanıcı bakım modu sayfası
- `templates/admin/maintenance.html` - Admin kontrol paneli
- `toggle_maintenance.py` - CLI yönetim scripti
- `MAINTENANCE.md` - Bu belge

---

## 📞 Destek

Sorularınız için:
- Email: support@llm-research.com
- Admin Paneli: http://localhost:8080/admin/maintenance
- Dokümantasyon: Bu dosya

---

## ✅ Önemli Notlar

1. **Veri Güvenliği**: Bakım modunda veriler korunur
2. **Oturum Devamı**: Aktif kullanıcı oturumları kapanmaz
3. **API Erişimi**: API endpoint'leri de etkilenir
4. **Statik Dosyalar**: CSS/JS gibi statik dosyalar çalışır
5. **Admin Bypass**: Yöneticiler her zaman erişebilir

---

## 🎉 Özet

Bakım modu özelliği ile:
- ✅ Güvenli sistem güncellemeleri yapabilirsiniz
- ✅ Kullanıcılara profesyonel bilgilendirme sağlarsınız
- ✅ Acil durumlarda hızlıca müdahale edebilirsiniz
- ✅ Yönetici erişimini korursunuz

**Kullanım önerisi**: Sistem güncellemeleri, veri tabanı bakımı veya acil müdahaleler öncesinde kullanın!
