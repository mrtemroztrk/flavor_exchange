"""
module_orders.py — 👤 ÜYE 2: Canlı Sipariş & Borsa Ekranı
═══════════════════════════════════════════════════════════════
Bu modül 4 katmanı da kapsar:
  🎨 GUI:    Ürün kartları, sepet, sipariş butonu, ↑↓ renkli fiyatlar
  💾 DB:     orders + order_items INSERT, products UPDATE (stok düş)
  📊 Grafik: Mini sparkline'lar (her ürün için son 30 tick'in çizgisi)
  🧠 Mantık: Fiyat kilitleme (locked_price), sipariş demand sinyali

Bu modül "canlı borsa" hissi verir. Fiyatlar saniyede bir güncellenir,
ekran yeşil/kırmızı yanar. Sipariş verince anlık sıçrama görülür.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import collections

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import config
import pricing
from models import Product


class OrdersModule(ttk.Frame):
    """Canlı sipariş sekmesi."""

    REFRESH_MS = 1000   # Her saniye fiyatları yenile
    SPARKLINE_LEN = 30  # Her üründe son 30 tick

    def __init__(self, parent, current_user_id: int = None):
        super().__init__(parent)
        self.current_user_id = current_user_id

        # Dahili durum
        self.products: dict[int, Product] = {}      # product_id → Product
        self.product_cards: dict[int, dict] = {}    # product_id → widget'lar
        self.last_prices: dict[int, float] = {}     # önceki tick fiyatı (renk için)
        self.cart: list[dict] = []                  # sepet

        # Sparkline geçmişi (her ürün için fiyat penceresi)
        self.sparkline_data: dict[int, collections.deque] = {}

        self._build_ui()
        self._load_products()
        self._tick_loop()   # Saniyede bir fiyatları yenile

    # ─────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────
    def _build_ui(self):
        # Başlık
        header = ttk.Label(
            self, text="📈  Canlı Sipariş — Borsa Ekranı",
            font=config.FONT_TITLE
        )
        header.pack(pady=(10, 5), padx=10, anchor="w")

        ttk.Label(
            self,
            text="Fiyatlar saniyede bir güncellenir. Karta tıklayıp sepete ekleyin, "
                 "sipariş anında fiyat kilitlenir.",
            font=config.FONT_NORMAL
        ).pack(pady=(0, 10), padx=10, anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ── SOL: Ürün kartları (scroll'lu canvas) ──
        cards_wrap = ttk.LabelFrame(body, text=" Menü ")
        cards_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.canvas_widget = tk.Canvas(cards_wrap, highlightthickness=0,
                                       background=config.COLOR_BG)
        scrollbar = ttk.Scrollbar(cards_wrap, orient="vertical",
                                  command=self.canvas_widget.yview)
        self.cards_frame = ttk.Frame(self.canvas_widget)

        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.canvas_widget.configure(
                scrollregion=self.canvas_widget.bbox("all")
            )
        )
        self.canvas_widget.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas_widget.configure(yscrollcommand=scrollbar.set)

        self.canvas_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── SAĞ: Sepet ──
        cart_wrap = ttk.LabelFrame(body, text=" Sepet ")
        cart_wrap.grid(row=0, column=1, sticky="nsew")

        self.cart_listbox = tk.Listbox(cart_wrap, height=15,
                                       font=config.FONT_NORMAL)
        self.cart_listbox.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Sepet alt kısmı
        self.total_label = ttk.Label(
            cart_wrap, text="Toplam: ₺0.00",
            font=config.FONT_SUBTITLE
        )
        self.total_label.pack(pady=4)

        ttk.Label(cart_wrap, text="Masa No:").pack()
        self.table_entry = ttk.Entry(cart_wrap, width=10)
        self.table_entry.insert(0, "1")
        self.table_entry.pack(pady=2)

        btn_frame = ttk.Frame(cart_wrap)
        btn_frame.pack(pady=8, fill="x", padx=8)

        ttk.Button(btn_frame, text="🗑 Temizle",
                   command=self._clear_cart).pack(side="left", padx=2, fill="x", expand=True)
        self.order_btn = ttk.Button(btn_frame, text="✓ Sipariş Ver",
                                    command=self._place_order)
        self.order_btn.pack(side="left", padx=2, fill="x", expand=True)

    # ─────────────────────────────────────────────────────
    # Veri Yükleme
    # ─────────────────────────────────────────────────────
    def _load_products(self):
        """DB'den ürünleri yükle, kartları oluştur."""
        rows = database.execute(
            "SELECT * FROM products WHERE is_active=1 ORDER BY category, name"
        )
        self.products = {r["id"]: Product.from_row(r) for r in rows}

        # Önceden var olan kartları temizle
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.product_cards = {}
        self.sparkline_data = {pid: collections.deque(maxlen=self.SPARKLINE_LEN)
                               for pid in self.products}

        # Kategori başlıklarıyla grupla
        current_category = None
        row_idx = 0
        for product in self.products.values():
            if product.category != current_category:
                # Kategori başlığı
                cat_label = ttk.Label(
                    self.cards_frame,
                    text=f"━━ {product.category} ━━",
                    font=config.FONT_SUBTITLE,
                )
                cat_label.grid(row=row_idx, column=0, columnspan=3,
                               sticky="w", pady=(10, 4), padx=4)
                row_idx += 1
                current_category = product.category

            self._create_card(product, row_idx)
            row_idx += 1

        self.cards_frame.columnconfigure(0, weight=1)

    def _create_card(self, product: Product, row: int):
        """Bir ürün için kart widget'ı oluştur."""
        card = ttk.Frame(self.cards_frame, relief="solid", padding=8)
        card.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        card.columnconfigure(0, weight=2)
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=1)

        # Ürün adı
        name_lbl = ttk.Label(card, text=product.name,
                             font=config.FONT_SUBTITLE)
        name_lbl.grid(row=0, column=0, sticky="w")

        # Fiyat label (renkli)
        price_lbl = tk.Label(
            card, text=config.fmt_money(product.current_price),
            font=("Consolas", 14, "bold"),
            fg=config.COLOR_NEUTRAL,
            background=card.tk.call("ttk::style", "lookup", "TFrame", "-background"),
        )
        price_lbl.grid(row=0, column=1, sticky="e", padx=4)

        # Yön ok'u
        arrow_lbl = tk.Label(card, text="—", font=("Arial", 14, "bold"),
                             fg=config.COLOR_NEUTRAL)
        arrow_lbl.grid(row=0, column=2, sticky="w")

        # Stok bilgisi
        stock_lbl = ttk.Label(
            card, text=f"Stok: {product.stock}", font=config.FONT_NORMAL
        )
        stock_lbl.grid(row=1, column=0, sticky="w")

        # Mini sparkline alanı
        spark_fig = Figure(figsize=(2.5, 0.6), dpi=70)
        spark_fig.patch.set_alpha(0)
        spark_ax = spark_fig.add_subplot(111)
        spark_ax.axis("off")
        spark_ax.margins(0)
        spark_canvas = FigureCanvasTkAgg(spark_fig, master=card)
        spark_canvas.get_tk_widget().grid(row=1, column=1, columnspan=2,
                                          sticky="ew", padx=4)

        # Sepete ekle butonu
        add_btn = ttk.Button(
            card, text="+ Sepete Ekle",
            command=lambda p=product: self._add_to_cart(p)
        )
        add_btn.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        self.product_cards[product.id] = {
            "card": card,
            "price_lbl": price_lbl,
            "arrow_lbl": arrow_lbl,
            "stock_lbl": stock_lbl,
            "spark_fig": spark_fig,
            "spark_ax": spark_ax,
            "spark_canvas": spark_canvas,
        }

        # İlk fiyatı sparkline'a ekle
        self.sparkline_data[product.id].append(product.current_price)

    # ─────────────────────────────────────────────────────
    # Sepet İşlemleri
    # ─────────────────────────────────────────────────────
    def _add_to_cart(self, product: Product):
        # Aynı üründen var mı?
        for item in self.cart:
            if item["product_id"] == product.id:
                item["quantity"] += 1
                self._refresh_cart()
                return
        # Anlık fiyatı kilitle (önemli!)
        self.cart.append({
            "product_id":   product.id,
            "product_name": product.name,
            "quantity":     1,
            "locked_price": product.current_price,
        })
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_listbox.delete(0, "end")
        total = 0.0
        for item in self.cart:
            line_total = item["quantity"] * item["locked_price"]
            total += line_total
            self.cart_listbox.insert(
                "end",
                f"{item['quantity']}x  {item['product_name']:20s}  "
                f"₺{item['locked_price']:6.2f}  =  ₺{line_total:7.2f}"
            )
        self.total_label.config(text=f"Toplam: {config.fmt_money(total)}")

    def _clear_cart(self):
        self.cart = []
        self._refresh_cart()

    def _place_order(self):
        if not self.cart:
            messagebox.showwarning("Sepet boş", "Önce ürün ekleyin.")
            return
        try:
            table_no = int(self.table_entry.get())
        except ValueError:
            messagebox.showerror("Hatalı", "Masa numarası tam sayı olmalı.")
            return

        total = sum(i["quantity"] * i["locked_price"] for i in self.cart)
        try:
            with database.get_connection() as conn:
                # 1) orders'a ekle
                cur = conn.execute(
                    "INSERT INTO orders (waiter_id, table_no, total_amount, status) "
                    "VALUES (?, ?, ?, 'cooking')",
                    (self.current_user_id, table_no, total)
                )
                order_id = cur.lastrowid

                # 2) order_items + stok düşür
                for item in self.cart:
                    conn.execute(
                        "INSERT INTO order_items "
                        "  (order_id, product_id, quantity, locked_price) "
                        "VALUES (?, ?, ?, ?)",
                        (order_id, item["product_id"],
                         item["quantity"], item["locked_price"])
                    )
                    conn.execute(
                        "UPDATE products SET stock = MAX(0, stock - ?) "
                        "WHERE id = ?",
                        (item["quantity"], item["product_id"])
                    )

                # 3) Talep şokunu uygula → fiyatlar sıçrasın
                for item in self.cart:
                    pid = item["product_id"]
                    if pid in self.products:
                        p = self.products[pid]
                        new_p = pricing.update_price(
                            p, recent_orders=item["quantity"], just_ordered=True
                        )
                        conn.execute(
                            "UPDATE products SET current_price=? WHERE id=?",
                            (new_p, pid)
                        )
                        conn.execute(
                            "INSERT INTO price_history (product_id, price) "
                            "VALUES (?, ?)",
                            (pid, new_p)
                        )

        except Exception as e:
            messagebox.showerror("Sipariş başarısız", str(e))
            return

        messagebox.showinfo(
            "Sipariş alındı",
            f"#{order_id} | Masa {table_no} | Toplam: {config.fmt_money(total)}"
        )
        self._clear_cart()
        self._load_products()   # Stoklar değiştiği için yeniden yükle

    # ─────────────────────────────────────────────────────
    # Canlı Tick — saniyede bir
    # ─────────────────────────────────────────────────────
    def _tick_loop(self):
        """Her saniye fiyatları DB'den yeniden oku, kartları güncelle."""
        try:
            self._refresh_prices()
        except Exception as e:
            print(f"[orders tick error] {e}")
        self.after(self.REFRESH_MS, self._tick_loop)

    def _refresh_prices(self):
        """DB'den anlık fiyatları al, kartları güncelle."""
        rows = database.execute(
            "SELECT id, current_price, stock FROM products WHERE is_active=1"
        )
        for r in rows:
            pid = r["id"]
            if pid not in self.product_cards:
                continue
            new_price = r["current_price"]
            old_price = self.last_prices.get(pid, new_price)
            self.last_prices[pid] = new_price

            # Sparkline güncelle
            self.sparkline_data[pid].append(new_price)

            # Yön
            direction = pricing.price_direction(old_price, new_price)
            color = {
                "up":   config.COLOR_UP,
                "down": config.COLOR_DOWN,
                "flat": config.COLOR_NEUTRAL,
            }[direction]
            arrow = {"up": "▲", "down": "▼", "flat": "—"}[direction]

            card = self.product_cards[pid]
            card["price_lbl"].config(
                text=config.fmt_money(new_price), fg=color
            )
            card["arrow_lbl"].config(text=arrow, fg=color)
            card["stock_lbl"].config(text=f"Stok: {r['stock']}")

            # Sparkline'ı yeniden çiz
            data = list(self.sparkline_data[pid])
            if len(data) >= 2:
                ax = card["spark_ax"]
                ax.clear()
                ax.axis("off")
                ax.margins(0)
                line_color = color if direction != "flat" else config.COLOR_ACCENT
                ax.plot(data, color=line_color, linewidth=1.2)
                ax.fill_between(range(len(data)), data,
                                min(data), alpha=0.15, color=line_color)
                card["spark_canvas"].draw_idle()

            # Ürün modeli güncel olsun
            if pid in self.products:
                self.products[pid].current_price = new_price
                self.products[pid].stock = r["stock"]
