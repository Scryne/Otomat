---
proje: Otomat
created: 2026-10-02
type: final-dokuman
status: onaylandi
---
# Otomat — Final Doküman

Kaynak: `docs/Proje-Fikri.md` (denetlendi, D-1…D-10 ve K-1…K-8), `docs/arastirma/01–04`, `spikes/`.
Scryne yetkiyi devretti ("her şeyi sana bırakıyorum", 2026-10-02); kararlar bu yetkiyle kapandı.

## Özet

Otomat, sıfır sermayeyle çalışan otomatik gelir botlarının şemsiyesidir. İlk kol **Shorts fabrikası v2**: açık
veriden (USGS, World Bank, Eurostat) olgu paketi çıkarır, olguyu kod şablonuyla cümleye, merak çerçevesini yerel
bir LLM ile kancaya çevirir, kodla harita/grafik animasyonu üretir, yerel TTS ile seslendirir, anlamsal hakemden
geçirip YouTube'a beş dilli metadata ve altyazıyla yükler. YouTube Analytics'ten gelen geri bildirimle hangi konu
ve kancanın tuttuğunu öğrenir. GitHub Actions'ta her gün kendiliğinden çalışır; Scryne'ın haftalık yükü ≤ 10 dk.

> **Format değişimi (2026-10-08, K-15…K-24).** Veri videoları izlenmedi (3-63 izlenme); iki kanal da **kaynaklı,
> illüstrasyonlu kısa hikâye** kanalına döndü. Aşağıdaki "Güncel mimari" bölümü bugünkü ürünü anlatır. Ondan sonraki
> bölümler (stack, mimari şeması, kapsam, riskler) v1 veri videosu kararlarıdır: veri motoru silinmedi, arşiv profilleri
> (`kanallar/veri-earth`, `veri-uzay`) ve testleriyle duruyor. Gerekçeler: `docs/arastirma/08-format-hikaye.md`,
> `09-kanal-karari.md`; faz kayıtları `docs/Roadmap.md` (Faz 14–15).
>
> **Kart biçimi (2026-10-14, K-25).** Earth'ün sahneli anlatımı 3-81 izlenmede kaldı (izleyicinin %62-75'i ilk
> saniyelerde kaydırdı); nişte tutarlı izlenen küçük kanallar hikâyeyi anlatıcısız tek ekran paragrafla ve konunun
> gerçek görseliyle veriyor. Earth `bicim = "kart"`a geçti (`otomat/hikaye/kart.py`); sahne motoru Orbit'te sürüyor.
> Kanıt ve karar: `docs/arastirma/10-rakip-kart.md`, Roadmap Faz 16.
>
> **Uzun film (2026-10-17…10-23, K-26…K-35).** Otomat'ın tek yayındaki kolu artık **One Ticket Back**: haftada bir
> 8-11 dk anlatıcılı, animasyonlu tarih filmi ve her filmden 3 dikey kesit. Shorts kanalları durdu: Orbit K-33
> (10-18), Earth K-35 (10-23; kart biçiminde de izleyicinin ~%31'i kaldı, eşik %50). Shorts motoru ve profilleri
> silinmedi; geri açma tarifi `.github/workflows/gunluk.yml` başında. Aşağıdaki "Güncel mimari (film)" bugünkü ürünü
> anlatır; "hikâye motoru" bölümü durmuş Shorts hattının, ondan sonrakiler v1 veri videolarının kaydıdır.
>
> **Spor Shorts kanalı (2026-10-24, K-37; K-36'yı Scryne'ın kararıyla açar).** Scryne: "shorts kanalı açalım… gerçek
> görüntüler… anlatımlı… popüler şeyler (mma, futbol)"; sonra "herşeyi sana bırakıyorum, para kazanayım yeterli, günde
> 2-3 shorts". Sıfırdan yeni kanal **Arena Lore**, İngilizce; hikâye motorunun sahne biçimi, üç seri (futbol, mma,
> boks) üç profil, günde her seriden bir video. **Yayın görüntüsü ve fotoğrafı yok:** lisans yolu bulunamadı, talepli
> Short'un geliri hak sahibine gider, ihtar kişiye ve One Ticket Back'e uzanır (`docs/arastirma/13-spor-shorts.md`).
> Görsel grafik roman illüstrasyonu, sporcular adsız rol figürü. Kanıt ve faz: Roadmap Faz 19.

