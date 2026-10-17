---
proje: Otomat
created: 2026-10-17
type: arastirma
---
# 11 — Shorts yerine uzun animasyonlu hikâye (K-26…K-30)

Tetik (Scryne, 10-17): "shorts yerine bu tarzda bir kanal büyütsek çok daha hızlı ve çok daha ilgi çekici olur…
normal videolar atmamız lazım… çok profesyonel olmalı. Tarihi figürleri anlatan, yaşadıklarını anlatan, yaşanılan
ilginç olaylar, bir karakterin macerası…" Referans: Day One Films (@dayonefilmsofficial).

Kaynaklar: üç araştırma ajanı (niş, araç zinciri, yayın yolu ve politika; birincil/ikincil etiketli), kendi Data API
taramamız (14 arama, ~1.450 birim) ve referans videoların storyboard + otomatik altyazıları (yt-dlp). [B] birincil,
[İ] ikincil, [Ö] kendi ölçümümüz.

## Referans kanal ne yapıyor [Ö]

- **Day One Films:** açılış 2026-09-27, 3 haftada 45,4 bin abone, 12 video, süre medyanı 2,9 dk, video medyanı ~86 bin,
  "DISCIPLINE" 3,8 milyon. Her ~1,6 günde bir video.
- **Anlatıcı yok.** Otomatik altyazılar yalnız şarkı sözü ve "[music]" (DISCIPLINE: "You are the fire. You are the
  future."). Videolar müzik + ses efektiyle ilerleyen sözsüz kısa filmler.
- Görsel (storyboard): siyah zemin, düz 2D, ince çizgili tek krem karakter; iç sesi kırmızı parlayan gölge bir figür ve
  kırmızı el yazısı ("skip the gym", "tomorrow."); "DAY 1 / DAY 47 / DAY 203" sayaçları. Kare kare hareket var.
- Kanal aynı zamanda bir kurs hunisi: Skool'da "Day One Films Studio" $29/ay, "AI workflow ile saatler içinde animasyon
  film" vaadi, araç adı yok [B, yayıncının sayfası]. Gelirin %80'i tek videodan [İ].
- Konusu motivasyon. Scryne'ın istediği konu (tarih, gerçek olay, karakter macerası) başka bir niş; Day One'dan
  ödünç alınacak olan paketleme ve görsel dil: tek kelimelik kapak yazısı, koyu sinematik minimal stil, tek karakterin
  yolculuğu, ekranda tarih damgası.

## Hedef niş [Ö + İ]

Kendi taramamız (son 60 gün, 4-20 dk videolar, izlenmeye göre):

| Kanal | Açılış | Abone | Uzun video süresi | Medyan izlenme | Sıklık | Biçim |
| --- | --- | --- | --- | --- | --- | --- |
| Animated History (@animatedhistoryy) | 2025-10 | 96,5 bin | 25 dk | 543 bin | ~18 günde 1 | çöp adam karakterler + kamu malı tablolar + animasyonlu harita, esprili anlatıcı |
| MapLore | 2026-04 | 84,8 bin | 2,3 dk | 1,56 milyon* | ~8 günde 1 | harita + animasyon (*tek viral video medyanı şişiriyor) |
| Day One Films | 2026-09 | 45,4 bin | 2,9 dk | 86 bin | ~1,6 günde 1 | sözsüz, müzikli |
| AniHis Hindi | 2026-01 | 123 bin | 21 dk | 65 bin | ~2,6 günde 1 | 2D animasyonlu biyografi/olay (Hintçe) |

İkincil (OutlierKit/AutonoLab, YouTube'da doğrulanmadı): Animistry (21 bin abone, "What was life like in medieval
London" 521 bin), Majestic Studios (236 bin, AI görsel + AI ses, 29 dk, ort. 922 bin), Brass & Blood ("Your life
as…", 19,5 bin abone, ort. 112 bin), Based Plato (8-14 dk, ort. 149 bin).

Ortak kalıplar:
- Kanıtı en güçlü çerçeveler: "Your life as…", "What it was like to be…", tek kişinin/olayın baştan sona gerçek
  hikâyesi, "The entire history of X in N minutes".
- Süre: tarih kanallarında 12-30 dk; kısa (2-10 dk) tarih animasyonu için büyüme kanıtı yok [İ]. vidIQ: evrensel ideal
  süre yok, retention'a göre ayarla [İ, 2026-09].
- Paketleme baskın (Galloway özeti: küçük resim başarının ~yarısı, 4-5 kelime, giriş vaadi ilk saniyelerde doğrular) [İ].
- RPM tahminleri (üçüncü taraf): tarih ~$5-12, eğitim/belgesel ~$10-14; Shorts RPM uzun videonun %3-14'ü [İ].

## Politika ve yayın yolu [B]

- **Inauthentic content** (YPP, support 1311392): şablonla seri üretim, videolar arası az değişim, aynı kalıpta aynı
  sonuçlu karakter hikâyeleri, anlatı değeri az slayt gösterisi para kazanamaz. AI araç olarak serbest; her videonun
  ayrı hikâyesi olan seri izinli. Temmuz 2026 açıklaması ve Ocak 2026 kapatma dalgası (16 kanal [İ]) bunu sertleştirdi.
- **AI etiketi** (support 14328491): gerçekçi olmayan, tamamen animasyonlu içerik muaf. Bizim stilimiz gerçekçi değil.
- **YPP:** 1.000 abone + 4.000 saat (yalnız public uzun video sayılır). 2027-02-01'den yeni başvurular 8.000 saat.
- **Buffer uzun videoyu desteklemiyor:** "Buffer currently supports YouTube Shorts only" (support 562); API'de küçük
  resim alanı yok. Shorts hattının yayın yolu uzun videoya taşınamaz.
- **Kendi API'miz:** `videos.insert` referansı (son güncelleme 2026-10-15) "doğrulanmamış projeden yüklenen video
  private'a kısıtlanmaz" diyor; 2020 kaydı ve bizim 10-05 gözlemimiz tersini söylüyor. 2025-12'den beri yükleme ~100
  birim; 2026-06'dan beri ayrı kova (günde 100 çağrı). Yalnız deney cevap verir.
- `thumbnails.set` 50 birim, telefon doğrulamalı kanal şart; doğrulanmamış projede çalışıp çalışmadığı belgesiz.
- Alternatif: Zernio (ilk 2 hesap ücretsiz, küçük resim ve uzun video belgeli), Upload-Post (ayda 10 yükleme ücretsiz).
  Audit durumları kendi sayfalarında yazmıyor. Postiz self-host aynı audit sorununu taşır.
- Uzun videoda bölümler açıklamaya (ilki 00:00, ≥3, her biri ≥10 sn); bitiş ekranı ve küçük resim A/B testi yalnız
  Studio'da.

## Araç zinciri (spike'lar, RTX 4060 Laptop 8 GB, 24 GB RAM) [Ö]

| Katman | Seçim | Lisans | Ölçüm |
| --- | --- | --- | --- |
| Görsel | FLUX.2 klein 4B fp8, yerel ComfyUI 0.41 | Apache-2.0 | 1344×768 ~7 sn; tek karakter referansıyla ~11 sn; 1920×1088 ~13 sn |
| Karakter tutarlılığı | karakter kartı (1024², sabit tohum) + `ReferenceLatent` | — | 4 farklı sahnede yüz, saç, kıyafet tutarlı; yaşlı/hemşire/çocuk varyantları aynı aile stilinde |
| Hareket | Wan 2.2 TI2V-5B (zaten kurulu), 832×480, 49 kare, 10 adım | Apache-2.0 | ~70 sn / 2 sn klip; karakter korunuyor, yüz ifadesi kayabiliyor. 1280×704 × 73 kare 10 dakikayı aştı (vazgeçildi) |
| Anlatım | Chatterbox (MIT), referans ses Kokoro `bm_george`'tan üretilir | MIT + Apache-2.0 | perde sapması Kokoro 3,96 → Chatterbox 5,33 yarım ton, Whisper ikisinde de hatasız; ~0,85× gerçek zaman. audiobox-aesthetics ayırt etmedi (CE 6,3-6,6 hepsi) |
| Müzik | Kevin MacLeod (CC BY 4.0), bölüm başına mood | CC BY | — |
| Kurgu | PIL afin kamera + ffmpeg, 1920×1080 24 fps | — | — |

Elenenler: Cloudflare'de görsel (klein-4b ~110 neuron/görsel → 96 sahne 10 bin neuron'luk günlük kotayı aşar, ve
Shorts hattıyla ortak), FLUX.2 klein 9B / Kontext dev / Qwen-Image 2.1 (ticari olmayan lisans), Higgs v3, Fish S2,
Voxtral, F5 ağırlıkları, MusicGen, MMAudio (ticari olmayan). Wan 14B (24 GB RAM'de kırılgan), LTX-2.x (gelir şartlı
lisans, 20 GB+ indirme) şimdilik denenmedi.

## Kararlar

- **K-26 Biçim:** 8-12 dk, anlatıcılı, tek kişinin ya da olayın kaynaklı gerçek hikâyesi; görsel dil minimal 2D, koyu
  sinematik ışık, video başına karakter kartlarıyla tutarlı karakterler; sahnelerin ~%30'unda gerçek hareket (Wan),
  gerisinde kamera hareketi; ekranda tarih/yer damgası; bölüm kartları ve açıklamada bölümler; kapak tek kelime büyük
  yazı + karakter. Day One'ın sözsüz müzik formatı alınmadı: tarih anlatısı anlatıcı ister ve nişin tutan kanallarının
  hepsi anlatıcılı.
- **K-27 Üretim yeri:** yerel makine (ComfyUI + Chatterbox), Actions değil. GPU işi bu laptopta bedava ve hızlı; Actions
  CPU'su ve Cloudflare kotası 100 sahneyi kaldırmaz. Hat `otomat/film/` (Shorts motorundan bağımsız).
- **K-28 Senaryo ve gerçeklik:** senaryo Wikipedia'nın sabit revizyonundan yazılır (`kaynaklar[].revid`); her cümle
  kaynakla satır satır karşılaştırılır, kaynakta olmayan iddia çıkar (pilotta 5 cümle düzeltildi: "too young and too
  pretty", "stern rose", "struck on the head", "four years", "outlived"). Her video ayrı hikâye ve ayrı yapı
  (inauthentic content). Sıklık haftada 2 ile başlar.
- **K-29 Kanal:** ilk uzun videolar Inkwell Oddities'e (Earth) gider: niş aynı (gerçek tuhaf olaylar, tarih), kanal
  geçmişi yok denecek kadar az (ceza yok, docs/arastirma/09). Ad uymazsa yeniden adlandırma Scryne'da (14 günde 2 hak).
- **K-30 Yayın yolu:** Buffer uzun videoyu taşımaz. Sıra: (1) kendi projemizden tek `videos.insert` unlisted denemesi
  (ayrı gün, hesap kilidi temkini; private kalırsa kilit sürüyor demektir), (2) olmazsa Zernio/Upload-Post denemesi,
  (3) o arada Scryne Studio'dan yükler (video başına ~3 dk: dosya, başlık, açıklama, kapak, bitiş ekranı).

## Pilot: Violet Jessop

(Pilot üretiminin ölçümleri aşağıda.)
