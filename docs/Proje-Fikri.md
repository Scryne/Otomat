---
proje: Otomat
created: 2026-10-02
type: proje-fikri
status: taslak
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
- **Bitti = kullanıldı:** Bot, **14 gün boyunca insan müdahalesi olmadan** gerçek kanala her gün en az bir video
  üretip yükledi; analitik geri beslemesi en az bir konu seçimini değiştirdi (logda görünür); haftalık rapor vault'a
  ve Kokpit'e düştü. Scryne'ın bu 14 günde dokunduğu süre toplamı ölçülür ve raporda yazar.
- **Temel özellikler:**
  1. Veri adaptörleri (ilk: USGS deprem, World Bank göstergeleri) ve konu üretici
  2. Senaryo (yerel LLM) + sayı doğrulama kapısı
  3. Görsel motor: kodla üretilen harita/grafik animasyonu, 9:16, 1080×1920
  4. Seslendirme (yerel açık kaynak TTS) + kelime zamanlı altyazı
  5. YouTube yükleme + planlama + çok dilli metadata
  6. Analitik toplayıcı + haydut seçici
  7. Zamanlayıcı (Windows Görev Zamanlayıcı) + haftalık rapor + hata alarmı

## Kapsam Dışı (v1)

- Facebook/Instagram Reels çapraz yayını (v2; aynı videolar, ek kol).
- Stok görsel (Adobe Stock/Freepik) ve baskı tasarım (Redbubble/TeePublic) kolları: aynı medya motoru, v2+.
- Oyun fabrikası (CrazyGames/Poki), Apify scraper mağazası, Telegram Stars botu: ayrı motorlar, sonraki projeler/fazlar.
- TikTok (Creator Rewards Türkiye'de yok, API denetimsiz hesapta private).
- Trade botu (sermaye ister; TradeBot ayrı proje).

## Öldürme kriteri

8 hafta sonunda kanal, para kazanma eşiğine (1.000 abone + 90 günde 10M Shorts izlenmesi) giden yolun %20'sinin
altındaysa konsept değişir (niş ya da format); iki konsept üst üste ölürse kol kapanır, motor diğer kollara kalır.

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
- Örnek birleşik çıktı: `spikes/out/ornek_shorts.mp4` (git dışı).

## Açık Sorular

- **S1 Niş:** hangi veri konusu Shorts'ta tutuyor, nerede rakip zayıf? (yt-dlp ile rakip kanal istatistiği)
- ~~S2~~ (kapandı, yukarıda) **Yükleme kilidi:** doğrulanmamış API projesinde video private'a kilitleniyor. Denetim (audit) formu bedava;
  süresi ve onay şansı? Plan B: Scryne haftada bir Studio'da toplu "herkese açık" (≤ 1 dk).
- ~~S3~~ (kapandı; doğallık kulakla bakılmadı) **TTS kalitesi:** Kokoro/Piper İngilizce anlatımı "robot" algısı yaratıyor mu? Çok dilde aynı kalite?
- ~~S4~~ (kapandı: Python) **Görsel motor:** Python (matplotlib/Pillow + ffmpeg) mı, Remotion mı? 8 GB GPU'da 60 sn video kaç dakikada?
- ~~S5~~ (kapandı) **Çok dilli ses kanalı:** YouTube Data API ek ses kanalı yüklemeyi destekliyor mu?
- **S6 Çalışma yeri:** bilgisayar kapalıyken ne olur? (GitHub Actions'ta CPU ile render mümkün mü)
