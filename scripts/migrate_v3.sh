#!/bin/bash
# Database Migration Script - LLM Research v3.0

echo "🔄 LLM Research Platform - Database Migration"
echo "============================================="
echo ""

# .env dosyasını yükle
if [ -f .env ]; then
    echo "✓ .env dosyası bulundu"
    export $(cat .env | xargs)
else
    echo "⚠️  UYARI: .env dosyası bulunamadı!"
fi

# Veritabanı yedekle (SQLite için)
if [ -f "database.db" ]; then
    BACKUP_FILE="database_backup_$(date +%Y%m%d_%H%M%S).db"
    echo "📦 Veritabanı yedekleniyor: $BACKUP_FILE"
    cp database.db "$BACKUP_FILE"
    echo "✓ Yedek oluşturuldu"
fi

echo ""
echo "📝 Migration oluşturuluyor..."
flask db migrate -m "v3.0: Added anonymous users, username field, ResearchFinding model"

echo ""
echo "⬆️  Migration uygulanıyor..."
flask db upgrade

echo ""
echo "✅ Migration tamamlandı!"
echo ""
echo "📊 Mevcut migration durumu:"
flask db current

echo ""
echo "🎉 Başarıyla tamamlandı!"
echo ""
echo "Yeni özellikler:"
echo "  • Anonim kullanıcı desteği (anonymous_id, is_anonymous)"
echo "  • Kullanıcı adı alanı (username)"
echo "  • ResearchFinding modeli (bulgular için)"
echo "  • Geliştirilmiş email alanı (artık opsiyonel)"
