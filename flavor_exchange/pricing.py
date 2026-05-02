"""
pricing.py
──────────
The Flavor Exchange'in BORSA MOTORU.

Geometric Brownian Motion (GBM) tabanlı, mean-reversion ve
talep şokları ile zenginleştirilmiş fiyat güncelleme algoritması.

Matematiksel Model:
    P_{t+1} = P_t · exp( μ_total · Δt + σ · √Δt · Z ) · (1 + δ)

    μ_total = μ_demand + μ_revert + μ_stock
        μ_demand = α · D_t              (talep yukarı iter)
        μ_revert = κ · ln(P_base / P_t) (mean reversion — baz fiyata çekiş)
        μ_stock  = β · (1 - stock/stock_0)  (stok azaldıkça yukarı baskı)
    Z       ~ N(0, 1)                   (Gauss şoku — borsa titreşimi)
    δ       ~ U(δ_min, δ_max)           (sipariş anı sıçraması)

Bu fonksiyon hem canlı modda hem simülasyon modunda kullanılır.
"""
import math
import random
from typing import Optional

from models import Product
import config


def update_price(
    product: Product,
    recent_orders: int = 0,
    just_ordered: bool = False,
    dt: float = 1.0,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Bir ürünün yeni fiyatını GBM ile hesaplar.

    Args:
        product:        Fiyatı güncellenecek ürün (current_price okunur)
        recent_orders:  Son talep penceresindeki sipariş sayısı (drift'i etkiler)
        just_ordered:   Az önce sipariş geldi mi? (anlık sıçrama uygular)
        dt:             Zaman adımı (sim'de 1 dakika = 1.0)
        rng:            Tekrar üretilebilir test için random nesnesi

    Returns:
        Yeni fiyat (P_min ile P_max arasında kırpılmış)
    """
    R = rng if rng is not None else random
    P = product.current_price

    # Sıfır fiyatı koruma (log alınamaz)
    if P <= 0:
        P = max(product.p_min, 0.01)

    # ─────────────────────────────────────────────────────
    # 1) Drift bileşenleri (deterministic eğilim)
    # ─────────────────────────────────────────────────────
    mu_demand = config.ALPHA * recent_orders
    mu_revert = config.KAPPA * math.log(product.base_price / P)
    mu_stock  = config.BETA_STOCK * (1.0 - product.stock_ratio)
    drift = mu_demand + mu_revert + mu_stock

    # ─────────────────────────────────────────────────────
    # 2) Stochastic shock (Gauss titreşimi)
    # ─────────────────────────────────────────────────────
    sigma = product.volatility if product.volatility > 0 else config.SIGMA_TICK
    Z = R.gauss(0.0, 1.0)
    shock = sigma * math.sqrt(dt) * Z

    # ─────────────────────────────────────────────────────
    # 3) Log-return → yeni fiyat
    # ─────────────────────────────────────────────────────
    log_return = drift * dt + shock
    P_new = P * math.exp(log_return)

    # ─────────────────────────────────────────────────────
    # 4) Sipariş anı sıçraması (varsa)
    # ─────────────────────────────────────────────────────
    if just_ordered:
        jump = R.uniform(config.ORDER_JUMP_MIN, config.ORDER_JUMP_MAX)
        P_new *= (1.0 + jump)

    # ─────────────────────────────────────────────────────
    # 5) Tabanlar (asla altına/üstüne çıkma)
    # ─────────────────────────────────────────────────────
    P_new = max(product.p_min, min(P_new, product.p_max))

    return round(P_new, 2)


def compute_price_change(old_price: float, new_price: float) -> tuple[float, float]:
    """
    Eski ve yeni fiyat arasındaki mutlak ve yüzdelik değişim.
    GUI'de yeşil/kırmızı ok için kullanılır.
    """
    abs_change = new_price - old_price
    if old_price == 0:
        pct_change = 0.0
    else:
        pct_change = (abs_change / old_price) * 100
    return abs_change, pct_change


def price_direction(old_price: float, new_price: float) -> str:
    """'up', 'down' veya 'flat' döner."""
    if new_price > old_price + 0.005:
        return "up"
    if new_price < old_price - 0.005:
        return "down"
    return "flat"


# ─────────────────────────────────────────────────────────────
# Hızlı test (çalıştır: python pricing.py)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Sahte ürün oluştur, 100 tick sim, fiyat hareketini bas
    test = Product(
        id=1, name="Test", category="Test",
        cost=100, base_price=200, current_price=200,
        stock=100, initial_stock=100,
    )
    print("Tick | Recent | Order | Price | %Δ")
    print("-" * 50)
    last = test.current_price
    for tick in range(20):
        recent = 3 if 5 <= tick <= 12 else 0
        ordered = tick in (5, 8, 10)
        new = update_price(test, recent_orders=recent, just_ordered=ordered)
        delta_pct = (new - last) / last * 100 if last else 0
        flag = "🍽️" if ordered else "  "
        print(f"  {tick:2d} |   {recent}    |  {flag}   | "
              f"{new:6.2f} | {delta_pct:+5.2f}%")
        test.current_price = new
        last = new
