---
proje: Otomat
created: 2026-10-06
type: rehber
---
# Yeni kanal ekleme (kanal 2: Orbit Ruler)

Scryne'ın dokunuşu üç adım, **üç ayrı gün**. 10-03 dersi: yeni hesap/kanal + Cloud + API'yi aynı güne yığmak Google'ın
otomatik kilidine takıldı. Buffer da yeni kanalın bağlanması için 1–2 gün bekletebiliyor.

Ön koşul: Earth in Numbers'ı açtığın **eski Google hesabın** (marka hesaplarının sahibi). Yeni Gmail açma.

## Gün 1 — Kanalı aç (K1, ~5 dk)

1. youtube.com → sağ üstte profil resmin → **Ayarlar** → **Yeni kanal oluştur** (ya da "Kanal ekle veya yönet" →
   **Kanal oluştur**).
2. Ad: `Orbit Ruler` · Herkese açık kullanıcı adı: `@orbitruler` (2026-10-06'da boştu).
3. Oluştur. **Başka hiçbir şey yapma** (Studio ayarları, yükleme, Buffer, API: hepsi sonraki günlere).
4. Bana "kanal açıldı" yaz. Kanal kimliğini ben API'den okurum.

## Gün 2 — Buffer'a bağla (K2, ~3 dk)

1. buffer.com → **Channels** → **Connect channel** → **YouTube**.
2. Google'da **eski hesabınla** gir. Kanal seçiminde **Orbit Ruler**'ı seç. Buffer kanalı **sahibi** olarak bağlar;
   "yönetici" olarak bağlanmaz.
3. "Bu kanal henüz bağlanamaz" derse 1 gün bekle, tekrar dene.
4. Ücretsiz planda 3 kanal sınırı var: Earth + Orbit Ruler = 2. Kanal bağlayıp koparma: ağ başına ömür boyu 8 bağlantı
   hakkı var.

## Gün 3 — Bizim uygulamaya izin ver (K3, ~2 dk)

Komutu ben çalıştırırım, sen yalnız tarayıcıda tıklarsın:

```
OTOMAT_KANAL=uzay uv run python -m otomat.yayin.youtube yetki
```

1. Açılan Google sayfasında eski hesabını seç → **hesap/kanal seçiminde Orbit Ruler** (Earth değil).
2. "Google bu uygulamayı doğrulamadı" uyarısı: **Gelişmiş** → **Otomat'a git (güvenli değil)**. Uygulama bizim; uyarı
   doğrulama başvurusu bitmediği için. Earth'te de aynısı oldu.
3. İzinlerin hepsine onay → "kimlik doğrulama tamamlandı" sayfası.

Sonra ben: `gh secret set YT_TOKEN_JSON_UZAY < sirlar/token_uzay.json`, repo değişkeni `OTOMAT_YAYIN_UZAY=buffer`,
matrise `uzay` satırı, kanal kimliğini doğrulama (token gerçekten Orbit Ruler'a mı ait), ilk koşu ve oturumsuz yayın
kontrolü.

## Sonra (isteğe bağlı, acele yok)

Profil resmi, banner, açıklama: `docs/marka/uzay/` hazırlanınca Studio'ya yükleme sende (Earth'teki gibi).
