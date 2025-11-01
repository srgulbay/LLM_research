# Admin Giriş Bilgileri

## Yönetici Paneline Erişim

**URL:** http://localhost:8080/admin/login

**Giriş Bilgileri:**
- **Email:** admin@llm.com
- **Şifre:** admin123

## Önemli Notlar

⚠️ **GÜVENLİK UYARISI:** Production ortamında mutlaka bu şifreyi değiştirin!

### Şifre Değiştirme

Python shell ile şifre değiştirmek için:

```bash
python -c "
from app import app, db, User
from werkzeug.security import generate_password_hash

app.app_context().push()

admin = User.query.filter_by(email='admin@llm.com').first()
admin.password_hash = generate_password_hash('YENİ_ŞİFRE_BURAYA')
db.session.commit()

print('✓ Admin şifresi güncellendi')
"
```

## Admin Panel Özellikleri

- ✅ Araştırma yönetimi
- ✅ Vaka yönetimi  
- ✅ LLM model yönetimi
- ✅ Kullanıcı yanıtları görüntüleme
- ✅ İstatistiksel analizler
- ✅ Veri export (CSV, JSON, Excel)
- ✅ Araştırma bulguları yönetimi
- ✅ Bilimsel analitik raporları

## Yeni Admin Kullanıcı Ekleme

```python
from app import app, db, User
from werkzeug.security import generate_password_hash

app.app_context().push()

new_admin = User(
    email='yeni_admin@example.com',
    username='Yeni Admin İsmi',
    is_admin=True,
    password_hash=generate_password_hash('güvenli_şifre')
)

db.session.add(new_admin)
db.session.commit()
```

---

**Oluşturulma Tarihi:** 30 Ekim 2025
**Versiyon:** 3.0
