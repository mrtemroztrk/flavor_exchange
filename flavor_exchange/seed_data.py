"""
seed_data.py
────────────
Veritabanını sıfırlar ve test verisi yükler.

Çalıştırma:
    python seed_data.py
"""
import hashlib

import database


# ─────────────────────────────────────────────────────────────
# Demo Kullanıcılar
# ─────────────────────────────────────────────────────────────
USERS = [
    # (username, password, role, full_name)
    ("admin",  "admin123",  "admin",  "Sistem Yöneticisi"),
    ("ahmet",  "garson123", "waiter", "Ahmet Yılmaz"),
    ("ayse",   "garson123", "waiter", "Ayşe Demir"),
]


# ─────────────────────────────────────────────────────────────
# Demo Ürünler (day_script.py'daki isimlerle eşleşmelidir)
# ─────────────────────────────────────────────────────────────
PRODUCTS = [
    # (name, category, cost, base_price, stock, volatility)
    # Sıcak İçecekler
    ("Espresso",         "Sıcak İçecek",   30,    60,    150, 0.004),
    ("Latte",            "Sıcak İçecek",   40,    80,    150, 0.004),
    ("Cappuccino",       "Sıcak İçecek",   40,    80,    150, 0.004),

    # Soğuk İçecekler
    ("Lemonade",         "Soğuk İçecek",   25,    60,    100, 0.005),
    ("Coke",             "Soğuk İçecek",   15,    50,    200, 0.003),
    ("Red Wine",         "Soğuk İçecek",  120,   280,     40, 0.006),

    # Ana Yemekler
    ("Caesar Salad",     "Ana Yemek",      80,   180,     60, 0.005),
    ("Margherita Pizza", "Ana Yemek",     100,   220,     50, 0.005),
    ("Wagyu Steak",      "Ana Yemek",     400,   850,     20, 0.008),  # Yüksek volatilite

    # Tatlılar
    ("Croissant",        "Tatlı",          35,    70,     80, 0.004),
    ("Cheesecake",       "Tatlı",          60,   140,     40, 0.005),
]


def hash_password(password: str) -> str:
    """SHA-256 hash. Düz metin asla saklanmaz."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_users():
    print("→ Kullanıcılar ekleniyor...")
    with database.get_connection() as conn:
        for username, password, role, full_name in USERS:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, full_name) "
                "VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, full_name)
            )
            print(f"   ✓ {username} ({role})")


def seed_products():
    print("→ Ürünler ekleniyor...")
    with database.get_connection() as conn:
        for name, category, cost, base, stock, vol in PRODUCTS:
            conn.execute(
                "INSERT INTO products "
                "  (name, category, cost, base_price, current_price, "
                "   stock, initial_stock, volatility) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, category, cost, base, base, stock, stock, vol)
            )
            print(f"   ✓ {name:20s} ₺{base:7.2f}  stok:{stock}")


def main():
    print("=" * 55)
    print("  THE FLAVOR EXCHANGE — Veritabanı Hazırlanıyor")
    print("=" * 55)
    print()

    print("→ Veritabanı sıfırlanıyor...")
    database.reset_database()
    print("   ✓ Şema kuruldu")
    print()

    seed_users()
    print()
    seed_products()
    print()

    print("=" * 55)
    print("  ✅ Hazır!  Uygulamayı 'python main.py' ile başlatın.")
    print("=" * 55)
    print()
    print("Demo Hesaplar:")
    print("   admin   / admin123    (yönetici)")
    print("   ahmet   / garson123   (garson)")
    print("   ayse    / garson123   (garson)")


if __name__ == "__main__":
    main()
