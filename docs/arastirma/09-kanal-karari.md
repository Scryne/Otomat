---
proje: Otomat
created: 2026-10-09
type: arastirma
---
# Yeni kanal mı, mevcut kanal mı? (2026-10-09)

Tetik (Scryne, 2026-10-09): "istersen yeni kanal açıp her şeyi en baştan yapalım, algoritma 0'dan oluşmuş olur."
Araştırma: arastirmaci, kaynaklı. Etiket: [B] birincil (YouTube/Google), [İ] ikincil.

## Bulgular
- **Kanal geçmişi cezası yok.** 2025-26'da "geçmiş yeni videoyu cezalandırır / kanal sıfırlanır" diyen resmî bir ifade
  bulunamadı. En doğrudan resmî söz 2022'den: "Every Short is given a chance to succeed no matter the channel or the
  number of videos on the channel" [B, Creator Insider]. Öneri sistemi kanalın itibarını da tartar
  (howyoutubeworks/recommendations) [B]. İki kanalın geçmişi ~1 hafta, ~60 izlenme, eski içerik private: sıfırlanacak
  bir şey kalmadı.
- **Yeni kanalın maliyeti somut:**
  - Telefon doğrulaması: bir numara 2 kanal doğrular (support 9891124) [B].
  - Buffer'ın yeniden bağlanması gerekir (sahip olarak bağlanmalı) [B].
  - Aynı altyapıdan bir kanal daha açmak küme riskini büyütür: Google'ın S-CTS makalesi şablon, sıklık ve ortak altyapıyla
    kümeleri birlikte kapatıyor. Canlı kullanımı doğrulanmadı [İ, 2026-07].
- **MFK:**
  - Kanal düzeyi ayar, var olan ve gelecek **tüm** videolara uygulanır. Video düzeyi ayar kanalınkini ezer (support
    9527654) [B]. YouTube yanlış ayarı kendisi düzeltebilir; itiraz yalnız video düzeyinde yapılabilir [B].
  - 2026'da en çok baskı altındaki kategori AI çocuk içeriği: Fairplay mektubu, Nisan 2026. YouTube Kids uygulamasında AI
    yalnız "küçük, yüksek kaliteli kanal kümesi" için açık [İ, Tubefilter/Bloomberg].
- **Inauthentic content (support 1311392, 2025-07)** [B]:
  - İzinli: aynı intro/outro ile her videosu ayrı hikâye anlatan seri. Yasaklı: şablonlu, minimum değişimli seri üretim.
  - 2026-07 netleştirmesi yalnız monetizasyonla ilgili [İ, TechCrunch].
  - AI etiketli video önerilerde cezalandırılmıyor; hedef "insan yaratıcı girdisi olmayan şablonlu seri üretim" [İ, TNW].
- **Ad ve tanıtıcı:** 14 günde en çok 2 değişiklik yapılabilir (support 2657964) [B]. Reddin gerekçesi ve "24 saat
  kilidi" resmî bir sayfada geçmiyor. Taklit politikası, bilinen bir varlığa benzeyen adı yasaklıyor (support 2801947) [B].
- **Büyüme pratikleri** (süre, döngü, günde kaç video): kaynakların hepsi ikincil ve satıcı blogu, kontrollü veri yok.
  Kendi ölçümümüz esas: Studio'daki "izlendi / kaydırıldı" oranı ve haydudun ödülü.
- **API kilidi:** videos.insert sayfasının 2026-10-08 sürümünü özetleyici "kilitli değil" diye okudu. 03-youtube-api.md
  "kilitli" diyor. Buffer yolu bundan etkilenmez; açık soru, yayın yolunu değiştirmez.

## Kararlar
- **K-20:** Yeni kanal açılmaz; Earth ve Orbit hikâye kanalı olarak sürer (K-17 teyit). Yeni kanalın kanıtlanmış bir
  kazancı yok; maliyeti ve küme riski somut.
- **K-21:** Orbit kanal düzeyinde MFK olur. Geri çekilen 3 eski uzay videosu silinmez, video düzeyinde "çocuklara özel
  değil" ve private kalır (`marka.eski_videolari_ayir`, kimlik uygulanırken). Bu geri alınabilir; silme alınamaz.
- **K-22:** Üretim yayından ayrıldı (pist, `durum.PIST_GUN = 2`). 10-09'da kaçan cron ve kota yüzünden o gün video
  çıkmamıştı.
- **K-23:** "Şablon izlenimi" riskine karşı her videonun yapısı da değişir: kanca kalıbı (haydut), kamera hareketi
  (sahne başına), müzik (mood), sahne sayısı. Aynı kalıptan çıkan videolar yan yana durmasın.

## Cloudflare kotası (2026-10-09 gözlemi)
- 10-08 17:33 UTC'de kota doldu (spike'lar + iki uçtan uca deneme ≈ 10,9k neuron).
- 10-09 12:53 UTC'de API hâlâ 4006 dönüyordu. Panel ise "Neurons used today: 0/10k" gösteriyordu ve 00:00 UTC'den
  beri kullanım yoktu.
- Yani sayaç 00:00 UTC'de sıfırlanıyor ama engel en az ~19 saat sürdü.
- 15 dakikalık yoklama: 16:45 UTC'de hâlâ 4006, 17:00 UTC'de açık. Kota dolduktan ~23,5 saat sonra açıldı. Bu,
  günlük sıfırlamayla değil kayan 24 saatlik pencereyle uyumlu. Kotayı dolduran gün ertesi güne yalnız 24 saat
  geçince açılır diye planlanır.
- Pist bu belirsizliğe karşı tampon. Geliştirme denemeleri üretimle aynı kotayı paylaşıyor: yerel spike'lar günlük
  koşudan sonra yapılır ve 4.000 neuron'u geçmez.
