# Apify kolu — doğrulama (2026-10-05)

Soru (Scryne): "gerçekten para kazandıracaksa şimdi yapalım." Cevap: **mevcut kısıtlarla (sıfır para, az emek) hayır; kol açılmadı.**

## Ölçülen (Store API, 05.10.2026, elle tekrar çekildi)
| Arama | En iyi actor, 30 günlük kullanıcı |
|---|---|
| eurostat | 2 (35 rakip) |
| world bank | 4 (23 rakip) |
| earthquake (USGS) | 1 (33 rakip) |
| sahibinden | 69 (13 rakip) |
| trendyol | 61 (33 rakip) |
| youtube transcript | 2.836 (38 rakip, lider güncel ve 5 puan) |
| indeed | 3.979 (36 rakip, lider 4,7 puan) |

## Koşullar (birincil kaynak: Apify docs/Terms/blog)
- Kâr = 0,8 × gelir − platform maliyeti; yalnız ücretli plan kullanıcıları sayılır. Rental 01.10.2026'da bitti, PPE.
- TR için pratikte havale: $100 eşik, SWIFT kesintisi $10–50, KYC. Eşik altında 12 ay kalan tutar yanar.
- 3 gün bozuk → "under maintenance" + sıralama düşer; 30 gün → deprecated. Issue'ya 14 gün içinde yanıt şartı.
- Medyan kazanç verisi yok; geliştirici başına ortalama ~$356–470/ay (dağılım çok çarpık).

## Sonuç
- Açık veri sarmalayıcısı (Otomat'ın kaynakları): talep yok, ölü fikir.
- Talebin olduğu yerde (YouTube, Indeed, Amazon) rakipler profesyonel ve günlük güncelleniyor; bakım ve anti-bot yükü "az emek"e uymuyor.
- TR nişi (Sahibinden/Trendyol): arz zayıf ama lider ayda ~60–70 kullanıcı ve 13–33 rakiple paylaşılıyor. Kaba tahmin
  (doğrulanmadı): lider bile ayda onlarca dolar; $100 eşik + kesinti yüzünden ödeme aylarca gecikir. Sahibinden anti-bot + KVKK riski.
- Yeniden açma koşulu: Scryne bakım zamanı ayırmayı kabul ederse ya da somut bir talep (ideas panosu, müşteri) görülürse.