## Güncel mimari (film, 2026-10-23)

| | |
| --- | --- |
| Kanal | One Ticket Back (@OneTicketBack), İngilizce, ayrı Google kanalı (K-32: YPP incelemesi Shorts'la karışmasın) |
| İçerik | tek kişinin ya da olayın kaynaklı gerçek hikâyesi; iki çerçeve dönüşümlü: "What if you…" (ikinci tekil, K-31) ve kişi/olay (K-26) |
| Kaynak | Wikipedia'nın sabit revizyonu (`kaynaklar[].revid`); her cümle kaynakla satır satır karşılaştırılır (K-28) |
| Takvim | film cumartesi 19:00 UTC, kesitler filmden sonraki pazartesi/çarşamba/cuma 19:00 UTC (K-34) |

| Katman | Seçim | Not |
| --- | --- | --- |
| Senaryo | `filmler/<id>/senaryo.json` (bölüm → blok → sahne, karakterler, kesitler), `otomat/film/senaryo.py` denetimi | ~1.500 kelime / 8-11 dk |
| Görsel | yerel ComfyUI, FLUX.2 klein 4B: karakter kartı (sabit tohum) + `ReferenceLatent` sahneleri, 1920×1088 | koyu sinematik minimal 2D; karakter tarifi her istemde |
| Hareket | Wan 2.2 I2V-A14B GGUF Q3 + lightx2v 4 adım, 832×480 16 fps, sahnelerin ~%30'u | bozuk klip kare kare elenir, gerisi kamera hareketi |
| Anlatım | Chatterbox (referans ses Kokoro `bm_george`'tan), parça başına Whisper kapısı (kelime ve sayı) | bitmiş videoda Whisper farkı %0,5-1,7 |
| Kurgu | PIL afin kamera + ffmpeg, 1920×1080 24 fps; tarih damgası, bölüm kartı, Kevin MacLeod müziği (CC BY) | -14 LUFS |
| Kesit | `kesit.py`: tek bölümün ardışık blokları, dikey, ≤ 59 sn, açıklamada filmin bağlantısı | film başına 3 |
| Yayın | kendi API projemiz: `videos.insert` private + `publishAt`, `thumbnails.set` (K-30); `otomat/film/yukle.py` | kanal 24 saatte 10 video sınırı → günde bir film + 3 kesit, Windows Görev Zamanlayıcı |
| Ölçüm | `otomat/film/rapor.py`, Actions `film` işi, haftalık `raporlar/film/` (hafta bitimi + 3 gün) | gösterim ve tıklama oranı API'de yok, Studio'dan |
| Çalışma yeri | yerel laptop (RTX 4060 8 GB, 24 GB RAM), K-27 | üretim planlı oturum işi; yayın ve rapor kendiliğinden |

**Bitti = kullanıldı (film, Faz 7):** bir ayın 4 filmi + 12 kesiti planlandığı saatte, kaçan ve çift olmadan yayına
çıktı; haftalık film raporu 4 hafta üst üste kendiliğinden düştü; yayın ve rapor tarafında kod müdahalesi yok;
Scryne'ın dokunuşu haftada ≤ 10 dk. Biçim kararı Faz 18 (ilk üç filmin verisi, ~11-16), öldürme kriteri Faz 8
(12-19); ikisinin eşikleri Roadmap'te önceden yazılı.

## Shorts hikâye motoru (2026-10-13; durdu 10-23, K-35)

| Kanal | YouTube adı | İçerik | Kaynak havuzu | Ses | Yayın (UTC) |
| --- | --- | --- | --- | --- | --- |
| `earth` | Inkwell Oddities Stories | gerçek tuhaf olaylar, genel kitle (K-15); **kart biçimi** (K-25): 8 sn, anlatıcısız paragraf + makalenin Commons görseli | Wikipedia: Unusual articles, ~710 makale (TypeSafe jev-1.13.0 ile süzüldü, K-18) | Kokoro `bm_george` 1,08× | 14:00 |
| `uzay` | Lanternbug Tales | Ezop masalları yumuşatılmadan, yetişkinlere (K-24) | Aesop's Fables, V. S. Vernon Jones 1912 (kamu malı), 245 masal | Kokoro `af_heart` 1,02× | 20:00 |

| Katman | Seçim | Not |
| --- | --- | --- |
| Senaryo, hakem, satır onarımı, çeviri | Cloudflare Workers AI `gpt-oss-120b` (JSON şeması) | Bedava 10.000 neuron/gün, iki kanal ve yerel denemeler ortak, **kayan 24 saat** (docs/arastirma/09) |
| Sahne görseli | `flux-2-klein-4b`, 768×1344, sahne başına; kanal stili profilde | Earth suluboya-mürekkep, Orbit 19. yy gravürü |
| Kare denetimi | Piksel panel denetimi (`panel.py`) + `llama-4-scout` (değişen görünüş, evet/hayır) + RapidOCR (karede yazı) | Tutmayan kare yeni tohumla yeniden çizilir; panelli kare dünya cümlesiz istemle |
| Ses ve altyazı | Kokoro ONNX; faster-whisper `base.en` kelime zamanı | Anlatıcı −14, müzik −30/−28 LUFS; kelime vurgulu yakılmış altyazı + 5 dilde SRT |
| Render | PIL + ffmpeg (Ken Burns, sahne başına 5 kamera hareketi), Kevin MacLeod müziği (CC BY 4.0, mood'a göre) | 1080×1920, 20-60 sn |
| Yayın | Buffer (private yükler) + YouTube Data API (`duzenle`: plan, etiket, 5 dil yerelleştirme, altyazı) | Audit gerektirmez (docs/arastirma/06); video gönderim süresince `otomat-site/media/`'da |
| Durum | SQLite (`durum/<kanal>.db`), her koşu sonunda commit | Tekrar engeli, seçimler, pist, planlanamayan, çeviri onarımı, ölçümler |
| İşletim | GitHub Actions matrisi (kanal başına iş), günde 4 cron (1'i asıl, 3'ü yedek), alarm = GitHub issue | Haftalık rapor kanal başına, portföy raporu iki kanal yan yana |

Günlük akış (kanal başına, `otomat/gunluk.py`):

```
"iş var mı" (sistem python'u, ~20 sn): pist dolu, rapor bekleyen yok, onarım yok → bitir
analitik (eşleştir + 3 günlük ödül penceresi) → marka kontrolü → pist denetimi (plansız kalan videoyu onar)
pistte boş slot (bugün + 2 gün) oldukça, koşu başına en çok 2 video:
  hazır üretim (kabulden geçmiş, kanala çıkmamış; artifact) → yoksa yarım üretim (senaryo + görseller) → yoksa
  haydut (kanca kalıbı) + havuzdan taze hikâye
    → senaryo (kod kapısı: sayı, ad, sembol, hakaret, uzunluk) + hakem, en çok 4 tur satır onarımı, son çare satır çıkarma
    → görsel tarifinde yazı taşıyan nesne ve çok mekân temizliği → sahneler (4'lü paralel) → panel + değişen görünüş
      + OCR denetimi
    → ses → Whisper hizalama → render → müzik karışımı → yayın kabulü (kabul.py; geçmeyen yayına çıkmaz)
    → 4 dil çeviri (rakam kapısı) → Buffer → YouTube planlama → kayıt
  kota (4006) → slot bir sonraki koşuya kalır; yarının videosu planlıysa alarm yok (K-22)
çeviri onarımı (kotaya takılıp çevirisiz planlanan videonun eksik dilleri; 3 tutmayan koşudan sonra vazgeçer)
→ altyazı onarımı (YouTube kotasına takılan izler kuyrukta, `altyazi_eksik`) → haftalık rapor (hafta bitimi + 3 gün,
Analytics gecikmesi) → alarm (açık alarmı yalnız alarmsız tam üretim koşusu kapatır, `calisma/temiz`)
```

Earth K-25'ten beri kart biçiminde (`otomat/hikaye/kart.py`): kart metni + kod kapısı (sayı, ad, işaret, ekrana
sığma) + olgu hakemi; makalenin Commons görseli (serbest lisans, NC/ND değil) ya da tek yatay (1344×768) AI
illüstrasyonu; 8 sn render, müzik −16 LUFS; altyazı izi yok, başlık ve açıklama 4 dile. Yayın sırasında Buffer video
id'yi verir vermez kayıt yazılır (koşu kesilirse çift gönderi olmasın); otomat-site medya tarihçesi boşaldıkça tek
commit'e sıkıştırılır.

Kararlar: K-15 (genel kitle, Wikipedia), K-16 (sahne başına illüstrasyon), K-18 (havuz TypeSafe ile bir kez süzülür,
üretimdeki hakem LLM), K-20 (yeni kanal yok), K-22 (pist: üretim yayından ayrı), K-23 (yapı videodan videoya değişir),
K-24 (Orbit genel kitleye, MFK kapalı), K-25 (Earth kart biçimi; pusula: ilk saniyeleri geçen oranı). K-14 öldürme kriteri kanal başına, formatın ilk public videosundan (`donem`)
56 gün.

## Teknoloji Stack

| Katman | Seçim | Gerekçe |
| --- | --- | --- |
| Dil, paket | Python 3.12, `uv` | Spike'lar Python'da çalıştı; veri, görsel ve ses kütüphaneleri Python'da en olgun |
| Çalışma yeri | GitHub Actions (private repo, cron) | K-6/D-5: bilgisayar kapalıyken de çalışır; ayda ~300 dk, bedava kota 2.000 dk. Model dosyaları Actions cache'inde |
| Veri | USGS FDSN/GeoJSON, World Bank API v2, Eurostat API (JSON-stat) | Üçü de ticari kullanıma açık (USGS kamu malı, diğerleri CC BY 4.0 + atıf); anahtarsız |
| Harita tabanı | Natural Earth 1:110m/1:50m (GeoJSON) | Kamu malı; ülke kodu (ISO A3) World Bank/Eurostat ile birleşir |
| Görsel | matplotlib (Agg) + ffmpeg (imageio-ffmpeg) rawvideo pipe | S4: 30 sn 1080×1920 video 17 sn'de, CPU. Ek bağımlılık ve tarayıcı yok |
| LLM (kanca, başlık, çeviri, hakem) | Ollama + qwen3:4b-instruct (varsayılan), gemma3:4b (yedek) | K-1 bedava, yerel; düşünmesiz model, runner'da kanca ~3,5 sn (Faz 1 ölçümü). Model kimliği `config/modeller.toml`'da (sağlık nöbeti izler) |
| Anlamsal hakem | Yerel qwen3 ile Jev arasında Faz 4 ölçümü | D-8: maliyetsiz olan ve daha çok yanlış yakalayan kazanır |
| TTS | Kokoro v1.0 ONNX (`kokoro-onnx`), tek kanal sesi `am_michael` | S3: Apache-2.0, CPU'da gerçek zamanın ~4 katı; Whisper geri dökümü birebir |
| Altyazı zamanlaması | faster-whisper (small, int8) kelime zaman damgası, bilinen metne hizalama | Ses bizim ürettiğimiz metin; Whisper yalnız zamanlamayı verir |
| Yükleme | YouTube Data API v3 (`google-api-python-client`, `google-auth-oauthlib`) | `videos.insert` 1 birim; `localizations` + `captions.insert` (400 birim) |
| Analitik | YouTube Analytics API (`yt-analytics.readonly`) | `engagedViews`, `averageViewPercentage`; 48–72 sa gecikme |
| Durum | Repo içi SQLite (`durum/otomat.db`), her koşu sonunda commit | Ek servis yok; geçmiş git'te |
| Sırlar | GitHub Actions Secrets (OAuth client + refresh token) | Koda ve repoya girmez |
| Kalite | ruff, pytest | CI: lint + test + "duman" (tek videoluk kuru koşu, yüklemesiz) |
| Audit sayfası | GitHub Pages (statik HTML: uygulama tanımı + gizlilik politikası + şartlar) | Bedava https; kişisel veri yok (D-9) |

## Mimari

Her koşu bir **boru hattı**dır; her aşama girdisini ve çıktısını diske (`calisma/<koşu-id>/`) yazar, bir aşama
düşerse koşu o videoyu bırakır, diğerine geçer, hata durumu rapora girer.

```
cron (Actions, günde 1)
  └─ seçici ── haydut (konu kolu, kanca kalıbı) ← analitik (geçmiş videolar, SQLite)
       └─ adaptör (USGS | World Bank | Eurostat) → olgu paketi (JSON, kaynak URL + çekim zamanı + hash)
            └─ tekrar kontrolü (aynı olgu/aynı açı son 60 günde var mı)
                 └─ anlatım: olgu cümleleri (kod şablonu, çeşitli) + kanca/başlık (LLM, yer tutucu)
                      └─ kapılar: (1) sayı/tutucu kapısı (2) anlamsal hakem (3) politika listesi
                           └─ görsel şablon (nokta harita | koroplet | sıralı çubuk) → sessiz video
                                └─ TTS → ses; Whisper → kelime zamanları → yakılmış altyazı + SRT
                                     └─ ffmpeg birleştirme → video.mp4 + kapak karesi
                                          └─ metadata: başlık/açıklama/etiket EN + ES/PT/DE/FR çeviri (LLM) + atıf
                                               └─ yayın: API yükleme + planlama (audit varsa)
                                                    │   ya da Plan B: Actions artifact (haftalık paket)
                                                    └─ kayıt: SQLite + rapor
aynı cron, üretimden önce → analitik toplayıcı (eşleştir + 3 günlük pencere) → SQLite → haydut posteriorları
aynı cron, pazartesi → raporlar/YYYY-HWW.md (üretilen, düşen, yüklenen, en iyi/kötü video, haydut durumu, dokunuş süresi)
sorun (analitik, kaynak, üretim, token) → calisma/alarm.md → "alarm" etiketli GitHub issue; temiz koşu kapatır
```

Önemli tasarım kararları:
- **K-4 Olgu koddan, çerçeve modelden.** LLM hiçbir sayı ya da özel ad üretmez; `{yer_tutucu}` yazar. Olgu cümleleri her
  olgu tipi için en az 5 varyantlı şablon havuzundan seçilir (politika: şablon tekrarı riski).
- **Kapı başarısızsa yayın yok** (K-3). Aynı koşuda bir kez yeniden üretilir; ikinci kez düşerse video bırakılır.
- **Ödül (Faz 6):** videonun ±14 gündeki komşularına göre sırası, yayın günü + 2 günlük pencerede: 0,7 × engagedViews
  + 0,3 × ortalama izlenme yüzdesi. Mutlak sayı değil, çünkü kanal büyüdükçe her video öncekini geçer. Konu (kol) ve
  kanca kalıbı için ayrı Beta(1, 1) posteriorları, son 56 günün ödülleriyle her koşuda baştan hesaplanır. Örnekleme
  ters CDF ile: aynı u'larla veri olmadan seçilecek kol da bulunur, fark logda `degisti` olarak görünür.
- **Tekrar engeli:** olgu paketi hash'i + (kol, ülke/bölge, gösterge) üçlüsü 60 gün içinde tekrar edilmez (videodaki
  botun %91 benzerlik eşiğinin bizdeki karşılığı, ama veride).
- **Hacim:** günde 1 video (v1). Artış, öldürme kriteri penceresindeki veriye göre karar olur.
- **Çok dil:** metin katmanı bizde (5 dil), ses katmanı YouTube'un otomatik dublajında (K-8).
- **Atıf:** her videonun alt köşesinde "Data: <kaynak>", açıklamada kaynak bağlantısı ve lisans (D-10).

## Kapsam (v1)

- **Süre tavanı:** ~4 hafta (Faz 1–6). Faz 7 takvim olarak 14 gün sürer.
- **Bitti = kullanıldı:** Bot 14 gün boyunca kod müdahalesi olmadan her gün en az bir video üretti, doğrulama kapısından
  geçenleri gerçek kanala yükledi (audit varsa otomatik; yoksa Plan B ile Scryne'ın haftalık toplu yüklemesi); analitik
  geri beslemesi en az bir seçimi değiştirdi (logda görünür); iki haftalık rapor repoya düştü. Scryne'ın toplam dokunuş
  süresi raporda yazar ve haftada 10 dakikayı geçmez.
- **Kollar:** USGS deprem (gerçek veriyle çerçeve), World Bank (duygusal çerçeveli sıralama), Eurostat (Avrupa ülke ülke).
- **Kanca kalıpları:** soru, "your country / each country", duygusal etiket, ölçek/çarpıtma.

## Riskler ve Doğrulamalar

| Risk | Durum | Önlem |
| --- | --- | --- |
| Görsel üretim yavaş/ağır | ✅ S4: 17 sn, CPU | — |
| TTS anlaşılmaz | ✅ S3: üç dilde birebir geri döküm | Doğallık Faz 4'te ilk 10 videoda kulakla (Scryne'a opsiyonel örnek) |
| LLM uydurur | ⚠️ S5/S6: sayı kapısı geçti, anlam hatası sürdü | K-4 + anlamsal hakem (Faz 4 ölçümü) |
| API yükleme kilidi | ⚠️ S2: audit olmadan private | Faz 5'te audit başvurusu; Plan B haftalık toplu yükleme; Studio otomasyonu yok |
| Audit reddi ya da sessizlik | açık | Plan B kalıcı olabilir; dokunuş haftada ≤ 10 dk sınırı içinde |
| "Inauthentic content" | açık | Veri + farklı açı, şablon varyantı, günde 1, tekrar engeli; atıf |
| Düz veri izlenmez | ✅ S1: çerçeve şart | Haydut konu × kanca öğrenir; öldürme kriteri 8. hafta |
| Actions runner LLM'i kaldırmaz | açık | Faz 1 ölçümü; qwen3:4b varsayılan; gerekirse kanca/başlık üretimi daha küçük modele |
| OAuth token 7 günde düşer | ✅ S2 araştırması | OAuth uygulaması "In production" (unverified ekranı tek kullanıcıya meşru); `invalid_grant` alarmı |
| Veri kaynağı değişir | açık | Adaptör başına sözleşme testi (gerçek yanıt şeması); kırılırsa o kol durur, diğerleri sürer |

## Kapsam Dışı

- Facebook/Instagram Reels çapraz yayını, stok görsel ve baskı tasarım kolları (v2, aynı medya motoru).
- NOAA GHCN rekorları, uzay ölçeği, "what if" senaryoları (D-2, D-3).
- Kokpit/vault rapor entegrasyonu (D-7).
- Oyun fabrikası, Apify mağazası, Telegram Stars botu (ayrı motorlar, sonraki projeler).
- TikTok, trade botu, ücretli her şey (K-1).
