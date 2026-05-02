"""
config.py
─────────
Proje genelinde kullanılan tüm sabitler ve ayarlar.
Değiştirilecek parametreler buradan tek noktadan yönetilir.
"""
import os

# ─────────────────────────────────────────────────────────────
# Yol Sabitleri
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(PROJECT_ROOT, "data")
EXPORT_DIR   = os.path.join(DATA_DIR, "exports")
DB_PATH      = os.path.join(DATA_DIR, "flavor_exchange.db")

# ─────────────────────────────────────────────────────────────
# Borsa / Fiyatlandırma Parametreleri (pricing.py kullanır)
# ─────────────────────────────────────────────────────────────
ALPHA       = 0.020   # Talep drift katsayısı
KAPPA       = 0.050   # Mean reversion gücü (baz fiyata çekiş)
SIGMA_TICK  = 0.005   # Tick başına volatilite (~%0.5)
BETA_STOCK  = 0.100   # Stok baskısı katsayısı
ORDER_JUMP_MIN = 0.010   # Sipariş anı min sıçrama (%1)
ORDER_JUMP_MAX = 0.025   # Sipariş anı max sıçrama (%2.5)

DEMAND_WINDOW_SEC = 300  # 5 dakikalık talep penceresi
TICK_INTERVAL_SEC = 1    # Canlı moddaki tick aralığı (saniye)

# Fiyat tabanları için varsayılanlar
DEFAULT_MIN_MARGIN = 0.20   # Fiyat asla maliyet × 1.20'nin altına inmez
DEFAULT_MAX_MARGIN = 1.50   # Fiyat asla maliyet × 2.50'nin üstüne çıkmaz

# ─────────────────────────────────────────────────────────────
# Simülasyon Parametreleri
# ─────────────────────────────────────────────────────────────
SIM_TICK_MINUTES = 1     # Her simülasyon tick'i kaç sim dakikası ilerler
SIM_DEFAULT_SPEED = 60   # Varsayılan hız (60x = 1 sim dak ≈ 1 sn)
SIM_MIN_SPEED = 1
SIM_MAX_SPEED = 500

# ─────────────────────────────────────────────────────────────
# GUI Sabitleri (Renk Paleti)
# ─────────────────────────────────────────────────────────────
COLOR_UP        = "#16a34a"   # Yeşil — fiyat yükselişi
COLOR_DOWN      = "#dc2626"   # Kırmızı — fiyat düşüşü
COLOR_NEUTRAL   = "#64748b"   # Gri — değişim yok
COLOR_BG        = "#f8fafc"   # Açık arka plan
COLOR_CARD      = "#ffffff"   # Kart arka planı
COLOR_PRIMARY   = "#0f172a"   # Koyu metin
COLOR_ACCENT    = "#3b82f6"   # Mavi vurgu
COLOR_BORDER    = "#e2e8f0"   # İnce çerçeve

FONT_FAMILY      = "Segoe UI"   # Mac'te otomatik fallback olur
FONT_TITLE       = (FONT_FAMILY, 16, "bold")
FONT_SUBTITLE    = (FONT_FAMILY, 12, "bold")
FONT_NORMAL      = (FONT_FAMILY, 10)
FONT_MONO        = ("Consolas", 11)

# ─────────────────────────────────────────────────────────────
# Uygulama
# ─────────────────────────────────────────────────────────────
APP_TITLE   = "The Flavor Exchange — Lezzet Borsası"
APP_VERSION = "1.0.0"

CURRENCY_SYMBOL = "₺"


def fmt_money(amount: float) -> str:
    """Tutar biçimlendirici: 123.4 → '₺123.40'"""
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


# Klasörlerin var olduğundan emin ol (modül import edildiğinde)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
