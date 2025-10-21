from app import app, db, seed_database

print("Veritabanı başlatma script'i (init_db.py) çalışıyor...")

# Uygulama bağlamı (application context) içinde veritabanı işlemlerini yap
with app.app_context():
    # Tüm tabloları oluştur
    db.create_all()
    print("Tablolar başarıyla oluşturuldu.")
    
    # Başlangıç verilerini (vakaları) ekle
    seed_database()

print("Veritabanı başlatma tamamlandı.")
