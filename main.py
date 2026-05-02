"""
main.py
───────
Uygulamanın giriş noktası.
Login penceresi açar, başarılı girişten sonra 4 sekmeli ana pencereyi gösterir.

Çalıştırma:
    python main.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import threading
import time
import os

import database
import config
import pricing
from models import UserRole

# Modüller
from module_menu       import MenuModule
from module_orders     import OrdersModule
from module_simulation import SimulationModule
from module_reports    import ReportsModule


# ─────────────────────────────────────────────────────────────
# Login Penceresi
# ─────────────────────────────────────────────────────────────
class LoginWindow:
    """Modern, basit giriş penceresi."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(config.APP_TITLE + " — Giriş")
        self.root.geometry("420x340")
        self.root.configure(background=config.COLOR_BG)
        self.root.resizable(False, False)

        self.user_id: int | None = None
        self.user_role: str | None = None
        self.username: str | None = None

        self._build_ui()
        # Enter tuşu = giriş
        self.root.bind("<Return>", lambda e: self.do_login())

    def _build_ui(self):
        frame = tk.Frame(self.root, background=config.COLOR_BG, padx=40, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame, text="🍽️", font=("Arial", 44),
            background=config.COLOR_BG, foreground=config.COLOR_PRIMARY
        ).pack()

        tk.Label(
            frame, text=config.APP_TITLE,
            font=(config.FONT_FAMILY, 14, "bold"),
            background=config.COLOR_BG, foreground=config.COLOR_PRIMARY
        ).pack(pady=(0, 20))

        # Kullanıcı adı
        tk.Label(frame, text="Kullanıcı Adı",
                 background=config.COLOR_BG, anchor="w"
                 ).pack(fill="x")
        self.username_entry = ttk.Entry(frame)
        self.username_entry.pack(fill="x", pady=(2, 12))
        self.username_entry.focus_set()

        # Şifre
        tk.Label(frame, text="Şifre",
                 background=config.COLOR_BG, anchor="w"
                 ).pack(fill="x")
        self.password_entry = ttk.Entry(frame, show="●")
        self.password_entry.pack(fill="x", pady=(2, 16))

        # Buton
        ttk.Button(frame, text="Giriş Yap",
                   command=self.do_login).pack(fill="x")

        # Demo notu
        tk.Label(
            frame,
            text="Demo:  admin/admin123  •  ahmet/garson123",
            background=config.COLOR_BG,
            foreground=config.COLOR_NEUTRAL,
            font=(config.FONT_FAMILY, 9)
        ).pack(pady=(14, 0))

    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Eksik", "Kullanıcı adı ve şifre girin.")
            return

        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        try:
            rows = database.execute(
                "SELECT id, username, role, password_hash FROM users WHERE username=?",
                (username,)
            )
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası",
                                 f"{e}\n\nseed_data.py çalıştırdınız mı?")
            return

        if not rows:
            messagebox.showerror("Hata", "Kullanıcı bulunamadı.")
            return

        user = rows[0]
        if user["password_hash"] != password_hash:
            messagebox.showerror("Hata", "Şifre hatalı.")
            return

        # Başarılı
        self.user_id = user["id"]
        self.user_role = user["role"]
        self.username = user["username"]
        self.root.destroy()


# ─────────────────────────────────────────────────────────────
# Canlı Tick Servisi (arka plan thread)
# ─────────────────────────────────────────────────────────────
class LiveTicker:
    """
    Canlı modda saniyede bir TÜM ürünlerin fiyatını GBM ile günceller.
    Simülasyon sekmesi ÇALIŞIRKEN devre dışı kalır (çakışmasın diye).
    """
    def __init__(self, get_simulation_running):
        self.running = False
        self.thread = None
        self.get_simulation_running = get_simulation_running

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        from models import Product
        while self.running:
            try:
                # Simülasyon çalışırken duraklat
                if self.get_simulation_running():
                    time.sleep(1)
                    continue

                rows = database.execute(
                    "SELECT * FROM products WHERE is_active=1"
                )
                with database.get_connection() as conn:
                    for r in rows:
                        p = Product.from_row(r)
                        new_price = pricing.update_price(
                            p, recent_orders=0, just_ordered=False, dt=1.0
                        )
                        conn.execute(
                            "UPDATE products SET current_price=? WHERE id=?",
                            (new_price, p.id)
                        )
                        conn.execute(
                            "INSERT INTO price_history "
                            "  (product_id, price, is_simulated) VALUES (?, ?, 0)",
                            (p.id, new_price)
                        )
            except Exception as e:
                print(f"[live ticker error] {e}")
            time.sleep(config.TICK_INTERVAL_SEC)


