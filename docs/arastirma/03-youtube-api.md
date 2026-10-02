---
proje: Otomat
created: 2026-10-02
type: arastirma
---
# YouTube API — yükleme kilidi, çok dil, analitik (S2/S5/S6)

`arastirmaci` kolu, 2026-10-02. Birincil kaynak öncelikli; [ç] = çıkarım.

## S2 Yükleme kilidi ve denetim
- 28.07.2020 sonrası doğrulanmamış projede `videos.insert` ile yüklenen **her video private'a kilitli**, itiraz yok;
  tek yol API Compliance Audit. (developers.google.com/youtube/v3/docs/videos/insert, 14.09.2026; support.google.com/youtube/answer/7300965)
- Kilitli videonun Studio'dan public yapılabildiği **resmî olarak teyit edilmedi**; yardım sayfası özeti "yeniden inceleme
  olmadan değiştirilemez" diyor (dökümde doğrulanamadı). `publishAt` kilidi aşmaz [ç].
- Audit formu: support.google.com/youtube/contact/yt_api_form. "Independent Developer/Sole Proprietor" seçeneği var.
  İstenen: https site, gizlilik politikası + kullanım şartları, proje numarası, gizlilik politikasının YouTube bölümü
  ekran görüntüsü, OAuth/yükleme akışı kanıtı. Süre taahhüdü yok; Ağustos 2026 forum örneği: düzeltmeden sonra 4 hafta yanıtsız.
  Ret sebepleri: yanlış proje numarası, YouTube markasının yanlış kullanımı.
- OAuth: "Testing" durumunda refresh token **7 günde düşer**. "In production"a almak doğrulama gerektirmez; doğrulanmamış
  uygulama "unverified app" ekranı + 100 kullanıcı sınırıyla çalışır — tek kişilik kullanım için meşru yol.
- Kota (15.09.2026): `videos.insert` **1 birim**, ayrı kova, 100/gün (04.12.2025'te ~1600'den indi; 01.06.2026 kova sistemi).
  `captions.insert` 400, `videos.update` 50; genel 10.000 birim/gün.

## S5 Çok dil
- Başlık/açıklama: `snippet.defaultLanguage` + `localizations` (BCP-47), `videos.update` 50 birim, hepsi tek seferde.
- Altyazı: `captions.insert` 400 birim, dil başına bir iz; zamanlamayı biz veririz (`sync` 2024'te kalktı).
- Ek ses kanalı: **API'de yok**, yalnız Studio ve "Advanced features" kanallarına.
- **Otomatik dublaj** (04.02.2026): herkese açık, 27 dil, uygun kanallarda varsayılan açık — bedava çok dilli ses.
  Shorts'ta açık olduğu net değil.

## S6 Analitik
- `views`, `engagedViews` (Shorts'ta eski sayım), `averageViewPercentage`, `averageViewDuration`; `video` boyutu,
  `creatorContentType==SHORTS` süzgeci. "Viewed vs swiped away" API'de **yok**.
- Gecikme 48–72 saat → haydut ödülü en erken 3. gün kesinleşir. Ayrı kapsam: `yt-analytics.readonly`.

## Otomasyona etkisi
1. Audit, v1'in kritik yolu: başvuru Faz 1'de, gizlilik politikası + uygulama sayfası GitHub Pages'ta (bedava).
2. Audit gelene kadar Plan B: bot videoyu üretir, Scryne haftada bir Studio'dan toplu yükler/planlar (~5 dk) — K-2 ihlali,
   geçici olarak kabul; Studio otomasyonu (tarayıcı botu) kanal kapanma riski yüzünden **yapılmaz**.
3. Çok dilli ses için YouTube'un otomatik dublajına yaslan; biz çok dilli başlık/açıklama/altyazı yazarız.
