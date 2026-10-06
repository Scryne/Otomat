# Orbit Ruler — logo kiti (2026-10-06)

**Fikir:** asteroitin yolu bir cetvel; Ay'ın yörüngesine (halka) en yakın noktasında teğet geçer, o noktada nane
rengi asteroit. Merkezde Dünya. Videolardaki `yakin_gecis` şablonunun özeti: "ne kadar yakın, ölçerek".
Earth in Numbers'ın şeritli dünyasından bilerek ayrı (K-11): farklı biçim, renk ailesi ve font.

Renkler `kanallar/uzay/DESIGN.md`'den: zemin `#04050b`, halka ve cetvel `#c9ccd8`, Dünya `#3f86f2`, asteroit
`#5ef0c8` (tek vurgu). Yazı Space Grotesk Bold/Medium (OFL), yalnız PNG banner'da.

| Dosya | Kullanım |
|---|---|
| `youtube/profil-800.png` | Kanal profil resmi (daireye kırpılır; sembol dairenin içinde). **Studio'dan yüklenir** (API yok) |
| `youtube/banner-2560x1440.png` | Kanal banner'ı; içerik ortadaki 1546×423 güvenli alanda. API ile yüklendi (2026-10-06) |
| `youtube/filigran-150.png` | Video filigranı. API isteği gönderildi, yanıt kütüphane hatasıyla okunamadı: Studio'da kontrol |
| `master/sembol-*.svg` | Sembol: siyah, koyu zemin, şeffaf; `-kucuk-` 32 px ve altı (çentiksiz, kalın) |
| `master/gen.py` | Sembol üreticisi (parametrik); `youtube.py` YouTube PNG'leri; `kanal_ayarla.py` banner + açıklama + anahtar kelime |

**Kurallar:** 32 px ve altında küçük kesim. Nane yalnız asteroit noktasında. Açık zeminde siyah sürüm.

**Test:** svg_audit siyah 100/100, renkli (3 renk) 100/100; 16/32 px piksel testi (halka + Dünya okunuyor, cetvel ince
çizgi olarak kalıyor); profil daire kırpması; banner güvenli alan. Marka tescil araması yapılmadı. Üretim: logo-design
skill'i. Konseptler: A dereceli yörünge (kadran/yükleniyor simgesine benziyordu), B ölçek dizisi (baloncuk/kardan adam
okuması), C teğet cetvel (seçilen).
