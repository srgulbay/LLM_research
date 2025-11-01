#!/bin/bash
# Güvenli dosya temizleme scripti

BACKUP_DIR=".backup_20251101"

echo "🧹 Proje Temizlik İşlemi Başlıyor..."
echo ""

# 1. Template dosyalarını yedekle ve sil
echo "📁 Template dosyaları temizleniyor..."
FILES=(
    "templates/admin/admin_dashboard_new.html"
    "templates/admin/admin_layout_new.html"
    "templates/admin/research_admin_dashboard_new.html"
    "templates/admin/case_review.html"
    "templates/select_research_new.html"
    "templates/final_report_new.html"
    "templates/case.html"
    "templates/edit_case.html"
    "templates/manage_llms.html"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        rm "$file"
        echo "  ✓ Silindi: $file"
    fi
done

# 2. Backup veritabanı
echo ""
echo "💾 Backup veritabanı temizleniyor..."
if [ -f "database_backup_20251030_125448.db" ]; then
    mv "database_backup_20251030_125448.db" "$BACKUP_DIR/"
    echo "  ✓ Taşındı: database_backup_20251030_125448.db"
fi

# 3. Geçici dosyalar
echo ""
echo "🗑️  Geçici dosyalar temizleniyor..."
if [ -f "cookie.txt" ]; then
    cp "cookie.txt" "$BACKUP_DIR/"
    rm "cookie.txt"
    echo "  ✓ Silindi: cookie.txt"
fi

if [ -f "app.log" ]; then
    cp "app.log" "$BACKUP_DIR/"
    rm "app.log"
    echo "  ✓ Silindi: app.log"
fi

# 4. Kullanılmayan script
echo ""
echo "📜 Kullanılmayan script temizleniyor..."
if [ -f "scripts/add_dark_classes.py" ]; then
    mv "scripts/add_dark_classes.py" "$BACKUP_DIR/"
    echo "  ✓ Taşındı: scripts/add_dark_classes.py"
fi

# 5. Eski data dosyası
echo ""
echo "📊 Eski data dosyası temizleniyor..."
if [ -f "pediatric_cases.json" ]; then
    mv "pediatric_cases.json" "$BACKUP_DIR/"
    echo "  ✓ Taşındı: pediatric_cases.json"
fi

# 6. Test dosyası
echo ""
echo "🧪 Test dosyası temizleniyor..."
if [ -f "generate_full_fake_data.py" ]; then
    mv "generate_full_fake_data.py" "$BACKUP_DIR/"
    echo "  ✓ Taşındı: generate_full_fake_data.py"
fi

echo ""
echo "✅ Temizlik tamamlandı!"
echo "📦 Yedek dosyalar: $BACKUP_DIR/"
echo ""
echo "📊 Özet:"
echo "  - Silinen template: 9 adet"
echo "  - Taşınan dosya: 6 adet"
echo "  - Toplam: 15 dosya"
