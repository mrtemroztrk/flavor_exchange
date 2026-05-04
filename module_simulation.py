"""
module_simulation.py — 👤 ÜYE 3: ⭐ GÜN SİMÜLASYONU
═══════════════════════════════════════════════════════════════
SUNUMUN YILDIZ ÖZELLİĞİ.

Bu modül 4 katmanı da kapsar:
  🎨 GUI:    Hız slider'ı, Başlat/Duraklat/Sıfırla, sim saati, log
  💾 DB:     Simülasyon başında ürünleri okur, geçmişi yazar (is_simulated=1)
  📊 Grafik: ⭐ CANLI ANIMASYONLU çoklu çizgi grafik (matplotlib + Tkinter)
  🧠 Mantık: day_script.py'yi parse eder, threading ile zaman hızlandırır,
             pricing.update_price'i sürekli çağırır

Sunumda hocaya: "Buraya bakın, 09:00'dan 23:00'a kadar bir gün
geçecek. Hızlandırılmış olarak bütün fiyat hareketlerini canlı izleyeceksiniz.
Bu bir Geometric Brownian Motion simülasyonu — finansta standart model."
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import threading
import time
import collections
import copy

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import config
import pricing
import day_script
from models import Product


class SimulationModule(ttk.Frame):
    """Hızlandırılmış gün simülasyonu sekmesi."""

    DEMAND_DECAY_TICKS = 5    # Recent_orders sayacı kaç tickte bir azalır

    def __init__(self, parent):
        super().__init__(parent)

        # Simülasyon durumu
        self.products: dict[str, Product] = {}   # name → Product (kopya, DB'yi etkilemez)
        self.sim_time: datetime = self._parse_time(day_script.DAY_START)
        self.end_time: datetime = self._parse_time(day_script.DAY_END)
        self.event_idx: int = 0
        self.recent_orders: dict[str, int] = {}  # ürün → son talep sinyali
        self.history: dict[str, list] = {}       # ürün → [(time, price), ...]

        self.running: bool = False
        self.paused: bool = False
        self.thread: threading.Thread | None = None

        self.tick_count: int = 0

        self._build_ui()
        self._load_products()

    # ─────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────
    def _build_ui(self):
        # Başlık
        ttk.Label(
            self, text="⏱️  Gün Simülasyonu — Hızlandırılmış Borsa Replay",
            font=config.FONT_TITLE
        ).pack(pady=(10, 5), padx=10, anchor="w")

        ttk.Label(
            self,
            text="day_script.py'deki olayları hızlandırılmış oynatır. "
                 "GBM random walk + mean reversion + talep şokları.",
            font=config.FONT_NORMAL
        ).pack(pady=(0, 10), padx=10, anchor="w")

        # ── Kontrol paneli ──
        control = ttk.LabelFrame(self, text=" Kontroller ")
        control.pack(fill="x", padx=10, pady=5)

        # Hız slider
        ttk.Label(control, text="Hız:").grid(row=0, column=0, padx=8, pady=8)
        self.speed_var = tk.IntVar(value=config.SIM_DEFAULT_SPEED)
        speed_scale = ttk.Scale(
            control, from_=config.SIM_MIN_SPEED, to=config.SIM_MAX_SPEED,
            variable=self.speed_var, orient="horizontal", length=200,
            command=self._on_speed_change,
        )
        speed_scale.grid(row=0, column=1, padx=4, pady=8)
        self.speed_lbl = ttk.Label(
            control, text=f"{config.SIM_DEFAULT_SPEED}x", width=6,
            font=config.FONT_SUBTITLE
        )
        self.speed_lbl.grid(row=0, column=2, padx=4, pady=8)

        # Sim saati
        ttk.Label(control, text="Sim Saati:").grid(row=0, column=3, padx=(20, 4), pady=8)
        self.clock_lbl = ttk.Label(
            control, text=day_script.DAY_START,
            font=("Consolas", 16, "bold"),
            foreground=config.COLOR_ACCENT,
        )
        self.clock_lbl.grid(row=0, column=4, padx=4, pady=8)

        # Butonlar
        self.start_btn = ttk.Button(control, text="▶ Başlat",
                                    command=self.start_simulation)
        self.start_btn.grid(row=0, column=5, padx=4, pady=8)

        self.pause_btn = ttk.Button(control, text="⏸ Duraklat",
                                    command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=0, column=6, padx=4, pady=8)

        self.reset_btn = ttk.Button(control, text="⏹ Sıfırla",
                                    command=self.reset_simulation)
        self.reset_btn.grid(row=0, column=7, padx=4, pady=8)

        # ── Ana grafik + log paneli ──
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Grafik
        chart_wrap = ttk.LabelFrame(body, text=" Canlı Fiyat Hareketleri ")
        chart_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.fig = Figure(figsize=(10, 5), dpi=90)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Saat")
        self.ax.set_ylabel(f"Fiyat ({config.CURRENCY_SYMBOL})")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title("Tüm Ürünlerin Anlık Fiyat Hareketi",
                          fontsize=11, fontweight="bold")

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_wrap)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

        # Çizgi referansları (her ürün için)
        self.lines: dict[str, any] = {}

        # Log paneli
        log_wrap = ttk.LabelFrame(body, text=" Olay Akışı ")
        log_wrap.grid(row=0, column=1, sticky="nsew")

        self.log_text = tk.Text(
            log_wrap, height=20, width=30,
            font=("Consolas", 9),
            background="#0f172a", foreground="#e2e8f0",
            wrap="word",
        )
        log_scroll = ttk.Scrollbar(log_wrap, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        log_scroll.pack(side="right", fill="y", pady=4)

        # Renk etiketleri (log için)
        self.log_text.tag_config("event",  foreground="#fbbf24")
        self.log_text.tag_config("order",  foreground="#34d399")
        self.log_text.tag_config("rush",   foreground="#f87171")
        self.log_text.tag_config("system", foreground="#94a3b8")

    # ─────────────────────────────────────────────────────
    # Veri Yükleme
    # ─────────────────────────────────────────────────────
    def _load_products(self):
        """DB'den ürünleri oku, simülasyon kopyalarını oluştur."""
        rows = database.execute(
            "SELECT * FROM products WHERE is_active=1 ORDER BY name"
        )
        self.products = {}
        for r in rows:
            p = Product.from_row(r)
            # Önemli: derin kopya, simülasyon DB'yi değiştirmesin
            self.products[p.name] = copy.copy(p)
            # Fiyat geçmişi: baz fiyatla başla
            self.history[p.name] = [(self.sim_time, p.current_price)]

        self._setup_chart()

    def _setup_chart(self):
        """Grafik başlangıç durumu."""
        self.ax.clear()
        self.ax.set_xlabel("Saat")
        self.ax.set_ylabel(f"Fiyat ({config.CURRENCY_SYMBOL})")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title("Tüm Ürünlerin Anlık Fiyat Hareketi",
                          fontsize=11, fontweight="bold")

        # Her ürün için boş bir çizgi başlat
        self.lines = {}
        # Renk paleti
        cmap = ["#3b82f6", "#16a34a", "#dc2626", "#f59e0b", "#8b5cf6",
                "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6", "#a855f7"]
        for i, name in enumerate(self.products):
            color = cmap[i % len(cmap)]
            (line,) = self.ax.plot(
                [], [], label=name, color=color, linewidth=1.4
            )
            self.lines[name] = line

        self.ax.legend(loc="upper left", fontsize=7, ncol=2,
                       framealpha=0.9)
        self.canvas.draw_idle()

    # ─────────────────────────────────────────────────────
    # Kontroller
    # ─────────────────────────────────────────────────────
    def _on_speed_change(self, value):
        speed = int(float(value))
        self.speed_lbl.config(text=f"{speed}x")

    def start_simulation(self):
        if self.running:
            return
        self._log("▶ Simülasyon başlatıldı", "system")
        self.running = True
        self.paused = False
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.reset_btn.config(state="normal")

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="▶ Devam")
            self._log("⏸ Duraklatıldı", "system")
        else:
            self.pause_btn.config(text="⏸ Duraklat")
            self._log("▶ Devam ediliyor", "system")

    def reset_simulation(self):
        self.running = False
        self.paused = False
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.thread = None

        # Durumu sıfırla
        self.sim_time = self._parse_time(day_script.DAY_START)
        self.event_idx = 0
        self.recent_orders = {}
        self.tick_count = 0

        self._load_products()
        self.clock_lbl.config(text=day_script.DAY_START)
        self.log_text.delete(1.0, "end")
        self._log("⏹ Sıfırlandı", "system")

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="⏸ Duraklat")

    # ─────────────────────────────────────────────────────
    # Simülasyon Döngüsü (arka plan thread)
    # ─────────────────────────────────────────────────────
    def _loop(self):
        """Bu metod arka plan thread'de çalışır. GUI'ye after() ile mesaj atar."""
        TICK_MIN = config.SIM_TICK_MINUTES   # 1 sim dakikası

        while self.running and self.sim_time < self.end_time:
            if self.paused:
                time.sleep(0.1)
                continue

            # 1) Bu zamana kadar olan event'leri işle
            self._process_events_until(self.sim_time)

            # 2) Tüm ürünlerin fiyatını GBM ile güncelle
            for name, product in self.products.items():
                recent = self.recent_orders.get(name, 0)
                new_price = pricing.update_price(
                    product, recent_orders=recent,
                    just_ordered=False, dt=1.0,
                )
                product.current_price = new_price
                self.history[name].append((self.sim_time, new_price))

            # 3) Recent orders sayacını yavaşça azalt
            if self.tick_count % self.DEMAND_DECAY_TICKS == 0:
                for name in list(self.recent_orders.keys()):
                    self.recent_orders[name] = max(0, self.recent_orders[name] - 1)
                    if self.recent_orders[name] == 0:
                        del self.recent_orders[name]

            # 4) GUI'yi güncelle (ana thread'de!)
            self.after(0, self._update_ui)

            # 5) DB'ye yaz (her 10 tick'te bir, performans için)
            if self.tick_count % 10 == 0:
                self._save_history_to_db()

            # 6) Hızlandırılmış bekleme
            speed = max(1, self.speed_var.get())
            real_wait = (60.0 * TICK_MIN) / speed
            time.sleep(real_wait)

            # 7) Sim zamanını ilerlet
            self.sim_time += timedelta(minutes=TICK_MIN)
            self.tick_count += 1

        # Bitiş
        self.after(0, self._on_simulation_end)

    def _process_events_until(self, current_time: datetime):
        """current_time'a kadar tüm event'leri işle."""
        while self.event_idx < len(day_script.EVENTS):
            event = day_script.EVENTS[self.event_idx]
            event_time = self._parse_time(event[0])
            if event_time > current_time:
                break
            self._handle_event(event)
            self.event_idx += 1

    def _handle_event(self, event):
        kind = event[1]
        time_str = event[0]

        if kind == "order":
            items = event[2]
            total_amount = 0.0
            order_items_data = []
            
            for prod_name, qty in items:
                if prod_name not in self.products:
                    continue
                p = self.products[prod_name]
                # Stoktan düş
                p.stock = max(0, p.stock - qty)
                # Sipariş anı sıçraması
                p.current_price = pricing.update_price(
                    p, recent_orders=self.recent_orders.get(prod_name, 0),
                    just_ordered=True, dt=0.5
                )
                # Demand sinyalini artır
                self.recent_orders[prod_name] = (
                    self.recent_orders.get(prod_name, 0) + qty
                )
                subtotal = qty * p.current_price
                total_amount += subtotal
                order_items_data.append((prod_name, p.id, qty, p.current_price))
                self._log(f"[{time_str}] 🍽️ {qty}x {prod_name}  "
                          f"→ ₺{p.current_price:.2f}", "order")
            
            # Siparişi DB'ye yaz (is_simulated=1)
            if order_items_data:
                try:
                    with database.get_connection() as conn:
                        cur = conn.execute(
                            "INSERT INTO orders (waiter_id, table_no, status, "
                            "total_amount, created_at, is_simulated) "
                            "VALUES (?, ?, ?, ?, ?, 1)",
                            (None, None, "served", total_amount, 
                             self.sim_time.isoformat())
                        )
                        order_id = cur.lastrowid
                        for prod_name, prod_id, qty, price in order_items_data:
                            conn.execute(
                                "INSERT INTO order_items "
                                "(order_id, product_id, quantity, locked_price) "
                                "VALUES (?, ?, ?, ?)",
                                (order_id, prod_id, qty, price)
                            )
                except Exception as e:
                    print(f"[sim order DB write error] {e}")

        elif kind == "rush_start":
            self._log(f"[{time_str}] 🔥 {event[2].upper()} RUSH BAŞLADI", "rush")

        elif kind == "rush_end":
            self._log(f"[{time_str}] ✓ {event[2]} rush bitti", "event")

        elif kind == "restock":
            prod_name, amount = event[2], event[3]
            if prod_name in self.products:
                self.products[prod_name].stock += amount
                self._log(f"[{time_str}] 📦 {prod_name} +{amount} stok", "event")

        elif kind == "close":
            self._log(f"[{time_str}] 🌙 Kapanış", "rush")

    # ─────────────────────────────────────────────────────
    # GUI Güncellemeleri (ana thread)
    # ─────────────────────────────────────────────────────
    def _update_ui(self):
        """Ana thread'den çağrılır (after()), grafik + saati günceller."""
        # Saat
        self.clock_lbl.config(text=self.sim_time.strftime("%H:%M"))

        # Grafik
        for name, line in self.lines.items():
            data = self.history.get(name, [])
            if len(data) < 2:
                continue
            xs = [t for t, _ in data]
            ys = [p for _, p in data]
            line.set_data(xs, ys)

        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _on_simulation_end(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="⏸ Duraklat")
        self._log("✅ Simülasyon tamamlandı", "system")

    # ─────────────────────────────────────────────────────
    # DB Yazma
    # ─────────────────────────────────────────────────────
    def _save_history_to_db(self):
        """Son tick'leri price_history'ye yaz (is_simulated=1)."""
        try:
            with database.get_connection() as conn:
                # Sadece son tick'i yazıyoruz (her 10 tickte bir)
                for name, p in self.products.items():
                    # product_id'yi bul
                    row = conn.execute(
                        "SELECT id FROM products WHERE name=?", (name,)
                    ).fetchone()
                    if row:
                        conn.execute(
                            "INSERT INTO price_history "
                            "  (product_id, price, timestamp, is_simulated) "
                            "VALUES (?, ?, ?, 1)",
                            (row["id"], p.current_price,
                             self.sim_time.isoformat())
                        )
        except Exception as e:
            print(f"[sim DB write error] {e}")

    # ─────────────────────────────────────────────────────
    # Yardımcılar
    # ─────────────────────────────────────────────────────
    @staticmethod
    def _parse_time(hhmm: str) -> datetime:
        """'HH:MM' → datetime (sabit gün: 2024-01-01)."""
        h, m = map(int, hhmm.split(":"))
        return datetime(2024, 1, 1, h, m)

    def _log(self, message: str, tag: str = "event"):
        """Log paneline satır ekle (thread-safe)."""
        def _do():
            self.log_text.insert("end", message + "\n", tag)
            self.log_text.see("end")
        self.after(0, _do)
