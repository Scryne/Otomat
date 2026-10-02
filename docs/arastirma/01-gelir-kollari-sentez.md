---
title: Otomasyon gelir kolları — araştırma sentezi
created: 2026-10-02
modified: 2026-10-02
type: note
status: active
tags: [gelir, otomasyon, arastirma, fikir]
---
# Otomasyon gelir kolları — araştırma sentezi (2026-10-02)

Scryne: "birden çok sektörde para kazanan otomasyonlar/botlar kuralım; ben kurayım, bot kazansın; sermayem yok;
2-3 değil çok sayıda kol olsun." Dört paralel `arastirmaci` kolu: para yolları (TR), platform politikaları,
açık veri + niş, gelir kolu kataloğu. Erişim tarihi hepsinde 2026-10-02. Proje kurulunca bu not
`docs/arastirma/` altına taşınır.

Tetikleyen video: TikTok @rahatyasam, "yattığı yerden para" Shorts botu (Quriox kanalı). Boru hattı: yerel Qwen
senaryo + iddia kontrolü → TTS → Pexels anlamsal klip → Whisper altyazı → YouTube Data API private + publishAt.
Ekrandaki sayılar: 335 video, 42 abone, ~4.7 bin izlenme/gün. Asıl gelir modeli "takip et, botu bilgisayarına
kurayım" — kitleyi satıyor.

## Kesişen bulgular
1. **Sıfır emek kol yok.** Scraper, eklenti, bot, oyun zamanla bozulur; bakım kol sayısıyla doğrusal artar →
   ortak motor + ince adaptör + öldürme kriteri şart.
2. **Çoğaltma = ceza.** YouTube "inauthentic content" (15.07.2025; Ocak 2026 dalgası: 16 kanal, 35M abone),
   Google "scaled content abuse" (güncelleme 28.08.2026), Redbubble/Pinterest toplu yükleme. Aynı motorla çok kol
   ancak her kolda farklı veri/değer varsa güvenli. "Çok kol" = çok farklı pazar yeri, aynı pazarda çok kopya değil.
3. **Kendi alıcısını getiren pazar yerleri kazanıyor.** Sermaye ve pazarlama yok → Apify Store, CrazyGames/Poki,
   Google Play, Adobe Stock, Etsy dağıtımı kendisi yapıyor. Kitle kurmak gereken kollar (Telegram kanalı, newsletter,
   kendi site) en yavaş.
4. **YouTube API:** doğrulanmamış projelerde (28.07.2020 sonrası) yüklenen video private'a kilitli, audit gerekir;
   yeni projede 100 videos.insert/gün.

## Para yolu (TR) — temiz / kapalı
- **Temiz:** AdSense ve YouTube (EFT/havale), Google Play (TRY EFT), Amazon.com.tr Ortaklık (havale, 25 EUR),
  Paddle (havale, $100, bireye açık), Lemon Squeezy (TR listede ama Stripe Managed Payments geçişi TR'yi kabul
  etmiyor — belirsiz), Etsy (TRY IBAN, ikincil), Apify (havale $100, KYC), CrazyGames (Tipalti, €100),
  Payoneer üzerinden Adobe Stock / Freepik / TeePublic / Redbubble.
