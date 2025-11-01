"""
Database Migration Script - v3.0 Güncellemeleri
Yeni alanları ve tabloları veritabanına ekler
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Basit bir Flask app oluştur (sadece migration için)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    print("Migration işlemi için komutlar:")
    print("\n1. Migration oluştur:")
    print("   flask db migrate -m 'v3.0 updates: anonymous users, research findings'")
    print("\n2. Migration uygula:")
    print("   flask db upgrade")
    print("\n3. Mevcut durumu kontrol et:")
    print("   flask db current")
    print("\n4. Geçmiş migration'ları gör:")
    print("   flask db history")
