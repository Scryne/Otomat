---
proje: Otomat
created: 2026-10-02
type: roadmap
status: aktif
---
# Otomat — Roadmap

Durum sütunu session-start hook'u tarafından otomatik okunur — format bozulmasın:
⏳ Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı.

| Faz | Adı | Durum | Bitti Kriteri |
| --- | --- | --- | --- |
| 1 | İskelet ve sağlık | ✅ Tamamlandı | Private repo `Scryne/Otomat`; CI (ruff + pytest + duman koşusu) yeşil; `.github/dependabot.yml` (uv); `config/modeller.toml`; Actions runner'da qwen3:4b + Kokoro + render süresi ölçülmüş ve yazılmış |
| 2 | Veri ve olgu motoru | ✅ Tamamlandı | USGS, World Bank, Eurostat adaptörleri; her biri ≥ 20 farklı olgu paketi üretir (kaynak URL, zaman, hash); sözleşme testleri kayıtlı gerçek yanıtla; tekrar engeli çalışıyor |
| 3 | Görsel motor | ✅ Tamamlandı | Nokta harita, koroplet, sıralı çubuk şablonları; 1080×1920, bölgesel zoom, atıf köşesi; her şablondan 3 gerçek-veri videosu kare kare kontrol edildi; görsel kimlik `DESIGN.md`'de |
| 4 | Anlatım ve kapılar | ✅ Tamamlandı | Olgu şablon havuzu (tip başına ≥ 5 varyant); LLM kanca/başlık (yer tutucu); anlamsal hakem seçimi 30 etiketli cümleyle ölçüldü (yerel vs Jev, D-8); TTS + kelime zamanlı altyazı; 10 uçtan uca video, kapı sonuçları raporlu |
| 5 | Yayın ve audit | ✅ Tamamlandı | Scryne D1–D3'ü yaptı; OAuth "In production"; yükleyici + planlama + 5 dilli metadata + altyazı; GitHub Pages'ta uygulama/gizlilik/şartlar; audit başvurusu gönderildi; ilk video gerçek kanalda (private-kilitli olsa bile); Plan B paketi çalışıyor |
| 6 | Geri besleme ve işletim | ✅ Tamamlandı | Analitik toplayıcı; faktörlü Thompson sampling (konu, kanca); günlük cron 3 gün kesintisiz; haftalık rapor; `invalid_grant` ve koşu hatası alarmı |
| 14 | Hikâye motoru (format değişimi) | ✅ Tamamlandı | `otomat/hikaye` main'de; Earth (gerçek tuhaf hikâye) ve Orbit (Ezop, genel kitle; K-24) için her kanaldan ≥ 2 uçtan uca video senaryo + kare + ses kontrolünden geçti; günlük koşu iki kanalda yeşil (alarmsız); test + CI yeşil |
| 15 | Kanal kimliği dönüşümü | 🔄 Devam Ediyor | Scryne kanalları yeniden adlandırdı (Inkwell Oddities, Lanternbug Tales) ve profil resmini yükledi; banner, açıklama (5 dil), anahtar kelime API ile yeni kimlikte; Orbit kanal düzeyinde MFK değil (K-24, 10-13; eski masal videoları video düzeyinde MFK); `kanal.toml` adları YouTube'la aynı; eski veri videoları private |
| 16 | Kart biçimi ve izlenme deneyi | 🔄 Devam Ediyor | Earth kart biçiminde (K-25) ≥ 5 video yayında; her birinin ilk saniyeleri geçen oranı (engaged / görüntüleme) ve ortalama izlenme %'si (döngü; görüntüleme tekrarı sayar) ölçüldü ve sahneli dönemle (%25-38) kıyaslandı; karar yazıldı: oran ≥ %50 → günde 3 video (slot kimliği), değilse biçim yeniden; Orbit'in genel kitle haftası (10-15'ten) değerlendirildi, kart mı sahne mi kararı yazıldı |
| 17 | Uzun animasyonlu hikâye (film hattı) | 🔄 Devam Ediyor | `otomat/film` main'de (senaryo denetimi, yerel FLUX.2 klein karakter kartı + sahne, Wan 2.2 i2v, Chatterbox anlatım + Whisper kapısı, kurgu, kapak, bölümlü açıklama), test + CI yeşil; pilot (Violet Jessop) kare, ses ve olgu denetiminden geçti; yayın yolu deneyle seçildi (K-30) ve pilot Inkwell Oddities'de public; ikinci ve üçüncü film farklı yapıda yayında |
| 7 | Gerçek kullanım | ⏳ Bekliyor | Final-Doküman'daki "bitti = kullanıldı" cümlesi yeni formatla gerçekleşti (14 gün, kod müdahalesiz; sayaç Faz 16'nın kararıyla oturan biçimin ilk günlük koşusuyla başlar); bulgular roadmap'e işlendi |
| 8 | Öldürme kriteri değerlendirmesi (tetiklemeli) | ⏳ Bekliyor | Kanal başına, yeni formatın ilk public videosundan 8 hafta sonra: son 56 günde ≥ 1,2M Shorts izlenmesi veya ≥ 200 abone ölçüldü; karar (sürdür / konsept değiştir / kapat) yazıldı |
| 9 | Reels ve görsel kolları (koşullu) | ⏳ Bekliyor | Faz 8 "sürdür" derse: aynı videolar Facebook/Instagram Reels'e; medya motorundan stok görsel kolu |
| 10 | Çok kanal temeli | ✅ Tamamlandı | Kanal profili (`kanallar/<id>/kanal.toml`), motor kanaldan habersiz; Actions matrisi (kanal başına iş, alarm, Release); Earth'ün davranışı değişmedi (regresyon testi + bir temiz günlük koşu main'de) |
| 11 | Kanal 2: Orbit Ruler (uzay) | ✅ Tamamlandı | JPL CAD + Exoplanet Archive; `yakin_gecis` + `olcek` şablonları, ayrı kimlik/ses/saat; 6 tipte uçtan uca video kare ve ses kontrolünden geçti; Scryne kanalı açtı ve Buffer'a bağladı (ayrı günler); token secret'ta; matrise eklendi; ilk planlı video public (oturumsuz doğrulandı) |
| 13 | Portföy işletimi | ✅ Tamamlandı | Haftalık raporda kanallar yan yana (üretim, izlenme, abone, kota: Buffer istekleri, API birimleri, Actions dakikası); kanal başına öldürme kriteri (K-14) raporda |

## Faz Detayları

Faz 1 ve "Gerçek kullanım" şablonla gelir: biri projenin sessizce çürümesini engeller, öbürü "bitti"yi kullanıma
bağlar. Aradaki fazlar projeye özeldir. Kararların gerekçesi `docs/Final-Dokuman.md` ve `docs/Proje-Fikri.md`
(Denetim D-1…D-10).

### Faz 1: İskelet ve sağlık
- **İşler:** `uv init` paket yapısı (`otomat/` altında `veri`, `anlati`, `gorsel`, `ses`, `yayin`, `haydut`, `rapor`);
  ruff + pytest; `.github/workflows/ci.yml` (lint, test, duman: tek videoluk kuru koşu, yüklemesiz);
  `.github/dependabot.yml` (`uv`); `config/modeller.toml` (qwen3 etiketi, Kokoro sürümü + hash); Actions'ta Ollama
  kurulumu ve model cache'i; private repo + Dependabot uyarıları. Spike kodu `spikes/`te kalır, ürün kodu yeniden yazılır.
- **Ölçülecek:** runner'da qwen3:4b ile 5 kanca üretim süresi, Kokoro 30 sn ses süresi, render süresi, cache geri yükleme
  süresi, toplam koşu dakikası → ayda dakika bütçesi.
- **Bitti Kriteri:** tablodaki gibi; ölçümler bu bölüme yazılır.
- **Ölçümler (2026-10-02, ubuntu-latest private runner, 7,8 GiB RAM):**

  | Model | Isınma | Kanca (5 deneme) | Kokoro 16 sn ses | Render 30 sn 1080×1920 |
  | --- | --- | --- | --- | --- |
  | qwen3:4b | 61,8 sn | 60–250 sn | 13,1 sn | 28,3 sn |
  | gemma3:4b | 16,6 sn | 3,0–4,5 sn | 8,5 sn | 19,2 sn |
  | qwen3:4b-instruct | 5,2 sn | 3,3–4,6 sn | 9,0 sn | 20,7 sn |

  Ollama kurulumu + model çekme ilk koşuda ~1,5 dk; ölçüm adımı ~1 dk. Günlük koşu tahmini 3–5 dk → ayda ~150 dk
  (kota 2.000 dk).
- **Notlar:**
  - `qwen3:4b` etiketi `think:false`'u yok sayıp düşünme metni üretti (yanıtlar "Hmm, the user wants…" ile başlıyor),
    kanca başı dakikalar sürdü. **Karar:** `qwen3:4b-instruct` (düşünmesiz, Apache-2.0) varsayılan, `gemma3:4b` yedek.
    Lokaldeki `qwen3:8b` aynı ayarla düşünmüyordu: etiketler zamanla farklı modellere işaret edebiliyor → model kimliği
    config'te ve sağlık nöbetinde, kod LLM yanıtının düşünme metniyle başlamadığını da kontrol etmeli (Faz 4).
  - Kanca çeşitliliği iki modelde de zayıf (5 denemede 3 kez aynı kalıp) → Faz 4'te kanca kalıbı parametreli istem,
    sıcaklık ve tekrar süzgeci.
  - İlk push'ta lint hatası: ölçüm dosyası CI adımları yerelde koşulmadan push edildi. Kural zaten vardı, uygulanmadı.
  - GitHub token'ı `workflow` kapsamı olmadan `gh repo create --push` reddetti; düz `git push` (Git Credential Manager) geçti.

