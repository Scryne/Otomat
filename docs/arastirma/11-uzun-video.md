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

- **K-31 İkinci biçim ve dil (10-18):** Scryne'ın gösterdiği Senin Devrin (@SeninDevrin, Türkçe; açılış 10-03, 15 günde
  4 video, 14,1 bin abone; "Eğer 1964'te Almanya'ya işçi olarak gitseydin?" 1,06 milyon izlenme, 865 yorum) "Your life
  as…" çerçevesinin en güçlü kanıtı: ikinci tekil şahıs, şimdiki zaman, ~1.100 kelime / 8-10 dk, kuru mizah, sonda
  izleyicinin kendi ailesine soru ("Senin ailende Almanya'ya giden var mı?"). Karar: ikinci film bu çerçevede ("What if
  you were … in …?") ama **İngilizce** ve Inkwell Oddities'te (Scryne: İngilizce izleyici daha çok kazandırıyor).
  Görsel dil bizim kalır (koyu sinematik); konu, karakter ve parlak arka planları kopyalanmaz. Ana karakter "sen"
  olduğundan gerçek kişinin yüzüne benzetme sorunu da kalkar.

## Pilot: Violet Jessop (10-17…10-18) [Ö]

Senaryo `filmler/violet-jessop/senaryo.json` (Wikipedia revid 1376997573): 8 bölüm, 47 blok, 1.150 kelime, 96 sahne.
Çıktı `calisma/film/violet-jessop/` (git dışı): `video.mp4`, `kapak.jpg`, `aciklama.txt`.

| Ölçü | Değer |
| --- | --- |
| Süre | 7:42 (anlatım 7:32 + 10 sn bitiş ekranı payı); K-26'nın 8 dk alt sınırının altında: 10 dk için ~1.500 kelime |
| Ses | -14,4 LUFS, LRA 2,6; müzik yatağı -27 LUFS, 7 parça |
| Görüntü | 1920×1080 24 fps, H.264 crf 18, 234 MB |
| Hareket | 21 Wan klibi / 96 sahne (%22); 28 planlandı, 7'si kameraya döndü (aşağıda) |
| Süre (duvar) | sahne ~21 dk (96 × ~13 sn), Wan ~30 dk (~65 sn/klip), anlatım ~10 dk, kare render ~20 dk (CPU, PIL) |
| Bellek | Wan fp8 ile en düşük boş RAM 6,0 GB (24 GB'ta) |
| Uçtan uca denetim | bitmiş videonun sesi (müzikle) Whisper small.en'den geçti: kelime farkı %0,8, senaryodaki **bütün sayılar** duyuldu; kalan farklar eşsesli (Jessop/Jessup, Assad/Asad) |

Üretimde bulunan ve kalıcı düzeltilen kusurlar:
- **Bellek:** 10-17'de ComfyUI'yi sistem kapattı: önbellekteki FLUX + Qwen (11 GB) üstüne Wan fp16 + UMT5 (15 GB). Wan
  yüklenirken fp8'e iner (`comfy.i2v_grafi`), i2v adımının öncesinde ve sonrasında modeller boşaltılır (`uretim.main`).
- **Wan yüz bozuyor:** göz/kaş/gülümseme hareketi istenen klipte nokta gözler siliniyordu. A/B (sahne 3, aynı tohum):
  fp16-10 adım ve fp8-20 adım eski istemle bozuk, fp8-10 adım yüzsüz istemle temiz → sebep istem. Senaryo denetimi
  i2v isteminde yüz hareketini reddeder (`senaryo.YUZ_HAREKETI`), istem yüzün sabit kaldığını söyler (`i2v_istemi`).
- **Wan kadraja bir şey sokuyor:** "the second hand ticks" bir insan eli getirdi (40, 63), ayrıca lazer çizgileri, uçan
  sallar, çaydanlık. İnsansız sahnenin istemi "No people and no hands appear. Nothing new enters the frame." der. Klip
  incelemesi (her klipten 0/12/24/36/48. kare) ilk turda 28'in 10'unu, istem düzeltmesinden sonra 10'un 6'sını, son
  videoda 1'ini daha (67, suda beliren nesne) bozuk buldu; bu 7 sahne kamera hareketine döndü. **Ders: Wan 5B'de
  hareket kalitesi tohum ve isteme çok bağlı; ~%25 bozuk klip beklenmeli, klip incelemesi üretimin parçası.**
- **Yan karakterler gerçekçi çiziliyordu:** referans yalnız kendi karakterini bağlıyor; masa başındaki yaşlı adam, kalabalık
  ve yolcular burunlu, yarı gerçekçi çıktı (23, 36, 42, 75, 87). Referanslı sahne istemi "every other person … same round
  cream-white head, dot eyes, no nose" der; 23 ancak adamın tarifi açıkça yazılınca düzeldi. Ayna ve lombozdan bakış
  kompozisyonu iki ayrı kişi üretti (22, 33): tarif aynasız/yandan yazıldı.
- **TTS yılı yanlış okudu:** Chatterbox "November 1916"yı "1906" söyledi (Whisper small ve medium aynı duydu). Kelime
  oranlı kapı bunu 0,048 farkla geçirdi. Artık yıllar TTS'e yazıyla gider ("nineteen sixteen"), karşılaştırmada sayı
  sözleri ve rakamlar aynı biçime iner ve sayısı tutmayan parça düşer (`anlatim.fark`); üç denemede düzelmezse üretim
  durur. Aynı düzeltme sahte alarmı da bitirdi: "two hours and forty minutes" ↔ "2 hours and 40 minutes" 0,22 fark alıp
  boşuna üç kez üretiliyordu. Parça dosyası metnin özetini taşır; metin değişince eski ses kullanılmaz.
- **Tarih damgası** açık gökyüzünde okunmuyordu: koyu kontur ve arkasında yumuşak koyu leke.

Açık kalan: 9 mumlu sahne 5 mum çiziyor; Titanic'in iskeleye yanaştığı sahnede yelken var (39); ses efekti yok; uzun
video yükleme yolu (K-30) denenmedi.
