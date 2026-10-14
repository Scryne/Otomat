---
proje: Otomat
created: 2026-10-14
type: arastirma
---
# 10 — Neden izlenmiyor, rakipler ne yapıyor (K-25)

Scryne (10-14): "videolar neden izlenmiyor… nasıl büyütücez, acaba yanlış mı ilerliyoruz?"

## Bizim veri (10-14, YouTube Analytics + Data API)

| Kanal | Public hikâye videosu | İzlenme | İlk saniyeleri geçen (engaged / görüntüleme) | Ortalama izlenen |
| --- | --- | --- | --- | --- |
| Earth | 4 (10-10 … 10-13) | 45, 81, 4, 3 | %25-38 | %54-62 |
| Orbit | 0 genel kitle (ilki 10-15); MFK masallar | hepsi 0 | — | — |

- İlk iki hikâye küçük bir test kitlesine gösterildi (45-81), tutmadı, sonrakiler 3-4'te kaldı. Ceza değil: her video
  ayrı test ediliyor (Creator Insider, 2023), her videoda aynı sonucu alıyoruz.
- İzleyicinin üçte ikisi ilk saniyelerde kaydırıyor. Aktarılan eşik (Paddy Galloway, ikincil): %70-90 iyi, %60 altı
  dağıtım söner.
- Kendi payımız: son iki haftanın emeği hattın güvenilirliğine gitti (iki tam denetim). Hat sağlam ama ölçülen şey
  "video çıktı mı"ydı, "izlendi mi" değil; haydut 3-80 izlenmelik gürültüden kanca öğrenemez.

## Politika (araştırma ajanı, birincil kaynaklar)

- "Inauthentic content" (eski "repetitious", 15 Tem 2025): YPP (para kazanma) politikası. Örnekleri bizim formata
  yakın: "image slideshows, templated storylines", "AI-generated content made with generic or unoriginal templates".
  Kanallar YPP'de değil; doğrudan dağıtım cezası yazılı değil. Neal Mohan (Oca 2026): düşük kaliteli AI içeriğe karşı
  spam/clickbait sistemleri genişletiliyor. Kaynak: support.google.com/youtube/answer/1311392.
- 31 Mar 2025'ten beri public izlenme sayısı her başlangıç ve tekrarı sayıyor; "engaged view" döngüsüz.
- Buffer ile yüklemenin dağıtımı düşürdüğüne kanıt yok. MFK videolar "diğer çocuk videolarıyla" önerilir (Help
  9527654); Shorts'a özel açıklama yok, bizim veri: MFK masallar 0.

## Rakip taraması (YouTube Data API, son 90 gün, 14 arama, 651 video, 513 kanal)

İngilizce tarih/tuhaf hikâye nişinde abonesi az ama tutarlı izlenen kanallar (son 50 videonun medyanı):

| Kanal | Medyan izlenme | Süre medyanı | Sıklık (son 50 video) | Biçim |
| --- | --- | --- | --- | --- |
| Dark History (805 abone) | 31 bin | 6 sn | ~6/gün | üstte paragraf, altta kesit |
| History Flash | 30 bin | 8 sn | ~2/gün | "Did you know?" + paragraf + görüntü |
| Past Vault | 28 bin | 7 sn | ~3/gün | aynı |
| History Snap92 | 23 bin | 7 sn | ~2/gün | aynı |
| Mechanism Hub | 39 bin | 7 sn | ~2/gün | aynı |
| Nightmare archives | 125 bin | 18 sn | 1/gün | dizi kesiti + tek başlık yazısı (telifli) |
| History Beyond Dates | 114 bin | 24 sn | ~2/gün | — |
| History with Asly | 42 bin | 20 sn | ~1/gün | gerçek tablo/fotoğraf + kare başına ekran cümlesi |
| Iris & Ash | 34 bin | 23 sn | ~2/gün | gerçek fotoğraf + ekran yazısı |
| Earth (biz) | 3-81 | 30-35 sn | 1/gün | AI illüstrasyon + TTS anlatım |

Aynı niş, aynı dönem: tipik videoda ~1000 kat fark. Niş tutuyor, biçim tutmuyor.

Ortak noktalar (storyboard + küçük resimlerden, 10-14):
1. Konunun **gerçek** görüntüsü (fotoğraf, tablo, gravür, belge). AI illüstrasyon yok.
2. Hikâye **ekranda yazıyla**; anlatıcı çoğunda yok, varsa ekran yazısı onu taşır (sessizde de anlaşılır).
3. En tutarlı küme 5-8 sn: üstte kısa başlık, altında 40-55 kelimelik tek paragraf (anahtar sözler renkli), altında
   görüntü. Paragraf bir okumada bitmiyor, izleyici videoyu döndürüyor: tekrarlar izlenme sayılıyor, izlenme oranı
   %100'ü aşıyor.
4. Sıklık günde 1-6.

## Uygulanabilirlik

- Havuzun 711 uygun makalesinin **453'ünde** (%64) ana görsel var, hepsi serbest lisans (268 kamu malı, kalanı CC BY /
  BY-SA / CC0; NonFree 0). Görseli olmayan ya da yazı ağırlıklı olan (Tarrare: belge sayfası) için kanal stiliyle tek
  AI illüstrasyonu.
- Video başına maliyet: bir kart metni + hakem (+ onarım), görsel çoğunlukla bedava. Sahneli video ~2.000 neuron.
- Telifli film/dizi kesiti kullanılmaz (Nightmare archives, Dark History yapıyor).

## Karar K-25 (2026-10-14)

- Earth **kart biçimine** geçer (`kanal.toml`: `bicim = "kart"`, `otomat/hikaye/kart.py`): 8 sn, anlatıcısız; kanal
  adı, 2-6 kelimelik kanca, 3-5 cümle / 40-55 kelime paragraf ([[vurgu]] renkli), makalenin Commons görseli (atıf
  karede ve açıklamada), müzik. Gerçeklik kapıları aynı: sayı/ad kaynakta, hakaret, olgu hakemi, en çok 4 tur onarım.
- Pusula: **ilk saniyeleri geçen oranı** (engaged / görüntüleme) ve ortalama izlenen %. Haftalık raporda "Kalan".
- Sıklık önce günde 1 (pist ve veri modeli değişmeden, sahneli son videolarla aynı saatte kıyas). İlk 3-4 kartta
  kalan oranı %50'yi geçerse günde 3'e çıkılır (`secimler.tarih` birincil anahtarı slot kimliğine döner: 6 dosyada 15
  sorgu).
- Orbit bir hafta sahneli genel kitle formatında veri toplar (ilk video 10-15), sonra karar.
- Erken karar noktası: 3 hafta içinde kalan oranı %50'yi geçmezse konsept değişir (Faz 8'in 8 haftası çok geç).
