#!/usr/bin/env python
"""
Bakım Modu Demo Script
Bakım modunu açıp kapatmayı gösterir
"""

from app import app, db, SystemSettings
import datetime

def toggle_maintenance_mode(enable=True, message=None):
    """Bakım modunu aç/kapat"""
    with app.app_context():
        # Bakım modu ayarı
        mode_setting = SystemSettings.query.filter_by(key='maintenance_mode').first()
        if mode_setting:
            mode_setting.value = 'true' if enable else 'false'
            mode_setting.updated_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            mode_setting = SystemSettings(
                key='maintenance_mode',
                value='true' if enable else 'false',
                description='Bakım modu durumu'
            )
            db.session.add(mode_setting)
        
        # Bakım modu mesajı
        if message:
            message_setting = SystemSettings.query.filter_by(key='maintenance_message').first()
            if message_setting:
                message_setting.value = message
                message_setting.updated_at = datetime.datetime.now(datetime.timezone.utc)
            else:
                message_setting = SystemSettings(
                    key='maintenance_message',
                    value=message,
                    description='Bakım modu mesajı'
                )
                db.session.add(message_setting)
        
        db.session.commit()
        
        status = "AÇILDI ✓" if enable else "KAPATILDI ✓"
        print(f"\n{'='*60}")
        print(f"🔧 Bakım Modu {status}")
        print(f"{'='*60}")
        
        if enable:
            print("\n📋 Durum:")
            print("   • Normal kullanıcılar: Erişim ENGELLENDİ")
            print("   • Yöneticiler: Tam erişim var")
            if message:
                print(f"\n💬 Mesaj:")
                print(f"   {message}")
        else:
            print("\n📋 Durum:")
            print("   • Tüm kullanıcılar: Normal erişim")
            print("   • Sistem: Tam operasyonel")
        
        print(f"\n🔗 Test URL:")
        print(f"   Ana Sayfa: http://localhost:8080/")
        print(f"   Admin Panel: http://localhost:8080/admin/maintenance")
        print(f"{'='*60}\n")

if __name__ == '__main__':
    import sys
    
    print("\n🎮 Bakım Modu Yönetimi")
    print("="*60)
    print("1. Bakım modunu AÇ")
    print("2. Bakım modunu KAPAT")
    print("3. Mevcut durumu GÖSTER")
    print("="*60)
    
    choice = input("\nSeçiminiz (1-3): ").strip()
    
    if choice == '1':
        message = input("\n💬 Bakım modu mesajı (boş bırakabilirsiniz): ").strip()
        if not message:
            message = "Sistem bakımda. Lütfen daha sonra tekrar deneyin."
        toggle_maintenance_mode(True, message)
    
    elif choice == '2':
        toggle_maintenance_mode(False)
    
    elif choice == '3':
        with app.app_context():
            mode_setting = SystemSettings.query.filter_by(key='maintenance_mode').first()
            message_setting = SystemSettings.query.filter_by(key='maintenance_message').first()
            
            print(f"\n{'='*60}")
            print("📊 Mevcut Bakım Modu Durumu")
            print(f"{'='*60}")
            
            if mode_setting:
                is_active = mode_setting.value == 'true'
                status = "🔴 AÇIK" if is_active else "🟢 KAPALI"
                print(f"\n   Durum: {status}")
                print(f"   Güncelleme: {mode_setting.updated_at}")
                
                if message_setting and is_active:
                    print(f"\n   Mesaj: {message_setting.value}")
            else:
                print("\n   ℹ️  Bakım modu ayarı bulunamadı (varsayılan: KAPALI)")
            
            print(f"{'='*60}\n")
    
    else:
        print("\n❌ Geçersiz seçim!")
        sys.exit(1)