# ─────────────────────────────────────────────────────────────
# Ana Uygulama Penceresi
# ─────────────────────────────────────────────────────────────
class MainApp:
    def __init__(self, root: tk.Tk, user_id: int, user_role: str, username: str):
        self.root = root
        self.user_id = user_id
        self.user_role = user_role
        self.username = username

        self.root.title(
            f"{config.APP_TITLE}  —  {username} ({user_role})"
        )
        self.root.geometry("1400x800")
        self.root.minsize(1100, 700)

        self._setup_style()
        self._build_ui()
        self._start_live_ticker()

        # Pencere kapatılırken thread'i durdur
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook.Tab", padding=[16, 8],
                        font=(config.FONT_FAMILY, 11))
        style.configure("TLabelFrame.Label",
                        font=(config.FONT_FAMILY, 10, "bold"))

    def _build_ui(self):
        # Üst çubuk
        topbar = tk.Frame(self.root, background=config.COLOR_PRIMARY, height=40)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(
            topbar, text=f"  🍽️  {config.APP_TITLE}",
            background=config.COLOR_PRIMARY, foreground="white",
            font=(config.FONT_FAMILY, 12, "bold")
        ).pack(side="left", padx=10)

        tk.Label(
            topbar,
            text=f"👤 {self.username} ({self.user_role})  ",
            background=config.COLOR_PRIMARY, foreground="#cbd5e1",
            font=(config.FONT_FAMILY, 10)
        ).pack(side="right", padx=10)

        # Notebook (sekmeler)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # 4 sekmeyi yarat
        self.menu_module       = MenuModule(self.notebook)
        self.orders_module     = OrdersModule(self.notebook,
                                              current_user_id=self.user_id)
        self.simulation_module = SimulationModule(self.notebook)
        self.reports_module    = ReportsModule(self.notebook)

        self.notebook.add(self.menu_module,       text="🍽️  Menü Yönetimi")
        self.notebook.add(self.orders_module,     text="📈  Canlı Sipariş")
        self.notebook.add(self.simulation_module, text="⏱️  Gün Simülasyonu")
        self.notebook.add(self.reports_module,    text="📊  Raporlar")

        # Yetki: garson menü düzenleyemesin (sekmeyi devre dışı bırak)
        if self.user_role != "admin":
            # Garsonlar sadece sipariş alır
            self.notebook.tab(0, state="disabled")
            self.notebook.select(1)

        # Alt status bar
        self.status_var = tk.StringVar(value="Hazır")
        status = tk.Label(
            self.root, textvariable=self.status_var,
            background="#e2e8f0", foreground=config.COLOR_PRIMARY,
            font=(config.FONT_FAMILY, 9), anchor="w", padx=8
        )
        status.pack(fill="x", side="bottom")

    def _start_live_ticker(self):
        """Canlı fiyat tick'ini başlat (simülasyon çalışırken pasif)."""
        self.live_ticker = LiveTicker(
            get_simulation_running=lambda: self.simulation_module.running
        )
        self.live_ticker.start()
        self.status_var.set("🟢 Canlı tick çalışıyor (saniyede bir fiyat güncellemesi)")

    def _on_close(self):
        """Pencere kapatılırken thread'leri temizle."""
        self.live_ticker.stop()
        if self.simulation_module.running:
            self.simulation_module.running = False
        self.root.after(200, self.root.destroy)


# ─────────────────────────────────────────────────────────────
# Giriş Noktası
# ─────────────────────────────────────────────────────────────
def main():
    # DB var mı kontrol et
    if not os.path.exists(config.DB_PATH):
        print("Veritabanı bulunamadı. Lütfen önce 'python seed_data.py' çalıştırın.")
        # GUI'siz uyarı ver
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Veritabanı yok",
            "Veritabanı bulunamadı.\n\n"
            "Lütfen önce şu komutu çalıştırın:\n\n"
            "    python seed_data.py"
        )
        return

    # Login penceresi
    login_root = tk.Tk()
    login = LoginWindow(login_root)
    login_root.mainloop()

    if login.user_id is None:
        return  # Kullanıcı pencereyi kapattı

    # Ana uygulama
    app_root = tk.Tk()
    app = MainApp(app_root, login.user_id, login.user_role, login.username)
    app_root.mainloop()


if __name__ == "__main__":
    main()