### Faz 2: Veri ve olgu motoru
- **İşler:** adaptör arayüzü (`olgu_paketleri() -> list[OlguPaketi]`); USGS (son 30 gün, ülke bazında en güçlü,
  yıllık sayım), World Bank (askerî harcama/GSYH, borç, yaşam süresi, nüfus… gösterge listesi config'te), Eurostat
  (eğitim, GSYH, nüfus göstergeleri); ülke kodu eşleme (ISO A3 ↔ Natural Earth ↔ Eurostat geo); SQLite şeması;
  tekrar engeli (60 gün).
- **Bitti Kriteri:** tablodaki gibi.
- **Sonuç (2026-10-02):** canlı toplayıcı 105 benzersiz paket: USGS 40 (38 bölge + dünya 30 gün + yılın en güçlü 10'u),
  World Bank 35 (12 gösterge × en yüksek/en düşük/en çok artan), Eurostat 30 (10 veri seti). Sözleşme testleri
  `tests/veri/kayit/` altındaki kırpılmış gerçek yanıtlarla (16 test). Tekrar engeli: hash ya da anahtar 60 gün.
- **Notlar:**
  - World Bank'ta askerî harcama kodu `MS.MIL.XPND.GD.ZS` (hafızadan yazdığım `.GD.PT` geçersizdi) — gösterge kodları
    hep canlı uçla doğrulanır.
  - USGS bölge adları normalize edilmeli: "Japan" / "Japan region", "Fiji" / "Fiji Islands" / "Fiji region" aynı bölge.
    Okyanus sırtları (Mid-Atlantic Ridge vb.) "senin ülken" çerçevesine girmez, ayıklanıyor.
  - Hassas içerik: askerî harcamada 1. sıra Ukrayna (%34,5, savaş). Faz 4 politika listesi savaş/ölüm çerçevesini
    nötr tutmalı ("military spending" veridir, yorum değil).
  - Kaynak API'lerin şeması değişirse adaptör sessizce az paket üretebilir → Faz 6'da günlük paket sayısı alarmı.

### Faz 3: Görsel motor
- **İşler:** üç şablon; kamera/zoom; ilk 1 sn'de kancayı görsel olarak taşıyan açılış; tipografi (OFL font) ve renk
  kimliği (`DESIGN.md`); kapak karesi; atıf köşesi.
- **Bitti Kriteri:** tablodaki gibi; kareler `gorsel-dogrulama` mantığıyla (taşma, okunurluk) gözle kontrol.
- **Sonuç (2026-10-02):** `otomat/gorsel/` — `sahne` (kanca kartı, başlık, atıf, güvenli alan), `nokta_harita` (bölge
  videosunda 2 sn yakınlaşma + 5° ızgara), `sirali_cubuk` (10→1 geri sayım, 1. sıra turuncu, ortanca çizgisi), `koroplet`
  (dünya/Avrupa, rank tabanlı beşte birlik tonlar + sınır değerleri, ilk 3 turuncu kenar, küçük ülkeler halka).
  `ornekler.py` 9 gerçek-veri videosu üretti (3 × şablon), her biri 4 kontrol karesiyle incelendi; 30 sn video ~25 sn.
  Kimlik `DESIGN.md` frontmatter'ından okunuyor (tek kaynak), lint 0 hata/0 uyarı; renkler dataviz doğrulayıcısından geçti.
- **Notlar:**
  - İlk turda bulunan ve düzeltilen kusurlar: okyanus bölgesinde (Tonga) boş harita → ızgara; üç satırlık başlık Avrupa
    haritasına çarpıyordu → içerik üst sınırı başlığın gerçek yüksekliğinden hesaplanıyor; dünya koropleti dikeyde kısa →
    altına büyük ilk-3 listesi; rank tabanlı renk + min/max lejant yanıltıcıydı → beşte birlik sınır değerleri.
  - World Bank "ülke" listesinde Macao, Hong Kong gibi bölgeler var; nüfus yoğunluğunda ilk 3'ün üçü de harita üstünde
    nokta kadar. Faz 4: kapsam ifadesi "countries and territories"; haydut bu tür paketlerde çubuk şablonunu seçebilir.
  - `npx @google/design.md` yine zaman aşımına düştü; paket scratchpad'e kurulup `.bin/design.md` ile çalıştı.

### Faz 4: Anlatım ve kapılar
- **İşler:** olgu tipi → cümle şablon havuzu; LLM istemleri (kanca kalıbı parametreli); sayı/tutucu kapısı; anlamsal
  hakem (olgu paketi + cümle → destekleniyor mu); politika listesi (yasak ifade, tıbbi/siyasi iddia); Kokoro;
  Whisper kelime zamanları; yakılmış altyazı + SRT.
- **Ölçüm (D-8):** 30 cümle (15 doğru, 15 bilerek bozulmuş: yanlış nicelik, yanlış bağlam, veride olmayan iddia) →
  yerel hakem ve Jev'in yakalama/yanlış alarm oranı. Maliyetli seçenek K-1 gereği elenir.
- **Bitti Kriteri:** tablodaki gibi.
- **Sonuç (2026-10-02):**
  - `otomat/anlati/`: `olgu_cumleleri` (6 olgu tipi × 5 varyant, sayılar koddan), `anlatim` (LLM kanca + başlık,
    yer tutuculu; kanca ve başlık ayrı kapıdan geçer, 3 denemede geçemeyen parça `yedek`ten gelir, kaynak kayda geçer),
    `kapilar` (tutucu/rakam/yazıyla sayı, politika listesi, anlamsal hakem), `ses.py` (Kokoro, cümle başına seslendirme →
    kesin cümle zamanları), `uretim.py` (uçtan uca, `meta.json` + `ozet.json`).
  - **Hakem ölçümü** (`hakem_olcum.py`, `tests/veri/hakem_30.json`: 17 doğru, 13 bozuk cümle):

    | Hakem | Yanlışı yakalama | Doğruya yanlış alarm |
    | --- | --- | --- |
    | qwen3:4b-instruct, istem v1 | 13/13 (%100) | 9/17 (%53) |
    | **qwen3:4b-instruct, istem v2** | 12/13 (%92) | 3/17 (%18) |
    | gemma3:4b, istem v2 | 4/13 (%31) | 0/17 (%0) |

    v2 seçildi; kaçırdığı tek cümle ("because of regional threats") politika kapısında yakalanıyor → birlikte 13/13.
    Jev ölçülmedi: ücretli (istek başı ~$0,00003), K-1 gereği Scryne'ın anahtarından harcama yapılmadı.
  - **10 uçtan uca video** (`calisma/uretim/2026-10-02/`): 10/10 üretildi; 20 parçanın (10 kanca + 10 başlık) 16'sı LLM'den
    (kanca 9/10, başlık 7/10), 4'ü yedekten. Video 19–35 sn. Yerel süre/video: anlatım 2–7 sn, ses 5–10 sn, görsel 17–34 sn. Bir videonun sesi
    Whisper'la geri döküldü: ekran metniyle birebir ("€4,800" → "4,800 euros").
- **Notlar:**
  - Altyazı Whisper kelime zamanı yerine **cümle zamanı + karakter orantısı**: her cümle ayrı seslendirildiği için
    cümle sınırları kesin; runner'da Whisper adımı yok. Kelime düzeyinde senkron gerekirse v2.
  - Kanca kartı süresi seslendirilen kancaya göre 1,5–3 sn (DESIGN.md'deki sabit 1,5 sn güncellendi).
  - Model ilk denemede örnek başlığı kopyaladı (küresel videoya "Indonesia"); hakem bunu yakaladı. Örnekler konudan
    uzak tutuldu, başlık "konunun tamamını anlatmalı" kuralı eklendi.
  - Testler bir kapı açığı yakaladı: "thousands" (çoğul) yazıyla-sayı kapısından geçiyordu.
  - Bash heredoc içinde `
` kaçışı iki kez gerçek satır sonuna dönüştü (hafızadaki tuzak); kod düzenlemeleri artık
    yalnız Write/Edit ile.
  - Kalite izlemesi: bazı kancalar tuhaf ("How did Indonesia shape the planet's tremors?"); "This Year" geçmiş 365 gün
    için hafif yanlış. Haydut verisi (Faz 6) hangi kalıbın tuttuğunu gösterecek.

### Faz 5: Yayın ve audit
- **Scryne dokunuşları:** D1 kanal + kanal e-postası, D2 Google Cloud projesi + OAuth onayı, D3 audit formu
  (`docs/Dokunus-Noktalari.md`; her biri için adım adım rehber bu fazda yazılır).
- **İşler:** OAuth akışı (yerelde bir kez, refresh token → Actions Secret); yükleyici (`videos.insert` + `publishAt`);
  `localizations` (EN, ES, PT, DE, FR); `captions.insert` (5 dil); GitHub Pages; audit başvuru metni; Plan B: haftanın
  videoları + metadata dosyası Actions artifact'ı olarak, Studio'da toplu yükleme rehberi.
- **Bitti Kriteri:** tablodaki gibi.
- **Durum (2026-10-02):** hesap gerektirmeyen kısım bitti; Scryne'ın D1–D3'ünü ve site onayını bekliyor.
  - Yazılan: `otomat/yayin/youtube.py` (OAuth masaüstü akışı, `videos.insert` + `publishAt` + `localizations`,
    `captions.insert`, `invalid_grant` hatası), `ceviri.py` (ES/PT/DE/FR; kapı: çeviride rakam kümesi kaynakla aynı),
    `srt.py`, `hazirla.py`, `otomat/gunluk.py` + `.github/workflows/gunluk.yml` (her gün 06:17 UTC; `OTOMAT_YAYIN=teslim`
    iken Plan B: videolar haftanın GitHub Release'ine), `docs/rehber/youtube-kurulum.md` (D1–D3 adım adım),
    `docs/rehber/audit-basvurusu.md` (form metni), `site/` (uygulama sayfası, gizlilik, şartlar; kişisel veri yok).
  - Çeviri ölçümü: 10 video × 4 dil = 40 çiftin 36'sı kapıdan geçti (%90); geçemeyen dil o videoda atlanır.
  - Yerel günlük koşu uçtan uca geçti (teslim modu): 105 paket → seçim → 27 sn video → 4 dil → teslim klasörü.
  - **Runner koşusu geçti** (2026-10-02, workflow_dispatch): toplam ~14 dk (Ollama 1 dk, üretim 12 dk), video haftanın
    Release'ine (teslim-2026-H40) eklendi, durum ve rapor repoya commit'lendi. Ayda ~420 dk (kota 2.000).
  - **D1 ✅ D2 ✅ (2026-10-02):** kanal **Earth in Numbers** (UC6vokENR8hP2Yo1UdZSqdiQ), Cloud projesi `otomat-510419`
    (no. 93875631034), OAuth uygulaması Otomat "In production" (doğrulanmamış), token + istemci GitHub Secrets'ta.
    Site public: https://scryne.github.io/otomat-site/ (yayın-öncesi taraması 0 bulgu). Kanal ülkesi boş (Scryne kararı).
  - **İlk API yüklemesi ✅:** `DBVL_Cakzbw` private; 5 yerelleştirme (en/es/pt/de/fr), 5 altyazı izi doğrulandı.
  - Bekleyen: **D3** audit formu (Scryne). Onay gelince repo değişkeni `OTOMAT_YAYIN=api` → planlı public yayın.
  - **2026-10-03 geri adım:** yeni açılan kanal hesabı (`earthinnumbers.data`) aynı gün Cloud projesi + doğrulanmamış OAuth
    + API yüklemesi sonrası Google'ın otomatik güvenlik sistemine takıldı: girişte telefon istiyor, her numarayı reddediyor;
    OAuth istemcisi `disabled_client`. İlk proje, token ve test videosu kayıp sayıldı (`sirlar/eski-askida/`). Karar
    (Scryne): kanal, Scryne'ın eski Google hesabının altında **marka hesabı**; D1–D2 bu yolla tekrar. Günlük hat
    teslim modunda etkilenmedi. Ders: otomasyon kanalını yeni hesapla değil, yaşlı hesabın marka hesabıyla aç; kurulum
    adımlarını aynı güne yığma.
  - **D1 ✅ D2 ✅ (2026-10-03, marka hesabı):** kanal Earth in Numbers `UClWIcIloPvkYIHEJf8ntArA` (`@earth.innumbers`,
    ülke boş), Cloud projesi `otomat-510508` (no. 915389790988) Scryne'ın kendi hesabında, token + istemci Secrets'ta
    (üzerine yazıldı). Test yüklemesi bilerek ertelendi (aynı güne yığmama dersi). Sırada D3 (ertesi gün).
  - **D3 ✅ (2026-10-03 14:09):** audit formu gönderildi, Google'dan "Thank you for your submission" onayı geldi. Kanıtlar:
    site ekran görüntüleri + `docs/rehber/kanit/otomat-oauth-yukleme-analitik.pdf` + `docs/rehber/otomat-mimari.png`.
    Kullanım alanı: Video Yükleme + Analiz ve Raporlama; ek kota istenmedi (videos.insert 5/gün beyanı). Sırada: Google'ın
    yanıtı (süre taahhüdü yok). Onay → repo değişkeni `OTOMAT_YAYIN=api`, Faz 5 kapanır.
  - **✅ 2026-10-05 — audit'siz yol: `OTOMAT_YAYIN=buffer`.** Kilit yalnız bizim projemizin `videos.insert`'ünde. Buffer'ın
    (ücretsiz plan, GraphQL API) audit'li YouTube bağlantısı videoyu private yükler; `youtube.duzenle` ile etiket,
    yerelleştirme, `publishAt` ve altyazı bizim API'mizden yazılır (`otomat/yayin/buffer.py`, `gunluk.yayinla_buffer`).
    Buffer dosya almaz: video gönderim süresince public `otomat-site/media/`'da durur, sonra silinir (deploy key secret
    `OTOMAT_SITE_ANAHTAR`). Günde tek slot (`yayin_slotu`: 14:00 UTC, kanaldaki son videonun ertesi günü). Buffer düşerse
    video Plan B paketine düşer + alarm. Kanıt: H40 üç video bu kodla yayında/planlı (`LPUuwdrc0E0` public, oturumsuz
    oEmbed 200; `W8-h8hWh5Pc` 06.10, `cv2snoQBV80` 07.10), 10-05 `JXSEMofyS3k` 08.10; 5 dil altyazı izleri doğrulandı.
    Araştırma ve test: `docs/arastirma/06-ucuncu-taraf-yukleme.md`. Audit gelirse `api` moduna dönmek isteğe bağlı.
- **Notlar:**
  - Çeviri ilk sürümde 4 kelimelik altyazı parçalarını tek tek çevirtiyordu: model cümle ortasından bölünmüş satırları
    birleştirdi (13 → 9 satır), kapı ~%50 reddetti. Tam cümle çevirisi + aynı zamanlarla yeniden parçalama → %90.
  - Rakam ayrıştırıcı "August 14, 2026"yı tek sayı sanıyordu; binlik ayracı yalnız ardından tam 3 hane gelirse sayılır.
  - Plan B için artifact yerine haftalık Release: Scryne haftada tek sayfadan 7 videoyu indirir.
  - GitHub Pages private repoda ücretsiz değil → site ayrı public repoya gider (K-1).
  - (2026-10-04) Plan B'de günlük YUKLE.md "üretimin ertesi günü, UTC" saati yazıyordu; haftalık toplu yüklemede bu
    saatler geçmiş olur ve Studio TR saati ister. Artık Release'e `HAFTA.md` (`otomat/yayin/hafta.py`) eklenir: H hafta
    videoları H+1'e günde bir, 17:00 TR, kopyala-yapıştır bloklarıyla. H40 sayfası elle üretilip Release'e kondu.

### Faz 6: Geri besleme ve işletim
- **İşler:** analitik toplayıcı (günlük; `engagedViews`, `averageViewPercentage`; 72 sa olgunlaşma); ödül tanımı;
  konu ve kanca için ayrı Beta posteriorları; seçim logu; haftalık rapor şablonu; alarm.
- **Bitti Kriteri:** tablodaki gibi.
- **Durum (2026-10-04):** kod bitti ve yerelde uçtan uca doğrulandı; "3 gün kesintisiz" sayacı 2026-10-05 koşusuyla başlar.
  - Yazılan: `otomat/analitik.py` (yükleme listesi ↔ seçim başlık eşleştirmesi, Plan B'de elle yüklenen videolar için;
    3 günlük ödül penceresi, 2 gün gecikmeyle bir kez ölçülür), `otomat/haydut.py` (ödül, Beta posteriorları, ters CDF'li
    Thompson, `veri_olmadan` karşı-olgusu), `otomat/rapor.py` (haftalık rapor; elle `python -m otomat.rapor 2026-H41`),
    `durum.py`'de `secimler` + `olcumler` tabloları ve Faz 6 öncesi koşuların `gunluk.jsonl`'dan taşınması. `gunluk.py`:
    analitik üretimden önce (düşerse üretim sürer, alarm), konu ve kanca haydutta (kol rotasyonu kalktı), pazartesi rapor.
    `gunluk.yml`: `issues: write`, "Alarm (issue)" adımı.
  - Ödül tanımı: Final-Doküman "Önemli tasarım kararları".
  - Doğrulama: 9 yeni test (40/40). Gerçek DB kopyası + gerçek token ile yerel günlük koşu geçti (analitik 0 eşleşme /
    0 ölçüm, çünkü kanalda video yok; haydut veri yokken θ = u, `degisti` boş; video + 4 dil). Gerçek API ile H40 raporu
    üretildi. Bozuk refresh token ile analitik adımı `invalid_grant` alarmını çözüm komutuyla yazdı, üretim sürdü.
  - Açık: haydut audit gelene ya da Plan B videoları elle yüklenene kadar veri görmez; o zamana dek seçim prior'dan
    rastgeledir. Analitik toplayıcının gerçek bir videoyla ilk ölçümü ilk public videodan ~5 gün sonra.
  - **✅ (2026-10-07):** 3 gün kesintisiz: 10-05 (elle tetik, sayılır), 10-06 ve 10-07 planlı koşular `durum: tamam`;
    10-05'teki tek alarm (YouTube 500) yeniden denemeyle kapandı, sonrası alarmsız. Pazartesi raporu (H40) üretildi.
    `eslesen: 0` beklenen: eşleştirme yalnız Plan B'nin elle yüklenen videoları için, Buffer modunda kimlik koşuda yazılır.
    İzlenecek: ilk gerçek ödül ölçümü 10-11 koşusunda (`W8-h8hWh5Pc`, yayın 10-06 + 3 gün pencere + 2 gün gecikme).
- **Notlar:**
  - `gh issue list --label alarm` etiket yokken 1 ile çıkıyor; Actions `bash -e` ile koştuğu için etiket önce `--force`
    ile oluşturulur (yerelde sınandı).
  - Ödül mutlak izlenme değil komşu sırası: büyüyen kanalda her yeni video eskisini geçer, bu konu/kanca başarısı değil.
  - (2026-10-04) Yayın öncesi içerik taraması, gerçek metin ve karelerden üç hata çıkardı (Faz 2–4'ten kalma):
    1. "En çok artan" paketi düşüşü artış diye anlatıyordu: 2015–2025'te Avrupa'da doğum oranı hiçbir ülkede artmamış,
       yine de "biggest rise… Serbia, up from 9.3 to 9.1" üretildi. Artık yalnız yuvarlanmış değeri gerçekten artanlar
       aday; 3'ten azsa paket yok (`siralama.py`, testli). Paket sayısı 105 → 104.
    2. Dört gösterge adı "the highest {ad}" kalıbına oturmuyordu ("the highest people who emigrated in one year"):
       fertility rate, yearly emigration, road death rate, birth rate. Artış şablonlarına "the" eklendi.
    3. Sıralı çubuk: artış grafiğinde çubuk seviyeyi, sıra artışı gösteriyordu (3. sıra en uzun çubuk olabiliyordu);
       artık çubuk artışın kendisi, değer "+x", etikette "önceki to son". 10 satırda çubuk içindeki değer çubuktan
       taşıyordu (her 10'lu videoda); değer fontu satır yüksekliğine, köşe yarıçapı DESIGN'daki 4 px'e bağlandı.
  - (2026-10-04) Tam katalog taraması (104 paket × tüm varyantlar, 175 yer adı TTS → Whisper, şablon başına kare):
    4. Ham World Bank adları anlatı ve grafikteydi ("Congo, Dem. Rep.", "Korea, Rep.", "Bahamas, The" → cümle sonunda
       "Rep.."); USGS adlandırılmış depremleri bölge sanıyordu ("Japan Earthquake", "2025 Hubbard Glacier Earthquake"),
       "CA" kısaltması, Turkey/Turkiye/Türkiye üç biçim. Tek ad katmanı: `otomat/veri/adlar.py` (üç adaptör).
    5. Eşitlikte sahte "birinci": onlarca ülke %100'deyken alfabede önce gelen "en yüksek" oluyordu (elektrik, internet,
       orman %0, CO2 0.0). İlk 4 değer gösterimde ayrışmıyorsa bir ondalık daha; yine ayrışmıyorsa paket yok. 104 → 98.
    6. TTS yanlış okuyordu: Türkiye → "Tuakii", Palau, Nauru, Timor-Leste, "U.S." durağı. Yalnız seste yazım değişir
       (`anlatim.OKUNUS`), ekranda asıl ad.
    7. Ada bölgelerinde (110m kara verisinde yok) yakınlaşınca harita boş kalıyordu: bölge adı haritanın üstünde.
    8. Açıklama: iç içe parantezli lisans ve "#TheWorld", "#YourCountry" etiketleri sadeleşti.
  - (2026-10-05) "3 gün kesintisiz" sayacının ilk günü: 06:17 UTC planlı koşu 13:30'a kadar hiç başlamadı (önceki iki gün
    5–6 sa gecikmişti). Koşu elle tetiklendi, geçti (98 paket, orman örtüsü videosu, H41 Release'i, H40 raporu). Önlem:
    ikinci cron 16:47 UTC yedek; gün zaten üretildiyse koşu Ollama kurulmadan biter (`durum.bugun_secildi_mi` + workflow
    adımı); checkout dalın o anki ucunu alır (kuyrukta bekleyen koşu öncekinin durum commit'ini görsün). Sayaç için elle
    tetikleme de bir gün sayılır: ölçülen şey hattın kesintisiz video üretmesi, GitHub zamanlayıcısı değil.
  - (2026-10-05) Analitik adımı YouTube'un tek seferlik `500 INTERNAL_ERROR`'üyle düştü, alarm açıldı; aynı çağrı yerelde
    geçti. API okumaları ve devam ettirilebilir yükleme artık 5xx/429'da 4 kez üstel bekleyerek yeniden dener
    (`youtube.DENEME`); `captions.insert` çift iz açabileceği için denemesiz. H40 raporu analitikle yeniden yazıldı.
  - (2026-10-05) Sıralı çubukta 10 satırda etiketin inen harfleri ("j", "g") çubuğa değiyordu: etiketin alt kenarı artık
    çubuğun 6 px üstünde. Etkilenen iki teslim videosu (H40 10-04, H41 10-05) yalnız görsel yeniden çizilerek Release'te
    değiştirildi: aynı paket (hash kontrolü), aynı ses izi, altyazı zamanları SRT'den.

### Faz 14–15: Format değişimi — hikâye kanalları (2026-10-08)
- **Neden:** Veri videoları izlenmedi (Earth 4 public video: 63/3/3/8; Orbit 60). Scryne: "yapılan videolar izlenebilir
  bir türden değil… çocuk içerikleri, bir şeyi konu alan kısa hikâye daha çok tutuyor." Araştırma, spike'lar (S10, S11)
  ve kararlar: `docs/arastirma/08-format-hikaye.md` (K-15…K-19).
- **Kararlar:** Earth → gerçek tuhaf hikâyeler (Wikipedia:Unusual articles, genel kitle). Orbit → çocuklar için Ezop
  masalları, made for kids (Scryne riskleri gördükten sonra seçti, K-19). Yeni kanal açılmaz (Faz 12 iptal). Metin ve
  görsel Cloudflare Workers AI bedava kotasıyla (gpt-oss-120b, flux-2-klein-4b); havuzlar TypeSafe ile süzüldü (K-18).
- **Faz 7 ile ilişki:** iki kanalın çıktısı baştan değişti; 10-08'de başlayan sayaç geçersiz. Eski veri videoları
  private'a çekildi, planlı yayınları kaldırıldı, günlük workflow geçici olarak durduruldu (10-08 17:10 UTC).
- **Faz 14 durumu (2026-10-08):** `hikaye` dalı; motor + testler (92) yeşil. Earth uçtan uca: "Great Molasses Flood"
  37,7 sn, 1.697 neuron, ~3,5 dk (görseller 4'lü paralel). Bulgular ve düzeltmeler: suluboya kâğıt kenarı (otomatik
  kenar kırpma), "the tank" → askeri tank çizimi (görsel tarifi tek anlamlı olmalı), "40°F" (sembol kodda reddedilir),
  iki panelli görsel (istemde "tek kare"), havuzda iki bölümde listeli makale (tekilleştirme). Orbit ilk denemede 4
  turda hakemden geçemedi; aynı gün spike'larla 10.000 neuron günlük kota doldu (4006) → kota hatası artık
  yeniden denenmeden alarm olur; çocuk hakemi örneklerle netleştirildi, kota sıfırlanınca yeniden denenecek.
- **Doğrulama turu (2026-10-08 akşam, `urun-dogrulama`):** yayın kabul kapısı (`otomat/hikaye/kabul.py`, önce yazıldı,
  `07d2488`; elle düzeltilmiş referans + 5 kusurlu varyantın hepsi reddedildi) üretim hattına bağlandı: kabulden geçmeyen
  video yayına çıkmaz, hikâye düşer. Bulunan ve düzeltilen hatalar: (1) private'a çekilen 10 eski video yayın slotunu
  tutuyordu (Earth'ün ilk hikâyesi 10-12'ye kayacaktı) → `geri_cekilen` tablosu; (2) ses -21,6 LUFS (YouTube sessizi
  yükseltmez) ve müzik -47,5 LUFS'ta duyulmuyordu → anlatıcı -14, müzik -30/-27 LUFS'a ayrı normalize, karışım -15,4 LUFS,
  tepe -1,6 dBFS; (3) kelime vurgusu orantılı tahminde p90 0,58 sn kayıyordu → Whisper (base.en) hizalaması, p90 0,16 sn,
  en kötü 0,20 sn (bağımsız referans: Whisper small). Molasses senaryosunun 8 satırı kaynakla tek tek karşılaştırıldı (8/8).
  Testler 97, CI yeşil (PR #3), test gevşetme bulgularının gerekçesi test_kanal'da (arşiv profili eski değerleri kilitler),
  izolasyon: test koşusu durum/, sirlar/, kanallar/, raporlar/ dosyalarına dokunmadı.
- **Kademeli açılış (2026-10-08 19:38 UTC):** `hikaye` main'e (`95eff03`), günlük workflow yeniden açık. Earth buffer
  modunda (ilk hikâye 10-09 06:17 UTC koşusunda, yayın 14:00 UTC); Orbit `OTOMAT_YAYIN_UZAY=teslim`: çocuk masalı uçtan uca
  henüz üretilmedi (10-08'de kota doldu, ilk deneme 4 turda hakemden geçmedi, hakem netleştirildi). 10-09 koşusunun teslim
  paketindeki video kare + ses + senaryo kontrolünden geçince `buffer`'a alınır. Faz 7 sayacı Earth'ün 10-09 koşusuyla başlar.
- **2026-10-09 — pist ve kanal kararı:**
  - 06:17 cron'u hiç başlamadı. 12:53'te elle tetiklenen koşu iki kanalda Cloudflare 4006'ya takıldı (issue #4, #5).
  - Panelde "0/10k used today" görünüyordu ama engel 10-08 17:33'ten beri sürüyordu. Bu yüzden üretim yayından
    ayrıldı (K-22, `9dfe127`): buffer/api modunda kanal bugün + 2 günü planlı tutar, koşu başına en çok 2 video
    üretir. Yarının videosu planlıysa kota alarm değildir.
  - Araştırma `docs/arastirma/09-kanal-karari.md` (K-20…K-23): yeni kanal açılmaz. Orbit kanal düzeyinde MFK olur, eski
    uzay videoları video düzeyinde MFK değil kalır (silinmez).
  - İçerik:
    - Sahne başına 5 kamera hareketi.
    - Senaryo anlatıcı yayına çekildi, en çok 2 sayı (kod 3'ü aşanı onarıma yollar).
    - İlk sahnenin görseli kaydırmayı durduracak yakın kompozisyon.
    - Haftalık raporda neuron satırı; günlük koşunun üretim klasörü 7 günlük artifact.
- **Kanal adları:** YouTube "Inkwell Oddities"i gerekçesiz reddetti; ardından çok deneme kilidi (24 saat). Yedek adlar
  profilde (`yedek_adlar`); hangisi tutarsa kimlik o adla uygulanır.
- **Faz 15 için Scryne'dan:** iki kanalın adı ve tanıtıcısı (Studio → Özelleştirme → Temel bilgiler) ve profil resmi
  (API ile yüklenemiyor). Gerisi API ile.
- **İlk hikâye yayınları (2026-10-09 akşam):**
  - Kota 17:00 UTC'de açıldı (kayan 24 saat). İlk koşuda 5 hikâye üretildi ama hepsi reddedildi: Actions'ta
    ffprobe yok. Earth'te bir sahne görseli 3030 filtresine takılıp koşuyu düşürdü. Günün kotası gitti.
  - Düzeltmeler:
    - Kabul ffmpeg ile okuyor.
    - Filtreye takılan görsel yalnız o hikâyeyi düşürüyor.
    - Hazır üretim: kabulden geçmiş ama kanala çıkmamış video, artifact'tan dönüp kota harcamadan kullanılıyor.
    - Buffer medya adı kanal önekli (iki kanal `2026-10-10.mp4`'te çakıştı).
    - Hakem anlatım tutarlılığını da denetliyor.
  - Elle inceleme: kareler iki kanalda temiz. Curse of the Colonel (sırası karışık) ve The Ass And The Dog (diyalog
    kopuk) reddedildi.
  - Kanala çıkanlar:
    - Orbit "The Proud Lamp Learns Humility" (10-09 20:00 UTC, MFK). Orbit `OTOMAT_YAYIN_UZAY=buffer`.
    - Earth "Prester John" (10-10 14:00 UTC).
  - Bu videolar çevirisiz çıktı (kota boştu).
  - Earth'ün adı Studio kilidinde (~10-21). Orbit adı tamam, tanıtıcısı bekliyor.
- **Denetim (2026-10-09 gece, uçtan uca kod + Actions + artifact incelemesi):** bulunan ve düzeltilen hatalar:
  1. Artifact kartopu: her koşu önceki 6 koşunun artifact'ını `calisma/gunluk`'a indirip yeniden yüklüyordu (uzay
     44 → 60 → 73 MB, toplam ~380 MB; private repo kotası 500 MB). Önceki üretimler artık `calisma/onceki/<koşu>/`'ya
     iner, yalnız bu koşunun klasörü yüklenir. Kapsanan eski artifact'lar silindi.
  2. Kotaya takılan üretim aynı slotta yeniden seçilince yeni senaryo yazılıyor, eski senaryonun sahne görselleri
     (`cf.gorsel` "varsa üretme") yeni sahnelere karışıyordu. Hakemden geçen senaryo `senaryo.json`'a yazılır, sonraki
     koşu senaryoyu ve biten görselleri sürdürür (kota ikinci kez harcanmaz); senaryo yoksa eski çıktılar silinir.
     Uçtan uca denendi (Cloudflare'siz): 7 sahnenin yalnız eksik 2'si çizildi, video kabulden geçti.
  3. Buffer Orbit videolarını `madeForKids: false` yüklüyordu (sonra `duzenle` düzeltiyordu); Plan B `HAFTA.md`
     Orbit için de "çocuklara özel değil" diyordu. İkisi de kanalın MFK ayarından.
  4. Haftalık rapor yalnız pazartesi deneniyordu: pazartesi koşusu pist dolu diye atlanırsa hafta raporsuz kalırdı.
     Biten haftanın eksik raporu sonraki koşuda yazılır ("Üretilecek iş var mı" adımı bunu da sorar).
  5. Silinmiş/çok kısa Wikipedia makalesi tüm koşuyu düşürüyordu: artık yalnız o hikâye düşer.
  6. Başlık "Title Case" yazıldığı için her kelimesi ad sanılıp onarıma gidiyordu ("name not in source: Haunts");
     başlıkta yalnız sayı kapısı, adları hakem denetler. Onarımın boşalttığı satır onarıma döner.
  7. Kotaya takılan koşu raporda "hata" görünüyordu (alarm yine yazılır); "kota" olarak kalır.
  8. Dayanıklılık: müzik indirilemezse aynı mood'un sıradaki parçası; görselsiz/bozuk Cloudflare yanıtı yeniden
     denenir, yarım dosya yazılmaz; çeviri aynı metin için yeniden yapılmaz (hazır üretim kotayı ikinci kez yakıyordu).
  9. Oran yazımı ("1:4-million") sembol kapısından geçiyordu, anlatıcı "1, 4 million" okudu (Tree of Ténéré,
     10-11 planlı; Whisper small dökümüyle bulundu). Oran onarıma gider; saat ("12:30") okunduğu için serbest.
  - Runner doğrulaması (elle tetik, 10-09 20:19 UTC): yeni indirme düzeni ve artifact (24,5 MB, yalnız bu koşu,
    senaryo + çeviri dahil), Earth 10-11 videosu `StbOqiF1sT0` planlı (4 dil, `ceviri_neuron` 317, `buffer_istek` 2,
    `havuz_kalan` 710). Portföy işi rapor klasörü yokken `git add`'de düştü, düzeltildi. Açık: "Niamey" "Naomi's"
    okunuyor (nadir yer adı telaffuzu; genel çözüm yok).
  - Eklenen: düşen hikâyelerin neuron'u, Buffer istek sayısı ve hikâye havuzunun kalanı günlük kayıtta ve haftalık
    raporda; havuz 21 hikâyenin altına inince alarm. Faz 13 portföy raporu (aşağıda).
  - Açık (kod dışı): 10-09/10-10 videolarında görsel kalite sorunları: karakter kareden kareye değişiyor (0c9d283'ten
    önce üretildi), Cock and Jewel'de iki başlı tavuk ve hikâyede olmayan iki ayı, Prester John'da anlamsız yazılar
    (flux "no text" kuralını her zaman tutmuyor). Bir görsel kalite kapısı (vision model) neuron harcar; ölçülmeden eklenmedi.
- **Görsel kalite ve politika (2026-10-12):**
  - Planlı ve yayındaki 5 videonun sahneleri kare kare incelendi. İki video geri çekildi, yeni komutla:
    `python -m otomat.yayin.youtube geri <id> "<neden>"`. Komut videoyu private yapar, `publishAt`'i düşürür,
    `geri_cekilen` tablosuna yazar.
    - Orbit "The Cock Who Chose a Grain" (`iOvy5ikUJiY`): public'ti, 0 izlenmeyle çekildi. Masalda olmayan iki
      insansı ayı vardı, tavuk her karede başkaydı.
    - Earth "Lord Bloody Wog Rolo" (`aEXgalmgZfA`, 10-13 planlı): başlıkta etnik hakaret ("wog") vardı.
  - Earth "Drag Nun" (10-12) yayında kaldı. Karelerinde anlamsız yazılar var, ama çekilirse slot boş kalırdı.
  - Hakaret kapısı (`kaynaklar.HAKARET`): havuzdaki makale adında ve yayın kabulünde (başlık, satırlar, kaynak
    adı) çalışır. Havuzdaki 713 uygun makalede başka eşleşme yok.
  - `marka.eski_videolari_ayir` artık yalnız format değişiminin veri videolarını "çocuklara özel değil" yapar.
    Kalite yüzünden çekilen masal çocuk içeriği olarak kalır.
  - **Kare içi yazı** (Prester John, LaRouche, Sister Boom Boom, Wog Rolo):
    - Kök neden: senaryo modelinin sahne tarifleri yazı taşıyan nesnelerle dolu ("neon signs", "sandwich board
      covered with slogans", "'For Sale' sign"). flux, "no text" demesine rağmen bunları harfle çiziyor.
    - Önleme 1: senaryo isteminde bu nesneler yasak.
    - Önleme 2: `senaryo.gorsel_temizle`. Tarifte yazı taşıyan nesne kalırsa en çok 2 onarım turu yapılır.
      Onarımdan dönen tarif 8 kelimeden kısaysa alınmaz, çünkü S12'de model iki sahneye tarif yerine "SCENE 2"
      yazdı ve kare ana karaktersiz çıktı.
    - Yakalama: `hikaye/yazi.py`. RapidOCR karede yazı bulursa sahne yeni tohumla yeniden çizilir (video başına
      en çok 3 kare). Yeni kare daha yazılıysa eskisi kalır. Kayıt `meta.json`'da (`yazi`, `gorsel_onarim`).
    - Eşik ölçümü (87 sahne, gözle etiketli): en az 3 Latin harf ve güven ≥ 0,7. Masal karelerinde yanlış
      alarm 0. Gözle yazı görülen Earth karelerinin çoğu yakalanıyor (Sister 7/8, Wog 8/8).
    - S12 spike (~2.300 neuron): Sister'ın en yazılı 4 sahnesi onarımdan sonra 4/4 yazısız çizildi. Wog'un iki
      sahnesinde OCR bulgusu 6'dan 1'e ve 5'ten 0'a indi. Onarım turu metin kotasından ~200 neuron yer.
  - Alarm: pistin 3. gününün bütün hikâyeleri düşünce (10-11, #6) alarm çalıyordu. Yarının videosu planlıysa
    artık çalmıyor (`HikayeDustu`, K-22'nin kota kuralıyla aynı). Sonraki koşu aynı slotu yeniden dener.
  - Testler 138 (yeni ve değişen 9 test eski kodda düşüyor). CI OCR'ı Linux'ta `--extra gorsel` ile kurar.
  - Açık: karakter tutarlılığı ve hikâyede olmayan nesne (ayılar). Bunlar için vision modeli gerekir, neuron
    harcar; ölçülmeden eklenmedi.
- **Senaryo yakınsaması (2026-10-12 akşam):**
  - 10-11 ve 10-12'de Earth'te denenen 8 hikâyeden 7'si hakemden geçmedi, 5'i son turda tek sorunla: kaynakta
    olmayan ayrıntı ("for interviews"), tekrar eden olay, fazla sayı. 10-12 koşusu 3 hikâyeyi de düşürdü, Earth'ün
    10-13 slotu boş kaldı (Wog Rolo da geri çekilmişti). Orbit aynı günlerde hep geçti.
  - Sayı sınırı aşılınca yalnız son sayılı satır işaretleniyordu, onarım öbür satırlara dokunmadı (Loret, 4 turda
    4 sayı). Artık ilk iki sayıdan sonrakini taşıyan her satır onarıma gider.
  - Onarım istemi yeni ayrıntı, amaç, neden ya da sayı eklemeyi yasaklar (onarım yeni uydurma getirebiliyordu).
  - Son çare (`senaryo.satir_cikar`): son turda kalan sorunlar en çok iki ara satırdaysa (başlık, kanca ve son satır
    değil) o satırlar sahneleriyle çıkarılır, senaryo kod kontrolünden ve bir hakem turundan daha geçerse kabul.
    Kabul en az 6 satır ister. Çıkarılan satırlar `meta.json`'da (`senaryo.cikarilan`). Ek maliyet bir hakem çağrısı.
  - Testler 140. Etkisi canlı koşuda ölçülecek: Earth'ün hikâye başına geçme oranı (10-11/12: 1/8).
  - İlk canlı koşu (elle tetik, 10-12 21:00 UTC; dünkü akşam koşusunun kotası kayan pencereden düşünce): Earth'te 3
    hikâyeden 2'si geçti. Mónica Macías 10-13 boş slotuna (`OoBBwiDNlSc`, 4. turda temiz), Bartman 10-14'e
    (`ZwMNjnj4uBk`, 2. turda temiz) planlandı. Roland the Farter tek sorunla düştü ("fertile" kaynakta yok, satır 5).
    Satır çıkarma bu koşuda devreye girmedi. Alarm #7 kapandı.
  - Kare incelemesi: iki videoda hakaret, şiddet ya da yanlış olgu yok, yayında kalıyor (Drag Nun emsali). Kusurlar:
    - Bartman'da skor tabelası "WACTER" diye çizilmiş; formalarda bozuk takım adı var.
    - Bartman'ın son iki satırı ters sırada: "13 yıl sonra yüzük" satırından sonra "polis çıkardı" geliyor. Hakem
      zaman sıçramasını yakalamadı.
    - Mónica'da tabela ve istasyon yazıları anlamsız Asya harfleriyle çizilmiş. OCR yalnız Latin harfi sayıyor,
      masal karelerinde uydurma Çince yanlış alarm verdiği için (yazi.py ölçümü); bu bilerek kabul edilmiş bir açık.
  - Görsel onarımı Bartman'da iki turda hiçbir tarifi değiştirmedi. "jersey" karakter tarifindeydi ve istem
    karakter tarifini değiştirmeyi yasaklıyordu. Skor tabelasının neden kaldığı bilinmiyor (model yanıtı
    kaydedilmiyor). Düzeltmeler:
    - `giysi_duz`: jersey kodla uniform olur, karakter tariflerinde de.
    - `yazisiz`: onarımdan sonra da işaretli kalan tarifin yazı taşıyan yan cümlesi kodla düşer. OCR yeniden
      çiziminde de istemden düşer; eskiden yalnız sona "yazısız" cümlesi ekleniyordu.
    - Bartman'ın gerçek tariflerinde 4 işaretin 4'ü temizleniyor. Testler 142.
- **Değişen görünüş ve Orbit'in kitlesi (2026-10-13):**
  - 10-14/15 videoları kare kare incelendi. Earth "Heraclitus" temiz. Orbit "Felix the Fox Who Loved His Tail"
    (`HPfeJf5PlLc`, 10-15 planlı) geri çekildi: kuyruğunu kaybeden tilki 3 karede kuyrukluydu, masalın konusu bozuk.
    Sahne metni "his tail gone" diyordu, 7. sahne "tails intact" istiyordu.
  - S13 (`spikes/s13_karakter_durumu.py`): klein olumsuzu çizemiyor ("his tail gone" 2/2 kuyruklu), görüneni söyleyen
    olumlu tarifi çiziyor (2/2 kuyruksuz). llama-4-scout 11 karenin 10'unda kuyruğu doğru söyledi, ~51 neuron/kare.
  - Düzeltme (`336bbe2`): senaryo `changes` bildirir (kim, ilk sahne, olumlu görünüş, evet/hayır sorusu); kod sonraki
    sahnelerin istemine "X is now …" ekler; `uretim.durumlari_denetle` soruyu önce değişimden önceki karede sınar
    (ayırt etmiyorsa atlar), sonra her sahnede sorar; tutmayan kare yeni tohumla yeniden çizilir (video başına 3),
    yine tutmazsa hikâye düşer. Karakter tutarlılığı açığının bir kısmını kapatır (renk ve tür kayması hâlâ açık).
  - Orbit 0 izlenme: public 3 masal videosu 0, Earth'ün hikâyeleri 6-81. MFK Shorts'un dağıtımı kapalı görünüyor
    (`docs/arastirma/08`, 10-13 kararı). Scryne genel kitleyi seçti (K-24, `67a79e6`): Ezop yumuşatılmadan, yetişkin
    anlatıcı, gravür stili, IM Fell English altyazı, MFK kapalı; kanal açıklaması, anahtar kelime ve banner sloganı
    API ile uygulandı. `geri_cek` artık MFK'yı videonun kendi ayarından alır. Faz 14'ün Orbit kanıtı yeni formatla
    yeniden toplanır; 7 gün sonra Earth'le kıyas.
  - Kota: bu oturumun spike'ları ve 10-12 21:00 elle koşusu kayan pencerede 10.000'i doldurdu (18:30 UTC). 10-14
    sabah koşusu pistin 3. günü için kotaya takılırsa alarm çalmaz; Orbit'in boşalan 10-15 slotu takılırsa çalar.
- **Tam denetim (2026-10-13 akşam, Scryne: "eksikliklerin ve hataların tamamını çöz"):** dört paralel denetim
  (orkestrasyon/workflow, hikâye hattı, yayın/analitik/haydut, canlı veri tutarlılığı) ~60 bulgu; doğrulananlar
  düzeltildi, her biri için düzeltme öncesi davranışı reddeden test (`tests/test_denetim_*.py`; 148 → 183 test).
  - Hikâye hattı (`d3631a5`): cast `{name, look}` (Earth'te "Ad, tarif" geliyordu, karakter tarifi hiçbir sahne
    istemine girmiyordu); sayı kapısı tam sayı ("19" "1950"den geçiyordu), ad kapısı kısa adı tam kelime arar, gün/ay
    muaf; başlık uzunluğu ve hakaret render'dan önce; uzun kaynakta son da modele gider; Wikipedia 5xx/ağ hatası
    yeniden denenir ve hikâyeyi havuzdan düşürmez; cf.py kilitli neuron sayacı, kopan bağlantı, 401/403 denenmez,
    güven 0-1; sahne çizimi kota/filtrede kuyruğu iptal eder; görünüş denetimi OCR'dan önce, yeniden çizim yazısız;
    render hatasında ffmpeg kapanır; müzik indirmesi mp3 başlığıyla doğrulanır; kabul kaynak atfını türüne göre arar.
  - Yayın/orkestrasyon (`ffd4413`, `3e51c27`): slot "son videonun ertesi günü" değil ilk boş gün; pist denetimi
    planlaması düştüğü kaydedilen (`planlanamayan`) videoyu yeniden planlar, kanalda kaybolanı ve elle çekileni
    alarm yapar; token düşükse üretime girilmez; uzak slot üst üste iki koşu düşerse alarm; geçmişe düşen yayın anı
    hemen public; altyazılar dil başına; çeviri kotada kalan dilleri denemez ve atlananı raporlar; çeviri onarımı
    (`350737e`) çevirisiz planlanan videonun eksik dillerini sonraki koşuda tamamlar (10-15 Earth: 4 dil kotaya
    takılmıştı).
  - Analitik/rapor/Buffer/workflow (`481f9d3`): kanal `donem` (Earth 10-10, Orbit 10-15): haydut ödülleri ve K-14
    sayacı format döneminden (Orbit'in çocuk dönemi kolları kirletmesin; **Orbit K-14 karar günü buna göre kayar**);
    satırsız analitik yanıtı bir haftadan önce kalıcı sıfır yazılmaz; rapor aynı slotu bir kez sayar, geri çekileni
    "ulaşan" saymaz, son 4 haftanın eksiğini ve analitiksiz yazılanı yeniden yazar; Buffer site push'u rebase ile
    yeniden dener, 30 günlük istek sınırına yaklaşınca alarm, Buffer düşünce hikâye harcanmaz (hazır üretim aynı
    videoyu yayınlar); workflow'ta sırlar yalnız Üret adımında, ubuntu-24.04 sabit (ubuntu-latest 10-19'da 26'ya
    geçiyor), 11:37 ve 21:37 yedek cron, artifact adı deneme numaralı ve 4 gün (depo 360 MB'a çıkmıştı).
  - Kalite: onarım istemi rivayeti "reportedly" ile işaretler, desteksiz sıfatı siler; hakem işaretli rivayeti kabul
    eder (`f8d7074`; 10-11/12 düşüşlerinin çoğu bu iki türdü).
  - Karakter referansı (`606f077`): flux-2-klein `input_image_0..3` (+5,37 neuron/görsel); ana karakterin ilk karesi
    sonraki sahnelerine referans. `referans = true` S14 (`spikes/s14_referans.py`) ölçülene kadar kapalı.
  - Bağımsız inceleme (diff + kabul kriteri, bağlamı görmemiş alt ajan): 3 yüksek, 3 orta bulgu, hepsi düzeltildi.
    Yayın anı geçmiş planlanamamış video da onarılır ve pist doluyken de bakım koşusu yapılır (iş var mı adımı
    `planlanamayan`a bakar); onarım üretim klasörü varsa metadata + yerelleştirme + altyazıyla; çeviri onarımı
    `ceviri_onarim` tablosuyla bir kez, tutmayan deneme de sayılır; Buffer gönderisi açılıp sonucu okunamazsa
    (`GonderiBelirsiz`) hikâye harcanır (ikinci kopya gönderilmez); buffer/api'de Plan B paketi konmaz (otomatik
    yeniden yayınla çift çıkardı); artifact penceresi 12 koşu (~3 gün = pist). 187 test.
  - Bilerek açık bırakılanlar: OCR'ın son karede bıraktığı yazı kabulü durdurmaz (daha az yazılı kare seçilir);
    render hatası hikâye değil altyapı hatası sayılır (hikâye harcanmaz, alarm); iş 45 dk zaman aşımına düşerse
    durum commit'i kaybolabilir (Buffer'a gitmiş video ile; çok nadir, koşu ~6 dk).
- **İkinci denetim (2026-10-13 gece, Scryne aynı isteği tekrarladı):** ilk turun kesitinden farklı dört bağımsız
  inceleme (orkestrasyon + iş akışı, hikâye hattı, yayın + analitik, eski kod + test + belge kayması), ~60 bulgu;
  doğrulananlar düzeltildi. Yeni testler (`tests/test_denetim2_*.py`, `test_hikaye_uctan_uca.py`) düzeltme öncesi
  koda karşı koşturuldu: 34'ün 32'si eski kodda düştü (kalan 2'si kapsama testi). 187 → 224 test.
  - Çift video riski: Buffer gönderisi açıldıktan sonra kopan bağlantı/yarım JSON/`post: null` ham istisnaydı,
    "gönderi açılmadı" sayılıp hazır üretim aynı videoyu yeniden gönderiyordu → hepsi `GonderiBelirsiz`. Belirsiz
    gönderinin yetimi analitikte başlıkla bulununca pist denetimine girer (slot sessizce kayboluyordu). "Durumu
    kaydet" adımı `bash -e` altında beş denemeyi hiç yapmıyordu; `durum/` çakışmasında koşunun sürümü + alarm
    (gerçek git senaryosuyla sınandı). Üret adımının kendi süre sınırı (33 dk): iş zaman aşımında kayıt adımı koşar
    (ilk turun "bilerek açık" maddesi kapandı).
  - Hikâye: aynı karakterin ikinci değişimi (taç) ilkinin (kuyruk) denetimini kapatıyordu, bir değişimin geçmesi
    aynı karenin öbür hatasını siliyordu, OCR'ın yeniden çizdiği kare görünüş için sorulmuyordu → görünüş birikir,
    kare başına bütün sorular, OCR sonrası yeniden soru. Senaryo `bicim` imzasıyla sürdürülür (K-24 öncesi masal
    senaryosu artifact'tan dönebilirdi; eski mood render'dan sonra koşuyu düşürürdü). Hakem açılış kalıbını görür,
    kadro tarifindeki yazı taşıyan nesne düşer, Cloudflare 400'ü yeniden denenir, kesinti hikâyeyi havuzdan yakmaz.
  - Pist ve onarım: kayıp ya da kalıcı hatalı video (3 deneme) her cron'u bakım koşusuna çevirmiyor; onarım video
    başına kaydedilir (çift altyazı yok); çeviri onarımı en yakın yayını önce alır ve pist dolu günde bakım koşusu
    açar (10-15 Earth videosu bu yolla onarılır). K-14 penceresi formatın ilk public videosundan.
  - Test ve CI: testler kabuktaki `OTOMAT_KANAL=earth`'le 5 yerde düşüyordu (conftest ezer); `uretim.uret` ve
    hikâye modunda `main()` ilk kez testte; CI üretimle aynı imajda (ubuntu-24.04) ve ses/OCR ekleriyle; Pillow açık
    bağımlılık; canlı koşu arşiv veri motorunu (28 modül + matplotlib) artık yüklemiyor.
  - Belgeler: Final-Doküman'a "Güncel mimari" (hikâye motoru), kökte README, kök `DESIGN.md` arşiv notu.
  - Bilerek açık: satır başındaki uydurma ad kod kapısından geçer (her cümle başı kelimesini sormak Earth'ün zaten
    düşük geçme oranını yanlış alarmla düşürürdü; hakem adları denetliyor); yazıyla yazılmış sayı sayı sınırına
    girmez; Latin dışı uydurma yazı OCR'da sayılmaz; portföyün API birimi tahmini onarım ve marka çağrılarını içermez.
- **Faz 14 ✅ (2026-10-14):** kapanış incelemesi, iki denetimin düzeltmelerinden sonraki ilk üretimlerle.
  - Kanıt: Earth "Heraclitus" (10-15, 10-13'te incelendi) ve "Ganesha" (10-16); Orbit yeni formatta (K-24) "Monkey As
    King" (10-15, `EyLJf022flw`) ve "Crow And The Pitcher" (10-16, `qFQ0QRFW4IY`). Senaryo kaynakla tutarlı, ses
    -14,8/-15,2 LUFS, tepe -1,0 dBFS, 24-32 sn, altyazı vurgusu yerinde. 10-13 akşam ve 10-14 koşuları iki kanalda
    `tamam`, alarmsız. 237 test, CI yeşil.
  - Karelerde kalan kusurlar (yayında kalıyor, Drag Nun emsali): Ganesha 4. sahnesi 4 panelli çizgi roman sayfası;
    Monkey'nin taç sahnesinde iki tilki; Crow'un içme sahnesinde üç ayaklı karga, testi kareden kareye toprak/metal.
  - **Panel kapısı (`74c382d`):** 164 benzersiz sahnenin (artifact'lar + yerel) gözle taramasında 4 panelli kare:
    Ganesha, Mónica Macías (10-13, yayında, son sahne iki panel), Molasses (10-08), Curse of the Colonel (reddedilmişti).
    Ganesha'nınki tarifin kendisinden ("Three separate temples in different settings"); öbür üçü zaman sıçramalı son
    sahne ("now an adult", "Modern summer street"), dünya cümlesi eski dönemi söylerken.
    - `panel.py`: kenar kırpılmış karede iç bölgede kare boyu uzanan düz bant, iki yanında resim. 4/4 yakalandı, 160
      panelsiz karede yanlış alarm 0 (eşiğe en yakın iki panelsiz kare testte). Neuron harcamaz.
    - Panelli sahne yeni tohumla, dünya cümlesi düşmüş + "tek sürekli resim" istemiyle yeniden çizilir (sahne başına 2,
      video başına 3); yine panelliyse video çıkar, `meta.json` `panel.son`.
    - Senaryo: görsel kuralı tek mekân ister (biçim imzası değişti: kayıtlı yarım senaryolar yeniden yazılır); çok
      mekânlı tarif görsel onarımına gider.
    - Açık: S15 (`spikes/s15_panel.py`) yeniden çizimin gerçekten tek kare verdiğini canlı ölçecek. 10-14 sabahı kota
      doluydu (kayan pencere, gece koşuları). Tutmazsa panel `son`a kalır, video yine çıkar.
  - Test hatası: iki pist testi saat 13:00 UTC'den önce düşüyordu (slot "ilk boş gün", bugünün slotu boş). CI akşam
    koştuğu için görülmemişti; test bugünü de planlı kurar.
- **Faz 13 (2026-10-09):** `otomat/portfoy.py` + günlük iş akışında `portfoy` işi (kanal işlerinden sonra, günün ilk
  koşusunda). Kanallar yan yana: üretim, kanala çıkan, düşen/kota/hata, görüntüleme, abone, havuz, neuron, Buffer
  isteği, YouTube API birimi (tahmin), Actions dakikası (GitHub API, kanal işine göre bölünür); K-14 öldürme kriteri
  kanal başına (ilk public + 56 gün; Earth 12-05, Orbit 12-04) ve paylaşılan kotaların en yoğun günü. Kanal raporları
  sayılarını `YYYY-HWW.json`'a yazar (token yalnız kanalın kendi işinde). H41 verisiyle yerelde üretildi. Bitti: ilk
  portföy raporu (H41) repoda.
  - **Kapandı (2026-10-12):** ilk portföy raporu günlük iş akışının `portfoy` işinden geldi (`38e8308`,
    `raporlar/portfoy/2026-H41.md`): iki kanal yan yana, K-14 karar günleri, paylaşılan kotaların en yoğun günü.

### Faz 10–13: Çok kanal (2026-10-06)
- **Neden:** Scryne: "farklı kanallarda farklı konulu kanallar… projeyi en üst seviyeye çıkaracak her şey, tamamen sana
  bırakıyorum." Araştırma, sınırlar ve kararlar: `docs/arastirma/07-cok-kanal.md` (K-10…K-14).
- **Sınırlar:** en çok 3 kanal (Buffer Free 3 kanal; API kotası kanal başı ~2.050 birim/gün; Actions ~420 dk/ay/kanal).
- **Asıl risk:** kanal kümesi cezası (ortak şablon/takvim/altyapı). Önlem: kanallar konu, veri, şablon, kimlik, ses,
  saat ve adla ayrışır; birer birer açılır.
- **Faz 7 ile ilişki:** "14 gün kod müdahalesiz" Earth'ün üretim davranışı için geçerli. Çok kanal işi Earth'ün
  çıktısını değiştirmemeli (test_kanal: eski yollar, kaynaklar, saat, ses; kanca istemine kanal tanımı eklendi, tek
  bilinçli değişiklik). Earth'ün çıktısını değiştiren bir commit Faz 7 sayacını sıfırlar.
- **Faz 10 durumu (2026-10-06):** `cok-kanal` dalı; 62 → 73 test; dal üzerinde iş akışı elle tetiklendi (matris,
  "bugün üretildi mi" adımı kanal başına doğru çalıştı, yayına dokunmadı). Main'e birleşme: 10-07 Earth koşusu Faz 6
  sayacını kapattıktan sonra. (Güncelleme: Earth yerelde tam koşuyla doğrulanınca aynı gece birleşti.)
- **Faz 11 notları (2026-10-06):**
  - JPL CAD çap vermiyor (24/24 kayıtta boş): çap H'den, p = 0,25–0,05 aralığıyla; videoda "estimated" ve aralık.
  - Exoplanet Archive: yalnız transit + ölçülmüş yarıçap. İlk taslakta "en yakınlar" listesinin ilk ikisi aynı yıldızın
    gezegenleriydi (sistem başına tek gezegen), "en kısa yıl" gün cinsinden eşitlendi (saat), "en büyük" listesinin
    tepesi ~2,5 Jüpiter (şüpheli ölçüm, liste çıkarıldı). Sıralamalar kapsamını söyler: "planets seen crossing their star".
  - Windows'ta Python sistem deposu JPL zincirini doğrulayamadı → `http.py` certifi ile.
  - Şablon kare kontrolü üç tur: yollar başlığa taşıyordu (dış halkaya kırpıldı), boyut panelinde eksen oranı daireyi
    yatay şeride çevirdi (piksel oranlı elips), küçük gövde adları üst üste biniyordu (piksel ofsetli etiket).

- **Kanal açıldı (2026-10-06 gece):** Scryne K1+K2'yi aynı gün yaptı (eski hesap, risk düşük), K3 da aynı gece: Orbit Ruler
  `UCbhRAMbzhwX7dqoBJhCcm2g` (`@orbitruler`), Buffer kanalı `6ac549856a5c39ccb634a0b1`, token kanal doğrulamasından geçti,
  `YT_TOKEN_JSON_UZAY` + `OTOMAT_YAYIN_UZAY=buffer`. Dal üzerinde matris koşusu (iki iş yeşil, alarm yok): ilk video
  `M1z_ITgDASs` Orbit Ruler'da private, publishAt 2026-10-07T20:00Z, 5 yerelleştirme, 5 altyazı izi (+ YouTube ASR).
  Aynı gece: Earth için yerel tam koşu (gerçek DB kopyası, teslim modu) yeni kodla geçti (aynı seçim
  `usgs:bolge_yillik:Japan`, 4 dil, alarm yok, yerleşim aynı) → dal main'e alındı (`cd0337b`, CI yeşil).
  Marka kiti (`docs/marka/uzay/`): teğet cetvel sembolü; banner + açıklama (5 dil) + anahtar kelime API ile.
  Açık: (profil resmi + filigran ✅ Scryne, 10-07) 07.10 23:00 TR oturumsuz public kontrolü;
  Faz 10 ✅ için main'de iki kanallı ilk temiz günlük koşu (07.10).
- **Faz 11 ✅ (2026-10-07 20:10 UTC):** ilk video `M1z_ITgDASs` ("The Closest Asteroid Flybys of the Week") oturumsuz
  oEmbed ile public (200, yazar Orbit Ruler). Bu video etiket düzeltmelerinden önce üretildi; ikinci video `rUEu2ssQwIg`
  (08.10 20:00 UTC) planlı, 403 beklenen. Faz 12'nin koşulu (K-13: kanal 2'nin ilk 7 günü alarmsız) 10-14'te dolar.
- **Bulgu (2026-10-06, tüm kanallar):** `uretim.birlestir` `-shortest` ile sesin bittiği yerde kesiyor; tasarlanan
  1,2 sn kapanış karesi (`KUYRUK`) hiçbir videoda yok (Earth dahil). Düzeltme (`apad`) Earth'ün çıktısını değiştirir:
  Faz 7 bitince ya da bilinçli bir Earth değişikliğiyle birlikte yapılacak.
  **Yapıldı (2026-10-07, `f080e42`):** `apad=pad_dur=KUYRUK` + gerçek ffmpeg testi; Faz 7 sayacı henüz başlamadığı için
  sayaç sıfırlanmadan main'e alındı. Aynı birleşmede `yakin_gecis` etiketleri çakışmasız yerleşiyor (9 geçişli kare
  gözle kontrol edildi). Aynı akşam (yalnız uzay): kırpma çemberinde biten komşu yol ucu etikete değiyordu (TQ1 → TX,
  sonra TA → TX): maliyet yolu sık örnekler, boşluklu kutuyla bakar, herhangi bir değme sabit ceza alır; ara kaydırma
  adayları ve halka etiketine aşağı açılar eklendi. 9/6/3 geçişte her yazı her yoldan ≥ 6 px (`test_..._yaziya_degmez`).
- **Faz 10 ✅ (2026-10-07):** main'de iki kanallı ilk planlı koşu (13:34 UTC) iki iş yeşil, alarmsız; Earth seçimi ve
  yerleşimi eski davranışla aynı (`usgs:bolge_yillik:Argentina`, `L2ar7ULV7Ic`), Orbit Ruler `rUEu2ssQwIg` planlı.

### Faz 16: Kart biçimi ve izlenme deneyi (2026-10-14)
- **Neden:** Scryne: "videolar neden izlenmiyor… yanlış mı ilerliyoruz?" Earth'ün public 4 hikâyesi 45, 81, 4, 3 izlendi;
  izlenmelerin %25-38'i ilk saniyeleri geçti. Aynı nişte küçük kanalların tipik videosu 23-125 bin. Kanıt, rakip
  taraması, politika ve karar: `docs/arastirma/10-rakip-kart.md` (K-25).
- **Yapılan (10-14):**
  - `otomat/hikaye/kart.py`: kart metni (gpt-oss; kanca + 3-5 cümle, `[[vurgu]]`), kod kapısı (sayı/ad kaynakta, yıl
    sayı sınırına girmez, vurgu sayısı ve uzunluğu, kelime), olgu hakemi, en çok 4 tur onarım; görsel: makalenin
    Commons ana görseli (serbest lisans, raster, ≥ 400 px, OCR'da ≥ 40 harf = belge → elenir), yoksa tek AI
    illüstrasyonu (panel/yazı çıkarsa bir kez yeniden); 8 sn render (cos zoom, döngüde sıçrama yok), müzik -16 LUFS.
  - Kabul kart dalı (cümle/kelime/kanca, Wikimedia atfı, tek görsel, 5-12 sn); çeviri altyazısız (srt yok, başlık ve
    açıklama 4 dile). Haftalık raporda video başına "Kalan" (engaged / görüntüleme) ve kanal oranı.
  - Testler 237 → 260 (`test_hikaye_kart.py`; iki testin bozuk koda karşı düştüğü elle denendi). Yerel uçtan uca
    (metin modeli sahte, kota kapalıydı): Molasses ve Dancing plague gerçek Commons görseliyle kabulden geçti, Tarrare'nin
    belge görseli elendi.
  - Test izolasyonu açığı: senaryosu sahtelenmiş bir test kart yoluna sapıp yerelde gerçek Cloudflare'e istek attı
    (`cf.kimlik` `sirlar/cloudflare.json`'a düşüyordu; CI'da dosya yok). `conftest` artık Cloudflare, YouTube ve
    Buffer kimliklerini testte kapatıyor.
- **İlk kart (10-15 koşusu, 10-17 slotu, `BpF0N2oblvg`):** Hobby Lobby kaçakçılık skandalı; kod kapısı ve hakem ilk
  turda temiz, olgular Wikipedia'yla tutarlı, 8 sn. Makalenin Commons görseli yok, AI illüstrasyonu (mağaza koridoru;
  tarifteki tabletler çizilmemiş, bir kez yeniden çizildi). Bulunan üç hata düzeltildi:
  - Çeviri kartta hiç çalışmıyordu: altyazı listesi boş, "çevrilmemiş çıktı" kontrolü `[] == []` ile dört dilin
    dördünü reddetti. Boş listede kontrol yalnız başlık/açıklamaya bakar; istem cümle bölümünü sormaz.
  - Çeviri onarımı kartta her dil için srt arayıp "altyazı yüklenemedi" alarmı çalacaktı; `en.srt` yoksa srt
    adımı atlanır. 10-17 videosunun dört dili bir sonraki koşuda bu yoldan tamamlanır.
  - Model `[[ $1.6 million]]` yazıyor, açıklamada çift boşluk kalıyordu: işaret içi kenar boşluğu atılır.
  - Çeviri istemi: "yer adlarını aynen koru" Almancada "UAE dealers", "US customs" bırakıyordu; rakam ve hashtag
    aynen, gerisi (million, yer adı) hedef dilde. Canlı es/de/fr denemesi temiz.
  - Bugüne sabitlenmiş pist testi (10-14 slotu) 10-15'te düştü; gerçek saate göreli yapıldı. 260 → 263 test.
- **Yayında kalan sahneli Earth videoları:** Bartman (10-14), Heraclitus (10-15), Ganesha (10-16). Kıyas tabanı.
- **Üçüncü denetim (2026-10-15, Scryne: "eksikliklerin ve hataların tamamını çöz"):** dört bağımsız inceleme (kart
  biçimi, orkestrasyon + iş akışı, hikâye hattı, yayın + analitik), ~46 bulgu; doğrulananlar düzeltildi. 263 → 307
  test; yeni 44 testin 44'ü eski kodda düşüyor (`tests/test_denetim3*.py`).
  - Canlı bulgu: Ganesha'nın (`CgRlUjXj9F8`, 10-16) fr/pt altyazıları 10-14'te YouTube kotasına takıldı (iki kanal tek
    Cloud projesi = günlük 10.000 birim; o gün elle marka işi de vardı); alarm çaldı ama hiçbir koşu yeniden
    denemiyordu. Artık düşen iz `altyazi_eksik` kuyruğuna girer, kota dolunca kalan diller denenmez, sonraki koşu önce
    videonun izlerini okuyup (çift iz açmadan) tamamlar; 3 kota dışı hatadan sonra alarmla vazgeçer. Ganesha'nın iki
    dili kuyruğa elle yazıldı. Alarm satırı HttpError'un nedenini taşır (`HttpError 403 quotaExceeded`; eskiden 200
    karakterde kesilen URL'ydi). Koşunun ölçülmüş YouTube birimi günlük kayıtta (`yt_birim`), portföy tahmin yerine onu
    kullanır (tahmin kartta da 5 altyazı sayıyordu).
  - Kart (10-17 Hobby Lobby karesi incelendi): AI görseli dikey çiziliyor, bant yatay olduğu için %70'i kırpılıyordu;
    konunun kendisi (masadaki tabletler) karede yoktu → kart görseli yatay 1344×768, istem "konu ortada" (canlı
    denendi). Atıf satırı görsel bandının içine (eskiden Shorts arayüzünün altında, uzun yazar adı kesik). İşarete
    bitişik yazı ayrılıyordu ("Lobby 's"); iç içe/bozuk `[[ ]]` ekrana parantezle çıkıp kabulden geçiyordu; onarım cümle
    ekleyip silemiyordu (iki öğeye sıkışmış kart dört turu boşa yakardı); 3 kelimeden kısa cümle ve ekrana sığmayan
    paragraf ancak render'dan sonra düşüyordu (artık kod kapısında). Lisans süzgeci CC BY-NC/ND'yi geçiriyordu; atıfta
    lisans bağlantısı ve "cropped" notu yok, "Unknown photographer; restored by X" yazarı boş kalıyordu; saydam PNG
    siyaha dönüyordu. Çeviri `captions: [""]` döndürünce kartın dili düşüyordu. Hazır üretim eski biçimin (sahneli)
    yayınlanmamış videosunu kart deneyine karıştırabiliyordu. Müzik döngüsündeki sönme 0,7 → 0,25 sn.
  - **Earth `donem` 10-17** (ilk kart): haydut ödülleri ve K-14 sayacı 8 sn kartları 30 sn sahneli videolarla
    karıştırmasın (Orbit K-24 gibi). **Earth K-14 karar günü buna göre kayar (~12-11).**
  - **"Kalan" uyarısı:** Shorts görüntülemesi 2025-03'ten beri her yeniden oynatmayı sayar, engaged saymaz; döngüye
    giren 8 sn kartta Kalan olduğundan düşük görünür. Faz 16 kararı Kalan'la birlikte ortalama izlenme %'sine de bakar
    (%100'ü aşıyorsa izleyici kartı döndürüyor); rapor bunu tablonun altına yazar.
  - Orkestrasyon: Üret adımının 33 dk sınırı Buffer beklemesinin ortasına düşerse kayıt yoktu, sonraki koşu aynı videoyu
    yeniden gönderirdi → Buffer id'yi verir vermez kayıt (+ planlama onarımı işareti), SIGTERM `finally`'leri koşturur,
    koşu kesilince hikâye harcanır; 12 dk'yı geçen koşu ikinci videoya başlamaz. Bakım koşusu (rapor, onarım) havuz,
    kimlik ve Buffer sınırına bakmadan açık alarmı kapatıyordu → yalnız alarmsız tam koşu kapatır. Kayıt adımı
    `raporlar/` çakışmasında hiç kaydetmiyordu. İş düşünce Python'un alarmına iş durumu eklenir. Önceki artifact'lar
    koşu sayısıyla değil son 4 günle seçilir. Artifact'ı olmayan ya da çevirisi hep düşen video her cron'u yayınına
    kadar bakım koşusuna çeviriyordu → 3 denemede vazgeçilir. Repo değişkeni yoksa kanal sessizce teslim moduna
    düşüyordu → alarm. Dal denemesi main'in eşzamanlılık grubunu paylaşıyor ve kanal kimliğini yazıyordu. uv sürümü
    sabit (0.13.1).
  - Yayın: medya Pages beklemesinde düşünce public repoda kalıyordu; **otomat-site tarihçesi** her videoyu (geri
    çekilenler dahil) tutuyordu, 10 günde 294 MB (Pages sınırı 1 GB, ~1 ayda dolacaktı) → medya klasörü boşaldıkça dal
    tek commit'e sıkıştırılır (kira korumalı force push; gerçek git ile sınandı). Buffer yoklamasında tek GraphQL
    hıçkırığı gönderiyi "belirsiz" yapıp hikâyeyi harcıyordu (artık üst üste 3). `<` `>` YouTube metninde 400 verip
    planlamayı düşürürdü (Commons yazar alanı). Haftalık rapor pazartesi yazılıyordu, Analytics son 2-3 günü eksik
    sayıyordu → hafta bitimi + 3 gün; "Konu" sütunu haydudun kolunu, "düşen" kota koşusunu saymaz. Site sayfaları tek
    kanal ve veri videoları anlatıyordu (Google API politikası doğru beyan ister) → iki kanal, kaynaklar, AI üretimi,
    Buffer, kanal ayarları; `yayin-oncesi` taraması temiz.
  - Hikâye hattı (Orbit): bir sahne filtreye takılınca öbürleri çizilmeye devam ediyordu (~470 neuron boşa); stil
    değişince sürdürülen senaryo her koşu kareleri yeniden siliyordu; yeniden çizilen kare panel/OCR denetiminden
    geçmiyor, panel yeniden çiziminin istemi sonraki çizimlerde geri geliyordu, ikinci görünüş turunun tohumları ilkiyle
    çakışıyordu. Ad kapısı Unicode adları ("Pérez"), unvandan sonrakini ("Dr. X") denetlemiyor, aksanı farklı yazılmış
    gerçek adı reddediyordu. Son 24 saatte düzenlenmiş makale anlatılmaz (vandalizm/istem enjeksiyonu her denetimden
    geçerdi), havuzdan da düşmez. "bullshit" gibi bitişik küfür süzgeçten geçiyordu. Uzun tire tek başına kelime
    oluyordu. Cloudflare yeniden denemesi üstel. Boş cümle listesi kabulü çökertiyordu.
  - Bilerek açık: YouTube kotasının iki kanal arasında önceden bütçelenmesi (ölçüm artık var; kuyruk ve pist onarımı
    kota taşmasını karşılıyor); bakım koşularının neuron/Buffer harcaması günlük kayda yazılmıyor; Wikipedia metni
    revizyona sabitlenmiyor (24 saat süzgeci yetiyor sayıldı).
- **Yayın öncesi kart incelemesi (2026-10-17):** 10-16 ve 10-17 koşuları (iki kanal, 4 koşu) alarmsız; iki kanalda
  pist 10-19'a kadar dolu, hepsi 4 dilli. Hobby Lobby (`BpF0N2oblvg`) 14:00'te yayında, 5 dil
  yerelleştirmesi canlıda doğrulandı. Zelda (10-18, ilk Commons görselli kart: yatay bant ve bant içi atıf doğru) ve
  Montauk (10-19) karesi ve olguları Wikipedia'yla karşılaştırıldı, tutarlı.
  - Bulgu: Montauk kartı "**The article** speculated…" diyor; makalenin kendi cümlesi ("The light-hearted article",
    bir gazete yazısı) taşınmış, izleyici hangi yazı olduğunu bilmiyor. Hakem olgu olarak doğru buldu. Kod kapısına
    `senaryo.kaynak_gondermesi` (kart + sahneli): "Wikipedia", "this article", "according to the source" ve önce bir
    yazı anılmadan "the article/report". Eldeki 16 geçmiş senaryoda yalnız Montauk'u işaretliyor. Video bırakıldı
    (kusur anlamı bozmuyor; geri çekmek deneyden bir slot alırdı). 307 → 311 test.
  - Gözlem: anlatıcısız kartta YouTube'un otomatik altyazısı müziği Vietnamca sanıyor (`asr`, `vi`); videonun
    `defaultAudioLanguage` değeri `en`. Silinemez (asr), etkisi altyazıyı açan izleyiciyle sınırlı; dokunulmadı.
  - **Takvim:** ölçüm penceresi yayın günü + 2 gün, üstüne 2 gün Analytics gecikmesi. 10-17 kartı 10-22'de, beşinci
    kart (10-21) 10-26'da ölçülür; **Faz 16 kararı ~10-26.** Kıyas tabanı canlıda: Bartman (sahneli) 3 günlük
    pencerede 200 görüntüleme, %31,5 Kalan, %50,5 izlenme.

- **K-33 Shorts tek kanala indi (2026-10-18, Scryne: "shorts kanallarını ya kapatalım ya da 1 tanesiyle
  ilerleyelim"):** son 28 gün Earth 662 görüntüleme / 3 abone (son 8 video 5-388, medyan ~55), Orbit 158 / 0 (son 8
  videonun beşi 0-3). **Orbit (Lanternbug Tales) durdu:** günlük matristen ve yayın kontrolünden çıktı, profil ve token
  duruyor, Buffer'da planlı son videolar yayına çıkar, kanal silinmedi. **Earth tek Shorts kanalı:** kart deneyi 10-26
  kararına kadar sürer; oran tutmazsa Earth de durur ve Shorts emeği One Ticket Back'te film kesitlerine (aynı kanalda
  uzun videoya abone çeken dikey fragmanlar) gider.

### Faz 17: Uzun animasyonlu hikâye (2026-10-17)
- **Neden:** Scryne: "shorts yerine bu tarzda [Day One Films] bir kanal büyütsek… normal videolar… çok profesyonel olmalı;
  tarihi figürler, yaşanmış ilginç olaylar, bir karakterin macerası." Araştırma, kararlar (K-26…K-30) ve pilot ölçümleri:
  `docs/arastirma/11-uzun-video.md`.
- **Yapılan (10-17…10-18):** `otomat/film/` (Shorts motorundan bağımsız, yerel GPU): senaryo JSON'u ve denetimi, FLUX.2
  klein karakter kartı + `ReferenceLatent` sahneleri, Wan 2.2 TI2V-5B klipleri, Chatterbox anlatım (Kokoro'dan sentetik
  referans ses) + parça başına Whisper kapısı, PIL/ffmpeg kurgu (kamera, tarih damgası, bölüm kartı, bitiş payı, müzik
  yatağı), kapak, bölümlü açıklama. `tests/test_film.py` 23 test; toplam 330 → 334.
- **Pilot (Violet Jessop) ✅ üretildi ve doğrulandı (10-18):** 7:42, -14,4 LUFS; bitmiş videonun sesi Whisper'da %0,8
  kelime farkı, bütün sayılar tutuyor; 96 sahnenin hepsi ve 21 klibin hepsi kare kare incelendi. Üretimde bulunan altı
  kusur sınıfı (bellek, Wan'ın yüz bozması ve kadraja nesne sokması, yan karakterlerin gerçekçi çizilmesi, TTS'in yılı
  yanlış okuması, okunmayan damga) kalıcı düzeltildi; ayrıntı araştırma notunda.
- **Film 2 (Klondike) ✅ üretildi ve doğrulandı (10-18):** K-31 biçimi ("What if you…", İngilizce), 10:38, -14,4 LUFS,
  bitmiş videonun sesi %1,7 kelime farkı ve bütün sayılar tutuyor; 103 sahne ve 19 klip incelendi (33 klibin 14'ü
  bozuktu). Karakter tarifi istemde, sayı kapısı yanlış alarmları düzeltildi; 334 → 338 test.
- **Kalan (Bitti kriteri):** K-30 yükleme denemesi (ayrı gün, hesap temkini); pilotun yayını; ikinci ve üçüncü film
  farklı yapıda. Süre: pilot 8 dk alt sınırının altında kaldı, sonraki senaryolar ~1.500 kelime.

### Faz 7: Gerçek kullanım
- **İşler:** 14 günlük koşu; Scryne'ın dokunuş süresinin kaydı; her gün kapı/yükleme sonuçlarının raporu.
- **Sayaç:** Faz 16'nın kararıyla oturan biçimin ilk günlük koşusuyla başlar. (10-14 sabahı "Faz 14 kapanınca başlar"
  yazılmıştı; aynı gün veri, izlenmeyen biçimi 14 gün dondurmanın kayıp olduğunu gösterdi: K-25.) 14 gün boyunca
  çıktıyı değiştiren commit sayacı sıfırlar; hata düzeltmesi ve ölçüm sayılmaz.
- **Bitti Kriteri:** "bitti = kullanıldı" cümlesi.
- **Notlar:**
  - **Kanal kimliği (2026-10-04):** `docs/marka/` — profil resmi, banner, filigran, favicon, logo varyantları (logo-design
    skill'i; şeritli dünya + taşan turuncu bant). Studio'ya yükleme Scryne'da; nereye ne gittiği `docs/marka/README.md`.
  - **Kanal ayarları ✅ (2026-10-06, Scryne):** profil resmi, banner, filigran; açıklama EN + ES/PT/DE/FR; anahtar
    kelimeler; düzen (Kısa videolar bölümü); yükleme varsayılanları (gizli, Bilim ve Teknoloji, EN); topluluk filtresi.
    API'den doğrulandı: açıklama, 5 dil, anahtar kelimeler, banner, profil resmi. Ülke bilerek boş. Açık: oynatma
    listeleri (Earthquakes / World Rankings / Europe by Country) ertelendi; kanalda yanlış adlı tek liste duruyor.
    Kanal düzeyindeki ayarların Shorts önerisine etkisi zayıf; asıl risk YouTube'un "inauthentic content" politikası
    (şablonla seri üretim) → Faz 8 değerlendirmesinde videoların birbirinden ne kadar farklı olduğuna bakılır.
  - **AgentTube karşılaştırması (2026-10-04, darkzOGx/youtube-automation-agent):** kod alınmadı (README'de memecoin
    adresi, Gemini'ye video ürettiriyor). İki fikri zaten bizde: "doğrulanmamış iddia yayını durdurur" = anlamsal hakem +
    politika kapısı (Faz 4); "yeniden seslendirmede sahne süresi sesten gelir" = cümle başına Kokoro, süre sesten (Faz 4).
    Medya hakkı kapısının karşılığı açık veri + açıklamadaki `Data:`/`Source:` atfı (`uretim.py`).
