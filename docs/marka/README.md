# Earth in Numbers — logo kiti (2026-10-04)

**Fikir:** şeritli bir dünya; ortadaki bant küreden taşar. Turuncu, videolardaki tek vurguyla aynı şey: "bakman gereken sayı".
Renkler ve font DESIGN.md'den: lacivert `#0b1220`, mavi `#4a8fe6`, turuncu `#ee5a2a`, açık zeminde koyu mavi `#184f95`,
yazı Barlow Condensed SemiBold (OFL), glifler path'e çevrildi (canlı metin yok).

| Dosya | Kullanım |
|---|---|
| `youtube/profil-800.png` | Kanal profil resmi (daireye kırpılır, sembol daire içinde) |
| `youtube/banner-2560x1440.png` | Kanal banner'ı; içerik ortadaki 1546×423 güvenli alanda |
| `youtube/filigran-150.png` | Video filigranı (Studio → Özelleştirme → Marka) |
| `sembol/` | favicon (küçük kesim), app ikonları, siyah/beyaz/tek renk varyantlar, `head-snippet.html` |
| `yatay/` | Yatay logo (koyu/açık zemin, siyah, beyaz) |
| `master/` | Kaynak SVG'ler + üretici betikler (`final.py`) |

**Kurallar:** 32 px ve altında `sembol-kucuk-*` (3 bant). Boşluk: logonun çevresinde en az bir bant yüksekliği.
Bantlar yeniden renklendirilmez; turuncu yalnız taşan bantta. Koyu zeminde mavi bantlar, açık zeminde `#184f95`.

**Test:** svg_audit 100/100 (sembol), 16/32/48 px piksel testi, tek renk, ters, kırpma. Rafta karşılaştırma: Eclipse IDE
ikonu (şeritli koyu disk + turuncu) en yakın benzer; ayrım mavi bantlar ve taşan çubuk. Marka tescil araması yapılmadı.
Üretim: logo-design skill'i (kaankiziltug, MIT).
