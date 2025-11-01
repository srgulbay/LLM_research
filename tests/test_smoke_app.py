import pytest
from flask import Flask
from app import app, db


def test_app_importable():
    """Uygulama içe aktarılabiliyor mu?"""
    assert isinstance(app, Flask)


def test_db_tables_create(tmp_path, monkeypatch):
    """In-memory DB ile tablolar oluşturulabiliyor mu?"""
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key"
    })
    with app.app_context():
        db.create_all()
        # basitçe model sınıflarının tablolarının yaratıldığını kontrol edelim
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        assert len(tables) > 0
        db.drop_all()
