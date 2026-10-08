# Hikâye kanalları — marka kiti (2026-10-08, Faz 15)

Earth in Numbers → **Inkwell Oddities**, Orbit Ruler → **Lanternbug Tales** (K-17, K-19; adlar YouTube aramasında
eşsiz, 2026-10-08). Eski kitler (`master/`, `uzay/`, `youtube/` …) veri formatına aittir, arşiv.

| Kanal | Fikir (tek cümle) | Renkler | Yazı |
|---|---|---|---|
| Inkwell Oddities | Hokkadan yukarı fırlayan mürekkep damlası: olmaması gereken ama gerçek olan; gövdedeki dalga hikâyenin akışı | parşömen `#F1E6CC`, mürekkep mavisi `#1C2B45` | IM Fell English (OFL, `fontlar/`) |
| Lanternbug Tales | Parlayan karnı açık bir kitap olan ateş böceği: yatmadan önce hikâyeyi aydınlatır | gece `#1F2B4D`, krem `#F6EBD9`, ışık `#FFB703` (altyazı vurgusuyla aynı) | Luckiest Guy (Apache 2.0), büyük harf |

| Dosya | Kullanım |
|---|---|
| `<kanal>/profil-800.png` | Kanal profil resmi (daireye kırpılır, sembol %72). **Studio'dan yüklenir** (API yok) |
| `<kanal>/banner-2560x1440.png` | Banner; içerik ortadaki 1546×423 güvenli alanda. `otomat/yayin/marka.py` yükler |
| `<kanal>/filigran-150.png` | Video filigranı. `otomat/yayin/marka.py` yükler |
| `<kanal>/master/sembol.svg` | Siyah master (logo-design skill'i); `sembol-v*.svg` iterasyonlar; `sembol-renkli.png` 1024 |
| `hikaye_gorselleri.py` | Renkli PNG'leri masterlardan üretir |
| `otomat/yayin/marka.py` + `kanallar/<id>/marka.toml` | Açıklama (5 dil), anahtar kelime, banner, filigran, kanal düzeyinde MFK: günlük koşu kanal yeni adını alınca bir kez kendisi uygular |

**İterasyon notları:** Inkwell v1'de ters damla harita iğnesi okunuyordu; v2'de ortadaki damla mum alevi; v3'te eğik damla
yaprak/saksı; v4 (seçilen) daha dik ve yuvarlak damla + iz kabarcıkları, parşömen üstünde mürekkep okunuyor. Lanternbug
v1'de yuvarlak kanatlar + kafa Mickey Mouse silüetiydi; v2'de kanatlar başı örttü; v3 (seçilen) ince çapraz kanatlar.

**Test:** svg_audit 99/100 ve 98/100; 88/48/24 px daire kırpma önizlemesi gözle kontrol edildi (24 px'de hokka ve
sarı karın okunuyor). Marka tescil araması yapılmadı.
