"""
module_menu.py — 👤 ÜYE 1: Menü Yönetimi
═══════════════════════════════════════════════════════════════
Bu modül 4 katmanı da kapsar:
  🎨 GUI:    Treeview ürün listesi, ekleme/düzenleme formu
  💾 DB:     products tablosu CRUD (Create, Read, Update, Delete)
  📊 Grafik: Kategori bazında pasta grafiği (matplotlib)
  🧠 Mantık: Maliyet validasyonu, P_min/P_max hesabı

Sunum İpucu:
  - Önce ürünü ekle, listede gör.
  - Sonra "Kategori Dağılımı" butonuna bas, pasta grafiğini göster.
  - Hocaya: "Bu sekmenin tamamını ben yazdım. SQL CRUD'u burada,
    pandas + matplotlib görselleştirmeyi de burada yaptım."
"""
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import config


class MenuModule(ttk.Frame):
    """Menü yönetim sekmesi — ttk.Notebook'a eklenir."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()
        self.refresh_products()

    # ─────────────────────────────────────────────────────
    # GUI Kurulumu
    # ─────────────────────────────────────────────────────
    def _build_ui(self):
        # Üst başlık
        header = ttk.Label(
            self, text="🍽️  Menü Yönetimi",
            font=config.FONT_TITLE
        )
        header.pack(pady=(10, 5), padx=10, anchor="w")

        subtitle = ttk.Label(
            self,
            text="Ürün ekleyin, düzenleyin, silin. Kategori dağılımını görselleştirin.",
            font=config.FONT_NORMAL
        )
        subtitle.pack(pady=(0, 10), padx=10, anchor="w")

        # İki sütunlu yerleşim: sol = liste + form, sağ = grafik
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        # ─── SOL: Ürün listesi + form ───
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Treeview
        cols = ("ad", "kategori", "maliyet", "fiyat", "stok")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        for col, label, width in [
            ("ad",       "Ad",        160),
            ("kategori", "Kategori",  110),
            ("maliyet",  "Maliyet",   80),
            ("fiyat",    "Anlık Fy.", 90),
            ("stok",     "Stok",      60),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Form
        form = ttk.LabelFrame(left, text=" Ürün Bilgileri ")
        form.pack(fill="x")

        self.entries = {}
        for i, (key, label) in enumerate([
            ("name",       "Ad"),
            ("category",   "Kategori"),
            ("cost",       "Maliyet (₺)"),
            ("base_price", "Baz Fiyat (₺)"),
            ("stock",      "Stok"),
        ]):
            ttk.Label(form, text=label).grid(
                row=i, column=0, sticky="w", padx=8, pady=4
            )
            entry = ttk.Entry(form, width=20)
            entry.grid(row=i, column=1, padx=8, pady=4, sticky="ew")
            self.entries[key] = entry
        form.columnconfigure(1, weight=1)

        # Butonlar
        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="➕ Ekle",       command=self.add_product).pack(side="left", padx=2)
        ttk.Button(btn_row, text="✏️ Güncelle",  command=self.update_product).pack(side="left", padx=2)
        ttk.Button(btn_row, text="🗑️ Sil",       command=self.delete_product).pack(side="left", padx=2)
        ttk.Button(btn_row, text="🔄 Yenile",    command=self.refresh_products).pack(side="left", padx=2)
        ttk.Button(btn_row, text="📊 Grafik Yenile",
                   command=self.refresh_chart).pack(side="left", padx=2)

        # ─── SAĞ: Grafik paneli ───
        right = ttk.LabelFrame(body, text=" Kategori Dağılımı (Matplotlib) ")
        right.grid(row=0, column=1, sticky="nsew")

        self.fig = Figure(figsize=(5, 5), dpi=90)
        self.ax  = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    # ─────────────────────────────────────────────────────
    # DB İşlemleri (CRUD)
    # ─────────────────────────────────────────────────────
    def refresh_products(self):
        """SELECT — DB'den oku, Treeview'i güncelle, grafiği yenile."""
        try:
            rows = database.execute(
                "SELECT id, name, category, cost, current_price, stock "
                "FROM products WHERE is_active=1 ORDER BY category, name"
            )
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", str(e))
            return

        # Treeview'i temizle, doldur
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(
                    r["name"], r["category"],
                    f"{r['cost']:.2f}",
                    f"{r['current_price']:.2f}",
                    r["stock"],
                )
            )
        self.refresh_chart()

    def add_product(self):
        """INSERT — yeni ürün ekle."""
        data = self._read_form()
        if data is None:
            return
        try:
            with database.get_connection() as conn:
                conn.execute(
                    "INSERT INTO products "
                    "  (name, category, cost, base_price, current_price, "
                    "   stock, initial_stock) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        data["name"], data["category"],
                        data["cost"], data["base_price"], data["base_price"],
                        data["stock"], data["stock"],
                    )
                )
        except Exception as e:
            messagebox.showerror("Eklenemedi", f"Hata: {e}")
            return
        messagebox.showinfo("Tamam", f"{data['name']} eklendi.")
        self._clear_form()
        self.refresh_products()

    def update_product(self):
        """UPDATE — seçili ürünü güncelle."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Seçim yok", "Önce listeden bir ürün seçin.")
            return
        data = self._read_form()
        if data is None:
            return
        product_id = int(sel[0])
        try:
            with database.get_connection() as conn:
                conn.execute(
                    "UPDATE products SET "
                    "  name=?, category=?, cost=?, base_price=?, stock=? "
                    "WHERE id=?",
                    (
                        data["name"], data["category"],
                        data["cost"], data["base_price"], data["stock"],
                        product_id,
                    )
                )
        except Exception as e:
            messagebox.showerror("Güncellenemedi", str(e))
            return
        messagebox.showinfo("Tamam", "Güncellendi.")
        self.refresh_products()

    def delete_product(self):
        """DELETE — yumuşak silme (is_active=0)."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Seçim yok", "Önce bir ürün seçin.")
            return
        if not messagebox.askyesno("Onay", "Bu ürünü silmek istediğinize emin misiniz?"):
            return
        product_id = int(sel[0])
        try:
            with database.get_connection() as conn:
                conn.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))
        except Exception as e:
            messagebox.showerror("Silinemedi", str(e))
            return
        self.refresh_products()

    # ─────────────────────────────────────────────────────
    # Form yardımcıları
    # ─────────────────────────────────────────────────────
    def _read_form(self) -> dict | None:
        """Form alanlarını oku ve doğrula."""
        try:
            data = {
                "name":       self.entries["name"].get().strip(),
                "category":   self.entries["category"].get().strip(),
                "cost":       float(self.entries["cost"].get()),
                "base_price": float(self.entries["base_price"].get()),
                "stock":      int(self.entries["stock"].get()),
            }
        except ValueError:
            messagebox.showerror(
                "Hatalı Değer",
                "Maliyet/fiyat sayı olmalı, stok tam sayı olmalı."
            )
            return None

        # İş kuralı: fiyat maliyetin altında olamaz
        if not data["name"] or not data["category"]:
            messagebox.showerror("Eksik", "Ad ve kategori boş olamaz.")
            return None
        if data["cost"] <= 0 or data["base_price"] <= 0:
            messagebox.showerror("Hatalı", "Maliyet ve fiyat pozitif olmalı.")
            return None
        if data["base_price"] < data["cost"] * (1 + config.DEFAULT_MIN_MARGIN):
            messagebox.showerror(
                "Mantıksız Fiyat",
                f"Baz fiyat en az maliyetin {(1+config.DEFAULT_MIN_MARGIN):.0%} "
                f"katı olmalı (₺{data['cost']*(1+config.DEFAULT_MIN_MARGIN):.2f})."
            )
            return None
        if data["stock"] < 0:
            messagebox.showerror("Hatalı", "Stok negatif olamaz.")
            return None
        return data

    def _clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, "end")

    def _on_select(self, event):
        """Listede satıra tıklandığında formu doldur."""
        sel = self.tree.selection()
        if not sel:
            return
        product_id = int(sel[0])
        rows = database.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)
        )
        if not rows:
            return
        p = rows[0]
        self._clear_form()
        self.entries["name"].insert(0, p["name"])
        self.entries["category"].insert(0, p["category"])
        self.entries["cost"].insert(0, str(p["cost"]))
        self.entries["base_price"].insert(0, str(p["base_price"]))
        self.entries["stock"].insert(0, str(p["stock"]))

    # ─────────────────────────────────────────────────────
    # Görselleştirme — Kategori Pasta Grafiği
    # ─────────────────────────────────────────────────────
    def refresh_chart(self):
        """Pandas + matplotlib ile kategori dağılımı."""
        try:
            with database.get_connection() as conn:
                df = pd.read_sql_query(
                    "SELECT category, COUNT(*) as adet, SUM(current_price) as deger "
                    "FROM products WHERE is_active=1 "
                    "GROUP BY category",
                    conn
                )
        except Exception as e:
            messagebox.showerror("Grafik Hatası", str(e))
            return

        self.ax.clear()
        if df.empty:
            self.ax.text(0.5, 0.5, "Veri yok",
                         ha="center", va="center", transform=self.ax.transAxes)
        else:
            colors = ["#3b82f6", "#16a34a", "#f59e0b", "#dc2626", "#8b5cf6", "#06b6d4"]
            wedges, texts, autotexts = self.ax.pie(
                df["adet"],
                labels=df["category"],
                autopct=lambda pct: f"{pct:.1f}%",
                colors=colors[:len(df)],
                startangle=90,
                textprops={"fontsize": 9},
            )
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontweight("bold")
            self.ax.set_title("Menüdeki Kategori Dağılımı",
                              fontsize=11, fontweight="bold")

        self.fig.tight_layout()
        self.canvas.draw_idle()
