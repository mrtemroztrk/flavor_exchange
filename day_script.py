"""
day_script.py
─────────────
Bir restoran gününün dakika dakika senaryosu.
Simülasyon (module_simulation.py) bu dosyayı okuyup hızlandırılmış
şekilde oynatır.

Format:
    EVENTS = [ (saat, tip, ...args), ... ]

Tipler:
    "order"       → ("HH:MM", "order", [(ürün_adı, adet), ...])
    "rush_start"  → ("HH:MM", "rush_start", "etiket")
    "rush_end"    → ("HH:MM", "rush_end",   "etiket")
    "restock"    → ("HH:MM", "restock", ürün_adı, miktar)
    "close"      → ("HH:MM", "close")

İPUCU: Sunum öncesi buradaki olayları kolayca düzenleyebilirsiniz.
        Yeni satır ekleyin, saati değiştirin, ürün adlarını değiştirin —
        simülasyon yeniden başlatınca otomatik yansıyacaktır.
"""

DAY_START = "09:00"
DAY_END   = "23:00"

EVENTS = [
    # ═════════════════════════════════════════════════════
    # SABAH (09:00 – 12:00) — Yavaş açılış, kahve ağırlıklı
    # ═════════════════════════════════════════════════════
    ("09:30", "order", [("Latte", 1)]),
    ("09:45", "order", [("Croissant", 2), ("Latte", 1)]),
    ("10:10", "order", [("Espresso", 1)]),
    ("10:25", "order", [("Cappuccino", 2), ("Croissant", 1)]),
    ("10:50", "order", [("Latte", 1), ("Croissant", 2)]),
    ("11:15", "order", [("Espresso", 2)]),
    ("11:40", "order", [("Cappuccino", 1)]),

    # ═════════════════════════════════════════════════════
    # ÖĞLE KOŞUSU (12:00 – 13:30) — Yoğunluk patlar
    # ═════════════════════════════════════════════════════
    ("12:00", "rush_start", "lunch"),
    ("12:05", "order", [("Caesar Salad", 2), ("Lemonade", 2)]),
    ("12:08", "order", [("Margherita Pizza", 1), ("Coke", 1)]),
    ("12:12", "order", [("Wagyu Steak", 1), ("Red Wine", 1)]),
    ("12:15", "order", [("Caesar Salad", 1), ("Lemonade", 1)]),
    ("12:20", "order", [("Margherita Pizza", 2), ("Coke", 2)]),
    ("12:25", "order", [("Wagyu Steak", 2)]),                  # Wagyu tırmanış
    ("12:30", "order", [("Wagyu Steak", 1), ("Red Wine", 2)]),  # tavana yaklaş
    ("12:35", "order", [("Caesar Salad", 3), ("Coke", 3)]),
    ("12:40", "order", [("Margherita Pizza", 1), ("Lemonade", 2)]),
    ("12:50", "order", [("Wagyu Steak", 1)]),
    ("13:00", "order", [("Caesar Salad", 2)]),
    ("13:15", "order", [("Cheesecake", 2), ("Espresso", 2)]),
    ("13:30", "rush_end", "lunch"),

    # ═════════════════════════════════════════════════════
    # ÖĞLEDEN SONRA (13:30 – 18:00) — Sakin, mean reversion devrede
    # ═════════════════════════════════════════════════════
    ("14:30", "order", [("Espresso", 1)]),
    ("15:00", "order", [("Cheesecake", 1), ("Latte", 1)]),
    ("15:45", "order", [("Cappuccino", 1)]),
    ("16:30", "order", [("Croissant", 1), ("Espresso", 1)]),
    ("17:15", "order", [("Lemonade", 2)]),

    # ═════════════════════════════════════════════════════
    # AKŞAM YEMEĞİ KOŞUSU (19:00 – 21:00)
    # ═════════════════════════════════════════════════════
    ("19:00", "rush_start", "dinner"),
    ("19:10", "order", [("Wagyu Steak", 2), ("Red Wine", 2)]),
    ("19:25", "order", [("Margherita Pizza", 3), ("Coke", 3)]),
    ("19:40", "order", [("Wagyu Steak", 1), ("Caesar Salad", 1)]),
    ("19:55", "restock", "Wagyu Steak", 8),                     # Mutfak takviye!
    ("20:00", "order", [("Wagyu Steak", 2), ("Red Wine", 1)]),
    ("20:15", "order", [("Margherita Pizza", 2), ("Lemonade", 2)]),
    ("20:30", "order", [("Caesar Salad", 2), ("Cheesecake", 2)]),
    ("20:45", "order", [("Wagyu Steak", 1), ("Cheesecake", 4)]),
    ("21:00", "rush_end", "dinner"),

    # ═════════════════════════════════════════════════════
    # GECE (21:00 – 23:00) — Tatlı ve içecek
    # ═════════════════════════════════════════════════════
    ("21:30", "order", [("Cheesecake", 2), ("Espresso", 2)]),
    ("22:00", "order", [("Red Wine", 2)]),
    ("22:30", "order", [("Cheesecake", 1), ("Latte", 1)]),

    ("23:00", "close"),
]


def get_summary() -> dict:
    """Senaryonun özet bilgisi (GUI'de göstermek için)."""
    total_orders = sum(1 for e in EVENTS if e[1] == "order")
    total_items = sum(
        sum(qty for _, qty in e[2])
        for e in EVENTS if e[1] == "order"
    )
    return {
        "start": DAY_START,
        "end": DAY_END,
        "total_events": len(EVENTS),
        "total_orders": total_orders,
        "total_items": total_items,
    }


if __name__ == "__main__":
    s = get_summary()
    print(f"Senaryo: {s['start']} - {s['end']}")
    print(f"  Toplam olay:    {s['total_events']}")
    print(f"  Sipariş sayısı: {s['total_orders']}")
    print(f"  Ürün adedi:     {s['total_items']}")