- **Kapalı/pratikte kapalı:** PayPal, Stripe (stripe.com/global'da TR yok), Gumroad, RapidAPI (yalnız PayPal),
  Chrome Web Store ücretli (2021'de kapandı), Spreadshirt, TikTok Creator Rewards, GPT Store, Pinterest doğrudan.
  Wise TR hesaplarında alma kısıtı (31.08.2026, ikincil).
- **Doğrulanmadı:** Telegram Stars → Fragment → TON çekimi TR'den (KYC; kendi hesabından Stars ayarlarında test).
- Payoneer: ~%1 alma + %2-3 çekim + $29,95/yıl (<$2.000) — küçük kazancı yer.

## Vergi (ikincil; danışman/özelge doğrulaması gerek)
- **GVK 20/B:** sosyal içerik + mobil uygulama mağaza geliri; istisna belgesi, TR banka hesabı, %15 tevkifat,
  2026 sınırı 5.300.000 TL. YouTube ve Google Play kapsamda. **Kendi sitedeki AdSense kapsam dışı** (GİB özelgesi
  12.01.2023). Affiliate/dijital ürün/SaaS gri.
- **Genç girişimci (GVK 20):** 29 yaş altı, 3 yıl, 2026 için 400.000 TL; şahıs mükellefiyeti gerekir.

## Platform politikası özeti
- Otomasyona dost: Apify Store (AI yasağı yok, %80 pay, kalite skoru), Adobe Stock (AI etiketi, benzer ≤3
  iterasyon), Freepik/Magnific (etiket), KDP (beyan, haftada format başına 2 başlık), Telegram (spam hariç).
- Uzak dur: faceless toplu YouTube, toplu AI SEO, Shutterstock (AI yükleme yasak, 16.07.2025), Medium Partner
  (AI paywall dışı), Pinterest onaysız otomasyon.

## Açık veri (ticari)
- Açık: USGS, NOAA, Wikidata (CC0), World Bank, Eurostat, İBB (CC BY 4.0 uyumlu), MET Norway, OpenAQ, OSM (ODbL;
  Nominatim toplu geocoding yasak), FRED (seri bazında).
- Tuzak: Open-Meteo ücretsiz API (reklamlı site = ticari), TMDB (reklam = ticari), Kandilli (yazılı izin), MGM (ücretli).
- Belirsiz (yazılı teyit olmadan ticari kurma): TÜİK, TCMB, EPDK, AFAD, YÖK Atlas, MEB, TFF, TCDD.
- Kalabalık niş: nöbetçi eczane, canlı altın/akaryakıt/kur, YKS tercih. Görece boş: küresel deprem arşivi (USGS),
  Eurostat bölgesel karşılaştırma, iklim normali + "gezi için en iyi ay", İBB ilçe rehberleri.

## Gelir gerçekliği (kataloğun kanıtlı kısmı)
- Apify: ~$1,4M/ay, ~3.000 geliştirici, ortalama ~$470/ay; uzun kuyruk sıfır. 01.10.2026'da kira modeli bitti → pay-per-event.
- Tarayıcı oyunu: CrazyGames %60, Poki %50 reklam payı; oyun başına "yılda birkaç dolar–birkaç yüz dolar".
- Abonelik uygulamaları: medyan $492/ay; yeni uygulamaların %81'i iki yılda $1K/ay'a ulaşamıyor (RevenueCat).
- Etsy medyan satıcı yılda <$500; Adobe Stock görsel başına ~$0,32, AI payı %48.
- WordPress/CodeCanyon: 1. yıl eklentilerin %84'ü <$500.
- Faceless YouTube, pSEO, Telegram, Pinterest için güvenilir sağkalım verisi yok; görülen rakamlar kurs/blog.

## Aria'nın önerisi (karar Scryne'da)
Dört motor, motor başına birden çok kol:
- **Veri motoru:** Apify actor portföyü (öncelik 1) → aynı veriler niş siteye (Amazon.com.tr affiliate).
- **Oyun motoru:** HTML5 oyun şablonu → CrazyGames/Poki + aynı oyun Google Play'e sarılı (20/B kapsamı; $25 kayıt
  + 12 testçi/14 gün).
- **Medya motoru:** global veri-Shorts (USGS/World Bank/Eurostat animasyonları; editör kapısıyla) + Adobe Stock /
  Freepik / POD görsel hattı (Payoneer).
- **Bot motoru:** Telegram Stars botu — önce TR çekim testi.
Elendi: faceless toplu YouTube, toplu AI SEO, Shutterstock, Medium, Gumroad, RapidAPI, Chrome ücretli, GPT Store,
KDP düşük içerik, Pinterest otomasyonu, TikTok ödülleri.
Spike adayları: S1 Apify ilk actor + havale/KYC; S2 Telegram Stars çekimi TR; S3 CrazyGames onayı; S4 vergi özelgesi.
