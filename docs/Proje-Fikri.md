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

## Açık Sorular

- **S1 Niş:** hangi veri konusu Shorts'ta tutuyor, nerede rakip zayıf? (yt-dlp ile rakip kanal istatistiği)
- **S2 Yükleme kilidi:** doğrulanmamış API projesinde video private'a kilitleniyor. Denetim (audit) formu bedava;
  süresi ve onay şansı? Plan B: Scryne haftada bir Studio'da toplu "herkese açık" (≤ 1 dk).
- **S3 TTS kalitesi:** Kokoro/Piper İngilizce anlatımı "robot" algısı yaratıyor mu? Çok dilde aynı kalite?
- **S4 Görsel motor:** Python (matplotlib/Pillow + ffmpeg) mı, Remotion mı? 8 GB GPU'da 60 sn video kaç dakikada?
- **S5 Çok dilli ses kanalı:** YouTube Data API ek ses kanalı yüklemeyi destekliyor mu?
- **S6 Çalışma yeri:** bilgisayar kapalıyken ne olur? (GitHub Actions'ta CPU ile render mümkün mü)
