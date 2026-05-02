# 🍽️ The Flavor Exchange

> **Lezzet Borsası** — Restoranların menüsündeki yemekleri borsa hisseleri gibi davranan dinamik varlıklar olarak modelleyen Python tabanlı yönetim sistemi.

**Python Dersi · Dönem Sonu Projesi · 4 Kişilik Takım**

---

## 🎯 Proje Özeti

Sipariş yoğunluğu, mutfak yükü, stok seviyesi ve zaman gibi faktörlere bağlı olarak yemek fiyatları **gerçek zamanlı dalgalanır**. Sistem altında **Geometric Brownian Motion (GBM)** + mean reversion + talep şokları çalışır — finansta hisse fiyatlandırması için kullanılan standart matematiksel model.

### Ana Özellikler

- 📈 **Canlı borsa ekranı** — fiyatlar saniyede bir güncellenir, yeşil/kırmızı oklar
- 🍽️ **Sipariş alma** — fiyat sipariş anında kilitlenir
- ⏱️ **⭐ Gün Simülasyonu** — tüm bir restoran gününü hızlandırılmış canlı izleyin
- 📊 **Profesyonel raporlama** — pandas + seaborn ile heatmap, violin plot, bar chart
- 📤 **Excel/CSV dışa aktarım**
- 👥 **2 kullanıcı tipi** — Admin (yönetici) + Garson

---

## 🚀 Kurulum (VS Code)

### 1. Gereklilikler
- **Python 3.11** (önerilir) veya 3.12
- VS Code + Python eklentisi

### 2. Sanal ortam oluştur

```bash
# Proje klasörüne gir
cd flavor_exchange

# Sanal ortam (venv)
python -m venv venv

# Aktive et
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Bağımlılıkları kur

```bash
pip install -r requirements.txt
```

### 4. Veritabanını hazırla

```bash
python seed_data.py
```

### 5. Uygulamayı başlat

```bash
python main.py
```

### Demo Hesaplar

| Kullanıcı | Şifre        | Rol     |
|-----------|--------------|---------|
| `admin`   | `admin123`   | Admin   |
| `ahmet`   | `garson123`  | Garson  |
| `ayse`    | `garson123`  | Garson  |

---

## 📁 Dosya Yapısı

```
flavor_exchange/
├── main.py                  ← Giriş noktası (login + ana pencere)
├── config.py                ← Tüm sabitler ve parametreler
├── requirements.txt
├── README.md
│
├── database.py              ← SQLite bağlantı yönetimi (paylaşılan)
├── models.py                ← Product, Order, User dataclass'ları
├── pricing.py               ← ⭐ GBM borsa motoru (paylaşılan)
│
├── module_menu.py           ← 👤 ÜYE 1: Menü Yönetimi sekmesi
├── module_orders.py         ← 👤 ÜYE 2: Canlı Sipariş sekmesi
├── module_simulation.py     ← 👤 ÜYE 3: ⭐ Gün Simülasyonu sekmesi
├── module_reports.py        ← 👤 ÜYE 4: Raporlama sekmesi
│
├── day_script.py            ← Simülasyon senaryosu (kolay düzenlenir)
├── seed_data.py             ← Başlangıç ürünleri ve kullanıcılar
│
└── data/
    ├── flavor_exchange.db   ← SQLite veritabanı (otomatik oluşur)
    └── exports/             ← Excel/CSV çıktıları
```

---

## 👥 Takım Görev Dağılımı

Her üye **kendi modülünde** GUI + DB + Grafik + Mantık'ın hepsini yazar. Bu sayede herkes Python'un her katmanını öğrenir.

| Üye | Modül | Sorumluluk |
|-----|-------|------------|
| 👤 1 | `module_menu.py` | Menü CRUD, kategori pasta grafiği |
| 👤 2 | `module_orders.py` | Canlı borsa ekranı, sparkline'lar, sipariş alma |
| 👤 3 | `module_simulation.py` | ⭐ Hızlandırılmış gün replay, animasyonlu çoklu çizgi |
| 👤 4 | `module_reports.py` | Heatmap, violin, Excel/CSV dışa aktarım |

**Paylaşılan altyapı** (Sprint 1'de birlikte yazılır): `database.py`, `models.py`, `pricing.py`

---

## 📐 Borsa Matematiği (Özet)

Her tick için yeni fiyat:

$$
P_{t+1} = P_t \cdot \exp\bigl(\mu_{\text{toplam}} \cdot \Delta t + \sigma \sqrt{\Delta t} \cdot Z\bigr) \cdot (1 + \delta)
$$

| Bileşen | Anlamı |
|---------|--------|
| $\mu_{\text{demand}} = \alpha \cdot D_t$ | Sipariş yoğunluğu yukarı iter |
| $\mu_{\text{revert}} = \kappa \cdot \ln(P_{\text{base}}/P)$ | Mean reversion (baz fiyata çekiş) |
| $\mu_{\text{stock}} = \beta \cdot (1 - \text{stok}/\text{stok}_0)$ | Stok azaldıkça yukarı baskı |
| $\sigma \sqrt{\Delta t} \cdot Z$ | Gauss şoku (borsa titreşimi) |
| $\delta \sim \mathcal{U}(1\%, 2.5\%)$ | Sipariş anı sıçraması |
| Tabanlar: $P_{\min} = c \cdot 1.20$, $P_{\max} = c \cdot 2.50$ | Asla altı/üstü |

**Detaylı açıklama** → `pricing.py` ve master plan dokümanı.

---

## 🎬 Sunum Demo Senaryosu

1. **Menü sekmesi** (Üye 1): yeni ürün ekle, pasta grafiği yenile
2. **Canlı Sipariş** (Üye 2): birkaç sipariş ver, fiyatların sıçradığını göster
3. **Simülasyon sekmesi** (Üye 3): hız 200x, "Başlat" — bütün gün ~4 dakikada izlenir
   - 12:00'da Wagyu nasıl tırmanıyor
   - Mean reversion'ın çekişi
   - Stok bittiğinde fiyat hareketi
4. **Raporlar** (Üye 4): Heatmap göster, Excel'e aktar, dosyayı aç

---

## 🛠️ VS Code Önerileri

### `.vscode/settings.json`
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true
}
```

### Sanal ortamı VS Code'un seçtiğinden emin ol
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. `./venv/bin/python` (Mac/Linux) veya `.\venv\Scripts\python.exe` (Windows) seç

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `ModuleNotFoundError: No module named 'pandas'` | Sanal ortamı aktive ettin mi? `pip install -r requirements.txt` |
| `Veritabanı bulunamadı` | `python seed_data.py` çalıştır |
| Tkinter import hatası (Linux) | `sudo apt install python3-tk` |
| Grafikler donuyor | Simülasyon hızını düşür (200x → 60x) |
| Türkçe karakter Excel'de bozuk | `utf-8-sig` encoding kullanılıyor — Excel'de zaten doğru olmalı |

---

## 📜 Lisans

Bu proje sınıf projesi olarak hazırlanmıştır.
