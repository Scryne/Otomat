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
| 5 | Yayın ve audit | 🔄 Devam Ediyor | Scryne D1–D3'ü yaptı; OAuth "In production"; yükleyici + planlama + 5 dilli metadata + altyazı; GitHub Pages'ta uygulama/gizlilik/şartlar; audit başvurusu gönderildi; ilk video gerçek kanalda (private-kilitli olsa bile); Plan B paketi çalışıyor |
| 6 | Geri besleme ve işletim | 🔄 Devam Ediyor | Analitik toplayıcı; faktörlü Thompson sampling (konu, kanca); günlük cron 3 gün kesintisiz; haftalık rapor; `invalid_grant` ve koşu hatası alarmı |
| 7 | Gerçek kullanım | ⏳ Bekliyor | Final-Doküman'daki "bitti = kullanıldı" cümlesi gerçekleşti (14 gün, kod müdahalesiz); bulgular roadmap'e işlendi |
| 8 | Öldürme kriteri değerlendirmesi (tetiklemeli) | ⏳ Bekliyor | İlk public videodan 8 hafta sonra: son 56 günde ≥ 1,2M Shorts izlenmesi veya ≥ 200 abone ölçüldü; karar (sürdür / konsept değiştir / kapat) yazıldı |
| 9 | Reels ve görsel kolları (koşullu) | ⏳ Bekliyor | Faz 8 "sürdür" derse: aynı videolar Facebook/Instagram Reels'e; medya motorundan stok görsel kolu |

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
- **Notlar:**
  - `gh issue list --label alarm` etiket yokken 1 ile çıkıyor; Actions `bash -e` ile koştuğu için etiket önce `--force`
    ile oluşturulur (yerelde sınandı).
  - Ödül mutlak izlenme değil komşu sırası: büyüyen kanalda her yeni video eskisini geçer, bu konu/kanca başarısı değil.

### Faz 7: Gerçek kullanım
- **İşler:** 14 günlük koşu; Scryne'ın dokunuş süresinin kaydı; her gün kapı/yükleme sonuçlarının raporu.
- **Bitti Kriteri:** "bitti = kullanıldı" cümlesi.
- **Notlar:**
