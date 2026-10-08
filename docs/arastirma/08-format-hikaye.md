---
proje: Otomat
created: 2026-10-08
type: arastirma
---
# Format değişimi: veri videosundan gerçek hikâyeye

Tetik (2026-10-08, Scryne): "yapılan videolar izlenebilir bir türden değil… çocuk içerikleri, bir şeyi konu alan kısa
hikâye daha çok tutuyor… tamamen sana bırakıyorum."

## Ölçüm (API, 2026-10-08)
- Earth: 4 public video, izlenme 63 / 3 / 3 / 8; 1 abone. Orbit Ruler: ilk video 60 izlenme.
- 10-04 Earth videosunun kare incelemesi: zoom sonrası harita tabanı kayboluyor (siyah zeminde birkaç nokta), alt üçte
  bir boş, ilk saniyede kaydırmayı durduracak görüntü yok, konu ("Kuzey Mariana Adaları depremleri") izleyicinin
  derdine dokunmuyor, sona doğru gerilim/sürpriz yok.

## Pazar ve platform (arastirmaci, kaynaklı; özet)
- Shorts feed'inde küçük resim yok; ilk gösterimler "izlendi / kaydırıldı" oranıyla tartılır (YouTube blog, 2024).
  Jenny Hoyos: "bir saniyen var" — şok, merak, tatmin.
- Inauthentic content (support.google.com/youtube/answer/1311392, 2025-07-15): şablonlu hikâye, anlatısız slayt,
  "seri üretim izlenimi veren generic AI" parasallaştırılamaz. İzinli: aynı karakter/format serisi, **her videoda ayrı
  hikâye/konsept**; kendi anlatını AI ile görselleştirmek. Ocak 2026'da 16 AI-slop kanalı silindi; karar kanal düzeyinde.
- Made for kids: yorum, kişiselleştirilmiş reklam, bildirim vb. kapanır; 2026'da en sert denetim otomatik çocuk
  içeriğinde (NYT Şubat 2026, The 74 Mart 2026: kanallar YPP'den çıkarıldı/kapatıldı). **Çocuk kanalı açılmaz (K-15).**
- AI etiketi: yalnız gerçekçi sentetik içerikte zorunlu; açıkça illüstrasyon/animasyon muaf (27 Mayıs 2026'dan beri
  fotogerçekçi AI otomatik etiketleniyor).
- YPP (blog.youtube, 2026-08-10): 1 Şubat 2027'den itibaren yeni başvuruda 20M nitelikli Shorts izlenmesi/90 gün ya da
  8.000 saat. Günde 1 Short ile Shorts geliri hedef olamaz; ölçüt izlenme/abone (Faz 8) kalır.

## Araçlar (arastirmaci, 2026-10-08)
- GitHub Models 2026-07-30'da kapandı. Gemini görüntü modelleri free tier'da yok. Pixabay'in müzik API'si yok.
- Cloudflare Workers AI: günde 10.000 neuron bedava (aşınca hata, fatura yok); Llama 3.3 70B (~49K çıktı token/gün) ve
  flux-1-schnell (tahmin ~57-170 görsel/gün) aynı havuzdan. Gemini Flash-Lite free (forumda 500 RPD, resmî sayı yok;
  free içerik ürün geliştirmede kullanılır) yedek metin yolu.
- CPU'da yerel FLUX 16 GB'a sığmaz; SD-Turbo 512² olur ama kalite sınırlı.

## Spike S10 (`spikes/s10_hikaye.py`, 2026-10-08)
Kaynak: Wikipedia:Unusual articles alt sayfaları → 2.073 makale + editörün tek satırlık tanımı (günde 1 ile ~5,5 yıl).
Görsel: makalenin Commons görselleri (PD/CC), Ken Burns. Ses: Kokoro. Kapı: senaryodaki her sayı ve özel ad kaynakta.

| Makale | Uygun görsel | Kapı | Not |
| --- | --- | --- | --- |
| Unsinkable Sam | 1 | geçti | 4b: "lost two of his nine lives" uydurması (ad/sayı değil, kapı göremez) |
| London Beer Flood | 4 | 2. denemede | 300,000 galon uydurması yakalandı |
| Dancing plague of 1518 | 1 | 3 denemede düştü | "30 others" uydurması yakalandı |

Bulgular:
- **Arşiv görseli yetmez:** makale başına 1-4 uygun görsel → aynı resim döner; sonuç "anlatılı slayt", politikanın
  saydığı kalıba yakın. Sahne başına ayrı görsel gerekiyor.
- **Yazı:** qwen3:4b hikâyeyi kurabiliyor ama anlamsal uydurma yapıyor; qwen3:8b belirgin daha iyi (Dancing plague
  temiz) ama tutarlılık hatası sürüyor (Bal des Ardents: "five nobles died" / "killing four"). Sayı/ad kapısı gerekli
  ama yeterli değil; satır başına kaynak-destek hakemi (D-8 hattı) ve daha büyük model gerekli.

## Kararlar
- **K-15:** Yeni format genel kitleye (made for kids değil) **gerçek tuhaf hikâyeler**; kaynak Wikipedia:Unusual articles.
  Her video ayrı hikâye (politika), olgular kaynaktan (K-4'ün hikâye karşılığı: sayı/ad kapısı + satır hakemi).
- **K-16:** Görsel sahne başına üretilen 2D illüstrasyon (Cloudflare flux-1-schnell, sabit stil; gerçekçi değil →
  AI etiketi gerekmez) + varsa arşiv görseli. Metin Cloudflare Llama 3.3 70B; yedek Gemini Flash-Lite, sonra qwen3:8b.
  Tek dokunuş: Scryne'ın Cloudflare hesabı + Workers AI token'ı.
- **K-17:** Yeni format 3. kanal olarak açılır (Buffer'da 3. yer boş); Earth ve Orbit Ruler Faz 7 sayacı için
  dokunulmadan sürer. Kod `hikaye` dalında; main'e 10-21'den (Faz 7 sonu) sonra. Faz 12 (iklim kanalı) bunun yerine geçer.
