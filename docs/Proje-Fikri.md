---
proje: Otomat
created: 2026-10-02
type: proje-fikri
status: denetlendi
---
# Otomat — Proje Fikri

Sıfır sermayeyle, kurulduktan sonra Scryne'ın elini neredeyse hiç sürmediği otomatik gelir botları.
Şemsiye proje: ortak motorlar, motor başına birden çok gelir kolu. İlk kol **Shorts fabrikası v2**.

Kaynaklar: `docs/arastirma/01-gelir-kollari-sentez.md` (dört araştırma kolunun sentezi, 2026-10-02),
`docs/arastirma/02-referans-video.md` (Scryne'ın verdiği TikTok botunun incelemesi).

## Problem

Scryne gelir istiyor, ama üç sert şartı var: (1) para yatırmak yok, (2) kurulumdan sonra emek yok,
(3) "videodaki gibi" bot tarzı. Piyasadaki hazır "otomatik YouTube botları" bu şartları kâğıt üstünde
karşılıyor ama para getirmiyor. Referans videodaki kanal 335 videoda 42 abonede: eşiğin 24 kat altında,
politika riskinin tam hedefinde. Sebep otomasyon değil, botun **kör** olması:

1. Aynı tip videoyu basıyor, hangisinin tuttuğuna bakmıyor (geri besleme yok).
2. Herkesin elindeki stok görüntüyü (Pexels) ve yapay zekâ metnini kullanıyor (özgün değer yok →
   YouTube "inauthentic content", 15.07.2025).
3. Tek dilde, tek platformda (erişim tavanı düşük).

Otomat bu üç kusuru hedefler.

## Hedef Kullanıcı

İzleyici: İngilizce konuşan global Shorts izleyicisi (Türkçe Shorts gelirinin bin izlenme başı değeri
çok daha düşük). Ürünün sahibi ve tek operatörü Scryne. Operatörün haftalık yükü ≤ 5 dakika olmalı.

## Shorts fabrikası v2 — nasıl farklı

| Kusur (videodaki bot) | Otomat |
|---|---|
| Stok klip + yapay zekâ metni | **Veri tabanlı özgün görsel:** açık veriden (USGS, World Bank, Eurostat, NOAA, Wikidata, OSM; hepsi ticari kullanıma açık) kod ile üretilen harita, grafik ve sıralama animasyonları. Videodaki her sayı veriden gelir, model uydurmaz |
| Uydurma riski (LLM iddiası) | Sayılar ve olgular koddan; LLM yalnız anlatım cümlesini yazar. Doğrulama: senaryodaki her sayı veri kaydıyla eşleşmeli, eşleşmeyen video yayınlanmaz |
| Kör üretim | **Geri besleme döngüsü:** YouTube Analytics API'den izlenme, izlenme oranı, kaydırma oranı okunur; konu kümeleri ve kanca kalıpları bir çok kollu haydut (Thompson sampling) ile seçilir. Tutan formatın payı artar, tutmayan söner |
| Tek dil | Başlık, açıklama ve altyazı çok dilli (API'nin `localizations` + `captions` uçları). Çok dilli ses kanalı API ile mümkünse o da (spike) |
| Seri üretim (günde 12) | Günde 1–3 video. Hacim değil isabet. Politika riskini düşürür |

## Kısıtlar (Scryne kararları, 2026-10-02)

- **K-1 Sıfır para.** Ücretli API, ücretli hosting, kayıt ücreti yok. Platform komisyonları gelirden kesilir, sorun değil.
  Yerel modeller (RTX 4060 8 GB, Ollama), açık kaynak TTS, bedava API kotaları.
- **K-2 Minimum dokunuş.** Scryne'ın dokunuşları başta bir kez (kanal açmak, OAuth onayı, AdSense/kimlik) ve sonra
  haftada ≤ 5 dk (rapor okumak, gerekirse tek onay). Her dokunuş noktası `docs/Dokunus-Noktalari.md`'de listelenir.
- **K-3 Kör otomasyon yok.** Her video doğrulama kapısından geçer; kapıyı geçemeyen yayınlanmaz.

## v1: Kapsam ve "Bitti" Tanımı

- **Süre tavanı:** ~4 hafta.
- **Bitti = kullanıldı** (denetimde kesinleşti, D-1): Bot **14 gün boyunca kod müdahalesi olmadan** her gün en az bir
  video üretti, doğrulama kapısından geçenleri gerçek kanala yükledi (audit varsa otomatik public; yoksa Plan B ile
  Scryne'ın haftalık toplu yüklemesi); analitik geri beslemesi en az bir seçimi değiştirdi (logda görünür); iki haftalık
  rapor repoya düştü. Scryne'ın 14 gündeki toplam dokunuş süresi raporda yazar ve haftada 10 dakikayı geçmez.
- **Temel özellikler:**
  1. Veri adaptörleri (v1: USGS, World Bank, Eurostat) ve olgu paketi üretici
  2. Anlatım: olgu cümleleri kod şablonundan, kanca/başlık yerel LLM'den + anlamsal hakem
  3. Görsel motor: kodla üretilen harita/grafik animasyonu, 9:16, 1080×1920
  4. Seslendirme (yerel açık kaynak TTS) + kelime zamanlı altyazı
  5. YouTube yükleme + planlama + çok dilli metadata
  6. Analitik toplayıcı + haydut seçici
  7. Zamanlayıcı (GitHub Actions cron) + haftalık rapor (repoya) + hata alarmı (Actions e-postası)

## Kapsam Dışı (v1)

- Facebook/Instagram Reels çapraz yayını (v2; aynı videolar, ek kol).
- Stok görsel (Adobe Stock/Freepik) ve baskı tasarım (Redbubble/TeePublic) kolları: aynı medya motoru, v2+.
- Oyun fabrikası (CrazyGames/Poki), Apify scraper mağazası, Telegram Stars botu: ayrı motorlar, sonraki projeler/fazlar.
- TikTok (Creator Rewards Türkiye'de yok, API denetimsiz hesapta private).
- Trade botu (sermaye ister; TradeBot ayrı proje).

## Öldürme kriteri

İlk public videodan 8 hafta sonra: son 56 günde **≥ 1,2M Shorts izlenmesi veya ≥ 200 abone** yoksa konsept değişir
(niş ya da format). Bu, eşiğin (1.000 abone + 90 günde 10M) orantılı %20'si. İki konsept üst üste ölürse kol kapanır,
motorlar diğer kollara kalır (D-6).

## Spike sonuçları (2026-10-02)

- **S4 Görsel motor ✅** — `spikes/s4_render.py`: matplotlib (Agg) + ffmpeg pipe, USGS son 30 gün M4.5+ (526 deprem)
  üzerine 1080×1920, 30 fps, 30 sn animasyon **16,9 sn'de** (CPU). GPU gerekmiyor → GitHub Actions'ta da koşabilir.
  Kusur: dünya haritası dikey kadrajda küçük kalıyor; bölgesel zoom/kamera hareketi gerekir.
- **S3 TTS ✅** — `spikes/s3_tts.py`: Kokoro v1.0 (ONNX, CPU, Apache-2.0) EN/ES/PT; 13,8 sn ses 3,7 sn'de. Anlaşılırlık
  vekili: Whisper geri dökümü üç dilde metinle kelimesi kelimesine aynı (`s3_geri.py`). Doğallık kulakla ölçülmedi.
- **Senaryo + kapı (kısmi)** — `spikes/s5_senaryo.py`, gemma3:4b, 7 sn. Sayı kapısı "80"i yakaladı ama o sayı yer
  adının içindeydi (yanlış alarm); "thirty" yazıyla geçti (kaçak); asıl hata **anlamsal**: "Indonesia accounted for 68
  of the most active areas" — sayı doğru, cümle yanlış. Sonuç: sayı kapısı yetmez. Tasarım kararı adayı: LLM sayı
  yazmaz, yer tutucu (`{total_quakes}`) yazar, kod doldurur; ayrıca anlamsal kontrol (olgu ↔ cümle) — aday TypeSafe
  (maliyet şartı K-1'e takılırsa yerel ikinci model hakem).
- **Yer tutucu denemesi** — `spikes/s6_yer_tutucu.py`, qwen3:8b (`think:false`, ~2 sn): sayı kapısı 3/3 geçti, ama
  anlamsal hatalar sürdü: "over 526" (yanlış nicelik), "6 of these" (dünya geneli 6'yı Endonezya'nın 68'ine bağladı),
  "powerful enough to cause significant damage" (veride olmayan iddia), "in the past 30," (birim düştü). **Sonuç:**
  olgu cümleleri koddan gelen çeşitli şablonlarla kurulur; LLM yalnız kanca, başlık ve geçiş cümlesi yazar; her video
  bir anlamsal hakemden geçer (karar adayı K-4, denetimde kapanır).
- **S2/S5/S6 ✅** — `docs/arastirma/03-youtube-api.md`: doğrulanmamış projede her yükleme private'a kilitli → audit
  v1'in kritik yolu; yükleme artık 1 birim; ek ses kanalı API'de yok ama YouTube otomatik dublajı (27 dil) bedava ve
  varsayılan açık; analitik 48–72 saat gecikmeli, "swiped away" API'de yok.
- **S1 Niş ✅** — `docs/arastirma/04-nis-analizi.md`: düz veri şablonu 0,3–6K izlenmede kalıyor; hit'ler (1–15M)
  çerçeveden geliyor (merak, "senin ülken", ölçek/çarpıtma, duygusal sıralama). En yakın kodla-veri analoğu küçük
  kalmış. **Değer verinin kendisinde değil, veri + çerçevede.** Haydudun deneyeceği şey bu yüzden konu değil,
  konu × kanca çifti.
- Örnek birleşik çıktı: `spikes/out/ornek_shorts.mp4` (git dışı).

## Denetim (2026-10-02)

Fikir dokümanı spike'lardan sonra eleştirel okundu. Bulgular ve kapanışları:

- **D-1 "Bitti" kendi içinde çelişiyordu.** "14 gün insan müdahalesi olmadan" ile audit gelene kadarki Plan B (Scryne'ın
  haftalık yüklemesi) aynı anda doğru olamaz; ayrıca bitti tanımı Google'ın audit takvimine bağlanmamalı. Düzeltildi:
  "kod müdahalesi olmadan" + Scryne'ın dokunuşu ölçülür ve haftada 10 dk'yı geçmez.
- **D-2 Kapsam 4 haftaya sığmıyordu.** 5 haydut kolu = 5 veri adaptörü + 5 görsel şablon. v1 üç kola indi: USGS, World
  Bank, Eurostat. Üçü üç görsel şablonu paylaşır (nokta haritası, koroplet harita, sıralı çubuk). NOAA GHCN rekorları
  (veri hacmi büyük) ve uzay ölçeği v2'ye.
- **D-3 "What if" senaryosu uydurma kapısı açar.** "12.0 deprem olsaydı" gibi fizik iddiası veriden gelmez → K-4'ü
  deler. v1'de yalnız gerçek veriyle çerçeve ("ülkendeki en güçlü deprem", "son 30 günde"). Senaryo kolu v2'de, ancak
  kaynağı olan bir modelle (ör. NOAA deniz seviyesi projeksiyonu).
- **D-4 Haydudun istatistiksel gücü zayıf.** 14 günde ~14–28 video ve 48–72 saat analitik gecikmesiyle 3 konu × 4 kanca =
  12 hücrede anlamlı öğrenme olmaz. Çözüm: hücre değil **faktörlü** haydut (konu ve kanca ayrı Thompson sampling, ödül
  `engagedViews` ve `averageViewPercentage`'dan); bitti kriteri "öğrendi" değil "mekanizma bir seçimi değiştirdi" der,
  dürüst sınır budur. Gerçek öğrenme 8 haftalık pencerede ölçülür.
- **D-5 Çalışma yeri Windows Görev Zamanlayıcı idi.** Bilgisayar kapalıyken bot durur → K-2'ye ters. K-6 ile GitHub
  Actions'a geçti. Risk: private repo standart runner'ı küçük (2 vCPU); qwen3:8b RAM'e sığmayabilir → varsayılan qwen3:4b,
  Faz 1'de ölçülür. Dakika bütçesi: private repoda ayda 2.000 dk; günde ~10 dk = ~300 dk.
- **D-6 Öldürme kriteri ölçülemezdi** ("yolun %20'si"). Sayıya bağlandı (yukarıda).
- **D-7 Rapor vault'a ve Kokpit'e düşemez.** Actions kullanıcının bilgisayarına yazamaz. v1: rapor repoya
  (`raporlar/YYYY-WW.md`), hata alarmı Actions'ın kendi e-postasıyla. Kokpit entegrasyonu v2.
- **D-8 Anlamsal hakem K-1 ile çakışabilir.** Global sistem LLM çıktısı doğrulamada TypeSafe'i önerir, ama maliyeti varsa
  K-1 (sıfır para) projede üstündür. Faz 4'te 30 etiketli cümleyle yerel hakem (qwen3, cümle başına evet/hayır) ile Jev
  ölçülür; maliyetsiz olan ve yanlış cümleyi daha çok yakalayan seçilir.
- **D-9 Gizlilik.** Audit için public bir gizlilik politikası sayfası şart; Kurallar gereği kişisel veri taşımaz. İletişim
  adresi olarak kanal için açılacak ayrı e-posta kullanılır (D1'de).
- **D-10 Atıf ve lisans.** World Bank ve Eurostat CC BY 4.0 → her videoda "Data: …" ve açıklamada kaynak bağlantısı.
  Natural Earth kamu malı. Arka plan müziği v1'de yok (telif riski).

## Kararlar (denetimde kapandı)

- **K-4 Olgu koddan, çerçeve modelden.** Olgu cümleleri çeşitlendirilmiş kod şablonlarıyla kurulur; yerel LLM
  (qwen3:8b) yalnız kanca, başlık ve geçiş yazar; her video anlamsal hakemden geçer.
- **K-5 Niş: "gezegen ve ülkeler, gerçek veriyle merak".** İngilizce, global. Başlangıç kolları (haydut kolları):
  (1) "your country" rekorları (NOAA GHCN, USGS, Wikidata), (2) gerçek veriyle "what if" tehlike senaryosu (USGS,
  deniz seviyesi + yükselti), (3) Avrupa ülke ülke (Eurostat), (4) World Bank + duygusal çerçeve (askerî harcama,
  borç, yaşam süresi), (5) uzay ölçek (Wikidata/NASA kamu malı). **D-2 ile v1 kolları: USGS (gerçek veriyle, "what if"
  yok), World Bank, Eurostat**; (1) NOAA kısmı ve (5) v2. Elenen: düz bar-chart-race, OSM "şehir çiziliyor",
  tarih/toprak (tarihî sınır verisi belirsiz). Kanca kalıpları: soru, "your country", duygusal etiket, ölçek.
- **K-6 Çalışma yeri: GitHub Actions** (private repo, günlük cron). Render CPU'da 17 sn, TTS CPU'da gerçek zamanın
  4 katı hızlı; bilgisayar kapalıyken de döner. LLM'in Actions CPU'sunda süresi Faz 1'de ölçülür (yedek: qwen3:4b).
- **K-7 Yükleme yolu:** YouTube Data API + audit başvurusu Faz 1'de (gizlilik politikası ve uygulama sayfası
  GitHub Pages'ta). Audit gelene kadar Plan B: haftalık toplu Studio yüklemesi (Scryne, ~5 dk). Tarayıcıyla Studio
  otomasyonu yok (kanal kapanma riski).
- **K-8 Çok dil:** başlık/açıklama/altyazı EN + ES + PT + DE + FR botla; ses için YouTube otomatik dublajı.

## Açık Sorular

- ~~S1~~ (kapandı) **Niş:** hangi veri konusu Shorts'ta tutuyor, nerede rakip zayıf? (yt-dlp ile rakip kanal istatistiği)
- ~~S2~~ (kapandı, yukarıda) **Yükleme kilidi:** doğrulanmamış API projesinde video private'a kilitleniyor. Denetim (audit) formu bedava;
  süresi ve onay şansı? Plan B: Scryne haftada bir Studio'da toplu "herkese açık" (≤ 1 dk).
- ~~S3~~ (kapandı; doğallık kulakla bakılmadı) **TTS kalitesi:** Kokoro/Piper İngilizce anlatımı "robot" algısı yaratıyor mu? Çok dilde aynı kalite?
- ~~S4~~ (kapandı: Python) **Görsel motor:** Python (matplotlib/Pillow + ffmpeg) mı, Remotion mı? 8 GB GPU'da 60 sn video kaç dakikada?
- ~~S5~~ (kapandı) **Çok dilli ses kanalı:** YouTube Data API ek ses kanalı yüklemeyi destekliyor mu?
- ~~S6~~ (kapandı: K-6, D-5) **Çalışma yeri:** bilgisayar kapalıyken ne olur? (GitHub Actions'ta CPU ile render mümkün mü)
