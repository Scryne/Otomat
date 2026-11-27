---
proje: Otomat
created: 2026-11-20
type: arastirma
---
# 14 — Kanal analizi (11-20) ve küresel trend açıklayıcı kanalı

Tetik (Scryne, 11-20): "kanalları analiz et güzelce. sonrasında… global olarak dünyada trend olan şeylerle alakalı
videolar yapacak bir sistem… yeni bir kanalda deniycez… uzun video, sonrasında o uzun videonun shorts videoları…
video üretirken daha iyi olmalısın, şu anki haliyle izlenmedi kanallar… github repolarını incele internette araştır."
Ek: bir YouTube videosundaki 16 Claude video-edit reposu ve transkripti. Yetki: "seni kısıtlamıyorum, herşeyi sana
bırakıyorum… opencode go orkestrasyonunu da kullanırsın."

Dört araştırma ajanı (repolar; trend veri kaynakları; trend kanal biçimi + platform kuralları; açık kaynak kalite
araçları) + canlı API ölçümü + kendi spike'larımız. [B] birincil (YouTube/Google'ın kendi sayfası, repo, resmî doküman),
[İ] ikincil (satıcı/blog), [Ö] kendi ölçümümüz.

## 1. Kanal analizi (2026-11-20, YouTube Data + Analytics API, ömür boyu) [Ö]

### One Ticket Back (film, 10-24'ten beri)

| | |
| --- | --- |
| Public | 4 film + 11 kesit; 17 video planlı (12-12'ye kadar) |
| Toplam | 1.937 görüntüleme, 4 abone, YPP saati ~0,1 / 4.000 |
| Filmler | Klondike 11, Lowell 6, Titanic/Violet 3, Ellis 2 görüntüleme (ömür boyu) |
| Kesitler | "An Officer Handed Her a Baby on the Titanic" 1.288 (%56 izlenme); "The Phone Call…" 432 (engaged %49) |
| Trafik | Shorts akışı 1.835 (%95), arama 75, önerilen 1 |
| Ülke | TR 559 (Scryne'ın kendi izlemesi olası), US 246, DE 85, GB 70 |

**Okuma:** uzun filmler **gösterim almıyor** (Faz 18 eşiklerinin hiçbiri ölçülemez: gösterim < 1.000). Sorun izlenme
yüzdesinden önce dağıtım: yeni yüzsüz kanalda arama talebi olmayan tarih konusu ("Lowell mill girl") önerilmiyor.
Kesitler çalışabiliyor (Titanic kesiti 1.288), ama izleyiciyi filme taşımıyor (filmlere trafik: arama 3, öneri 0).
vidIQ'nun yeni kanal çalışması [İ] medyan ilk uzun video için 30 günde 180 görüntüleme diyor; biz bunun ~20'de biriyiz.

### Arena Lore (spor Shorts, 10-28'den beri)

| | |
| --- | --- |
| Public | 51 video, 12 abone |
| Toplam | 7.495 görüntüleme (51 videoda medyan ~70) |
| En iyiler | Roberto Rojas sahte işaret fişeği 1.174 (engaged %42), İtalya–B.Almanya 1982 finali 837, Vietnam–Tayland 449 |
| Trafik | Shorts akışı 5.294 (%79), **YouTube araması 1.372 (%18)** |
| Kalan (engaged/görüntüleme) | seri ortalaması ~%30-35 (Faz 19 eşiği %50) |
| Ülke | US 942, GB 405, ID 277, IN 186 |
| Yaş | 35-44 erkek %33, 35-44 kadın %22 |
| Üretim | boks 11-06…11-15 arası 1 video (bütçe paylaşımı, Faz 19 notu); MMA/futbol günde 1 |

**Okuma:** iki kanalın ortak dersi: **isimli, aranan olaylar** (Roberto Rojas, 1982 finali, Khabib–McGregor) arama
trafiği getiriyor; isimsiz/ilgi dışı konu akışta ilk saniyede kaydırılıyor (%30 Kalan dört Shorts denemesinde sabit).
Bugünkü üretim hızı ve görsel dili (tek illüstrasyon + yavaş kamera, ekranda bilgi yok) "slayt" hissi veriyor: film
karelerinde (Great Stink) hareket yalnız kamera kaydırması.

### Bu analizin trend kanalına çıkardığı üç şart
1. **Hazır talep:** konu, insanların o gün aradığı şey olmalı (trend tanımı gereği).
2. **Ekranda bilgi:** sayı, manşet, zaman çizgisi, alıntı, gerçek fotoğraf; anlatıcı söyledikçe gelen parçalar.
3. **Kesit uzun videoya huni değil, kendi başına giriş kapısı** [İ: YouTube blog 2026-07-14]; Shorts'un uzun videoya
   bağlantısı yalnız Studio'dan elle eklenir (support 14075157) → Scryne'ın haftalık 1 dk'lık dokunuşu ya da tarayıcı.

## 2. Trend tespiti: kaynaklar [B, canlı denendi 11-20]

| Kaynak | Durum | Ne verir |
| --- | --- | --- |
| Google Trends RSS `trending/rss?geo=XX` | çalışıyor, anahtarsız, geo başına ~10 satır | sorgu, yaklaşık trafik, 3 haber (yayıncı URL'li) |
| Wikimedia Pageviews top + per-article | çalışıyor, UA şart, ~1 gün gecikme | günün en çok okunanları; makale başına 40 gün → artış oranı |
| Google News arama RSS `rss/search?q="X"+when:3d` | çalışıyor | "neden trend" başlıkları (link Google yönlendirmesi) |
| GDELT DOC 2.0 | çalışıyor (araştırma) | çok kaynaklı haber hacmi; v2'de eklenebilir |
| YouTube `mostPopular` | 2025-07'den beri yalnız müzik/film/oyun grafikleri | genel trend için işe yaramaz |
| Reddit, X, TikTok Creative Center, Exploding Topics | bedava ve kararlı yol yok | — |
| Wikinews | 2026-05'te kapandı | — |

Canlı radar (11-20): ham artış sıralamasında ölüm haberiyle sıçrayan kişiler ve bot kaynaklı sıçramalar üstte (Larry
Poindexter ×2463, Fiona hipopotam ölümü). TypeSafe ile eleme şart çıktı (bölüm 6).

## 3. Kanal biçimi ve platform kuralları

- **Inauthentic content** [B 1311392, 2025-07-15]: şablonlu/tekrarlı içerik, slayt gösterisi, minimal anlatımlı kayan
  yazı ve "özgün bakışı olmayan jenerik şablonlu AI içerik" para kazanmaz. **Reused**: haber akışını yalnız seslendirmek
  uygun değil. Yüzsüzlük yasak değil; ölçü özgün katkı ve üretim çeşitliliği. → her videoda **tez** (özgün açı),
  konuya göre değişen yapı, kaynaklı olgu.
- CEO mektubu 2026-01-21 [B]: "AI slop" azaltılacak; 16 büyük AI kanalının kapatılması [İ]. Kapatma kişiye gider
  (2802168) → yeni kanal ayrı Google hesabında açılmalı, One Ticket Back ve Arena Lore'dan ayrık.
- Sentetik içerik etiketi [B 14328491]: gerçekçi olmayan grafik, altyazı ve senaryo yardımı bildirim gerektirmez;
  gerçek kişiyi yapmadığı şeyi yaparken gösteren gerçekçi AI görüntü gerektirir → **gerçek kişilerin AI görüntüsü
  yok**; fotoğraflar gerçek ve lisanslı (Commons). TTS sesi açıklamada belirtilir.
- Haber rafları otorite sinyaliyle seçiliyor [B 9057101]: yeni yüzsüz kanal son dakikada görünmez → hedef **"X
  explained" arama niyeti**, konunun 3-7 gün süren merak penceresi, son dakika değil.
- Başlık [İ vidIQ 4M video]: soruyla biten başlık 0,82×; somut hikâye çerçeveleri kazanıyor. Kapak [İ vidIQ 500
  breakout]: yüksek kontrast, tek odak, medyan 5 kelime.
- Test & Compare yalnız Studio'dan, ölçütü izlenme süresi payı; API yok [B 13861714].
- Uzun video tutma [İ AIR 302 kanal]: 5-15 dk medyan %30, üst çeyrek %41; ilk 5-10 sn vaat [B blog 2026-07-14].
- Shorts payı yüklemelerin %25-40'ı ideal [İ AIR 18 bin kanal, korelasyon] → 1 uzun + 3 kesit = %75: kesitler daha
  seyrek (uzun video başına 2-3) ve kendi başına anlamlı.

## 4. Repolar (videodaki 16 repo; tam liste ve okunanlar ajan raporunda) [B, GitHub sayfaları]

Videodaki tezle aynı sonuç: tek bir repoyu kurmak yetmez; motor HyperFrames, üstüne kendi kurallarımız. Alınanlar:

| Repo | Alınan | Nerede |
| --- | --- | --- |
| HyperFrames (Apache-2.0, 87k★) | motor: HTML+GSAP → MP4, `check` (ölü süre, okunmayan satır, kontrast), `snapshot --review`; paketle gelen zanaat rehberleri (story, motion, film, captions, review) | `otomat/trend/kurgu.py`, `kesit.py` |
| vox-explainer (hyperframes-community-skills) | statik sahne ≤ 1/3, ardışık aynı tarif yok, gerçek varlık (Commons) | `senaryo.yapi_kapisi` |
| open-edit (Apache-2.0) | ekrandaki sayı kaynakla doğrulanır | `senaryo.sayi_kapisi` |
| motion-video-kit / claude-motion-design | üretici ve eleştirmen ayrı; eleştirmen yalnız kareleri görür | `uretim` görsel eleştirmen (gemini-4-argon) |
| saas-motion-kit | aynı geçiş arka arkaya yok, ≥ 3 geçiş ailesi | `kurgu.gecis_sec` |
| onetake (PolyForm NC; kod alınmadı) | "sahneler birbirini değiştiriyorsa slayttır" fikri: girişler sahnede bir nesneyle | `_giris_js` (perde, sel, savur, zoom) |
| brag | 0. kare kapak karesidir (boş/siyah değil) | `gecis_sec` ilk sahne kesme, kesit kancası 0. karede |
| lemo-opuscar | her TTS satırı Whisper'la geri okunur (bizde zaten var: film hattı) | `film.anlatim.seslendir` |
| herk-edit-kit, ffmpeg-skill, rea-video, snapcn, brag sesleri | ölçümler (ölü an ≤ 1 sn, -14 LUFS), notlar | `uretim.ses_seviyesi` |

HyperFrames telemetrisi kapalı çalıştırılır (`HYPERFRAMES_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`); sürüm sabit (0.9.19,
11-06; paket her gün sürüm çıkarıyor).

## 5. Araçlar [B/İ, ajan raporu]

- **TTS:** Chatterbox 2026-08'de "emekli, bakımsız" (MIT, çalışıyor) — film hattının Whisper kapılı yolu korunur.
  Ming-3.0-tts-0.5B (MIT, açık ağırlıklarda en iyi Elo) A/B adayı. Kokoro yedek.
- **Görsel:** gerçek konu için Commons (kişi, mekân, etkinlik fotoğrafları bol; lisans alanı makineden okunur), NASA
  kamu malı. Pexels/Pixabay anahtarlı genel B-roll (konu-özel değil) → v2.
- **Müzik/SFX:** Kevin MacLeod (CC BY, atıf), HyperFrames'le gelen 20 Pixabay SFX (atıfsız).
- **Metin modeli:** OpenCode Go uç noktası (`opencode.ai/inference/go/anthropic`), belgeli doğrudan kullanım; kendi
  UA + `x-opencode-session` şart (ölçüldü: UA'sız Cloudflare 1010, oturumsuz 400). Senaryo kimi-k3, olgu denetimi
  glm-5.3, görsel eleştirmen gemini-4-argon (görüntü okuyor; spike karelerinde benim gördüğüm kusurların aynısını
  buldu). Cloudflare bütçesine ve Claude limitine dokunmaz.

## 6. Spike ölçümleri [Ö]

| Ölçüm | Sonuç |
| --- | --- |
| HyperFrames render, 48,5 sn 1080p30, 9 sahne, 4 işçi, donanım GPU | 53,7 sn (≈ gerçek zaman) → 8 dk video ~9 dk |
| `check` | geçti; uyarılar: okunmayan satır, 3 sn+ ölü an, 28 px altı yazı → şablonlar düzeltildi |
| Jev (jev-1.14.0) eleme | GTA VI geçer (açıklanabilirlik 2,8/3, küresel 0,94); ölüm haberi trajedi 0,96; yerel basketbol küresel 0,10 |
| Editör (kimi-k3) 11-20 seçimi | GTA VI çıkışı, tez: "ilk kez bir oyun küresel ekonomik olay gibi davrandı"; yedek: Anthropic halka arzı |
| Commons, GTA VI konusu | 36 serbest görsel (makaledeki reklam panoları, Miami, oyun fuarı, mağaza kuyruğu) |

## Kararlar

- **K-38 (2026-11-20): yeni kol "trend açıklayıcı" (çalışma adı Trend Decoded), ayrı kanal.** İngilizce, küresel;
  günün en çok aranan, açıklanabilir ve trajedi/siyaset olmayan hikâyesi; 6-9 dk uzun video + 2-3 dikey kesit.
  Motor HyperFrames (`otomat/trend`), film ve spor hatlarından bağımsız; kanal Scryne'ın ayrı Google hesabında açılır
  (kapatma kişiye gider, 2802168).
- **K-39: görsel dil "yayın grafiği".** Zemin hep içerik (gerçek fotoğraf) ya da doygun renk alanı (sarı `#FFD60A`,
  kırmızı `#FF3B2F`, mürekkep `#0F0F10`, kâğıt `#F4F2EC`); League Gothic başlık, Roboto gövde; 9 sahne türü, her
  parça anlatıcı söylediğinde. Gerçek kişinin AI görüntüsü yok.
- **K-40: olgu zinciri.** Wikipedia sabit revizyonu + haber başlıkları = kaynak paketi; yazar her sahnede kaynak
  kimliği verir; kod kapısı (sayılar, yapı) + ayrı model olgu denetimi + onarım (en çok 4 tur); geçmeyen senaryo
  seslendirilmez.
- **K-41: seçim.** Radar (GT RSS 10 geo + Wikipedia artış) → Jev sert eleme (trajedi < 0,5, siyaset < 0,5, küresel ≥
  0,4, açıklanabilirlik ≥ 1,4/3) → LLM editör hikâye + tez + görsel aramaları. Kapsanan hikâye listesi
  `durum/trend_gecmis.json`.

## 7. İlk uçtan uca üretim (GTA VI, 11-20) [Ö]

| Aşama | Sonuç |
| --- | --- |
| Seçim | radar 36 aday → Jev elemesi → kimi-k3 editör: "GTA VI çıkışı"; tez: "asıl rekor 1,8 milyar değil, hastalık izinleri: oyun ekonomik veride görünen ilk çıkış" |
| Kaynak | Wikipedia 38.590 karakter (sabit revizyon) + 20 haber + 36 serbest Commons görseli (reklam panoları, Toronto metrosu, Edinburgh, Miami) |
| Senaryo | 56 sahne, 712 kelime; 4 olgu turu: sorun 9 → 1-2; 4 desteklenmeyen sahne son çare çıkarıldı |
| Ses | Chatterbox + Whisper kapısı, 5 dk 24 sn; kelime hizalama rakamlarda da doğru |
| Kurgu denetimi | HyperFrames check: hatalar 12 → 0; eleştirmen P0 bulguları 73 → 34 (kalanların çoğu kesimdeki 1-3 karelik geçiş) |

**Metin modeli dersleri (OpenCode Go, "pay" = abonelik birimi):**
- Tek çağrıda ~60 sahnelik JSON: kimi-k3 16k ve 32k token sınırına takıldı (akıl yürütme token'ları), bir çağrı ~1,93
  pay. Çözüm: iskelet (düşünerek, 3k token, ~0,29) + bölüm bölüm sahne (düşünme kapalı, `thinking: disabled`).
- Düşünme kapatılınca glm/kimi çıktısı 4-5 kat kısalıyor. Bölüm yazımı: kimi-k3 ~0,07/çağrı, glm-5.3 ~0,001/çağrı
  (glm'nin metni editoryal olarak yeterli çıktı; varsayılan glm-5.3).
- Olgu denetimi: glm-5.3 düşünürken 32k token'ı akıl yürütmeye harcayıp boş döndü; gemini-4-argon düşünmesiz
  ~0,06/çağrı, 10-16 sn, isabetli. Denetçiye görsel listesi verilmezse fotoğraf alt yazılarını kaynaksız sayıyor.
- LLM onarımı anlam sorunlarını düzeltiyor, biçim kurallarını (görsel tekrarı, durağan oran, çift kapanış) düzeltemiyor
  → `senaryo.yapi_onar` bunları kodla düzeltir.
- Video başına metin maliyeti (yaklaşık): iskelet 0,29 + bölümler 0,01 + kesit seçimi 0,02 + 4 denetim 0,25 + 4 onarım
  (kimi) ~0,6 ≈ **1,2 pay**; onarımı glm'ye taşımak ~0,6'ya indirir.

**Kurgu dersleri:** sahnenin ana öğesi anlatımdaki ipucu kelimesine bağlıyken ipucu geç gelince ekran 5 sn'ye kadar
boş renk zemin gösterdi (eleştirmen + `dead_stretch`). Kural: ana öğe ≤ 0,12 sn'de, sayı rakam söylenince sayar,
durağan sahnede tek yavaş itiş (1.0 → 1.04). Fotoğraf başlığı koyu kutuda (parlak tabela üstünde beyaz yazı okunmadı).

## 8. Scryne'ın izleme geri bildirimi ve v2 (11-20 akşam) [Ö/B]

Scryne iki videoyu izledi: "bu halle atamayız". Üç somut şikâyet:
1. **Anlatıcı** "çok sıkıcı, dümdüz metin anlatıyor, sesi AI olduğu belli".
2. **Müzik** "çok kötü, aynı parça sürekli döngüde, bayıyor".
3. **Görsel** "fotoğrafların arasında düz renk gelip yazılar geliyor, çok sıkıcı".

Üç araştırma ajanı (ses, müzik, görsel; 11-20) ve yerel ölçümlerle çözüm:

| Sorun | Kök neden | Çözüm (v2) | Ölçüm |
| --- | --- | --- | --- |
| Düz anlatım | Chatterbox'ın referansı Kokoro'nun sentetik sesiydi (klon referansın düzlüğünü kopyalar); senaryo cümle başına bir olgu | Qwen3-TTS-12Hz-1.7B **CustomVoice "Ryan"** (Apache-2.0) + sahne başına doğal dil ton talimatı (`ton`); yazar "hikâye anlatıcısı" kurallarıyla yazar | perde yayılımı 3,5 → 5,6 yarım ton (p5-p95 aralığı 12 → 16-20); konuşmacı benzerliği cümleler arası 0,84 (VoiceDesign 0,70, kimlik kayıyor); 4060'ta ~2× gerçek zaman |
| Döngü müzik | Tek Kevin MacLeod parçası 5 dk | **ACE-Step 1.5** (MIT, yerel) ile bölüm başına ruh haline göre tam uzunlukta parça; 3 sn çapraz geçiş; konuşma zamanından kısılma zarfı (konuşma -20 dB, boşluk -12, bölüm kartı -9, rakamdan önce nefes -26) | 95 sn parça ~9 sn'de; Whisper ile vokal sızıntısı yok; -14,5 LUFS |
| Düz renk kart | sayı/ifade/alıntı/zaman/ikili sahneleri renk alanında | Her sahnenin altında **2.5D parallax** (Depth Anything V2 Small ONNX, Apache-2.0; tek paylaşılan WebGL bağlamı), kartlar karartılmış/flu görüntünün üstünde; film greni, vinyet, manşette fosforlu kalem, bölümde ışık sızıntısı; her sahneye görsel (en çok 3 kez, komşu tekrar yok) | derinlik ~0,7 sn/görsel (CPU); 12 sn parallax render 21 sn (donanım GPU) |

**Elenenler ve nedenleri:**
- Gerçek bir kişinin sesini klonlamak: kişinin izni yok; modellerin şartları da taklidi yasaklıyor. Bunun yerine
  modelin kendi hazır sesi.
- VoiceDesign: en doğal ses tasarımı ama cümleden cümleye kimlik kayıyor (benzerlik 0,64-0,70).
- Hazır müzik kütüphaneleri (Incompetech, Pixabay, Jamendo, Openverse, Bensound): hepsinde Content ID talebi riski var
  (Jamendo ve Incompetech kendi sayfalarında söylüyor); Pixabay Music ve YouTube Audio Library'nin API'si yok.
  MusicGen/YuE2: ağırlıklar ticari değil.
- Yerel video üretimi (Wan 2.2 5B, LTX-2): 4060'ta 480p, klip başına dakikalar, film hattında %25-42 bozuk klip.
- Openverse görsel API'si 11-20'de 504 veriyordu; stok video (Pexels/Pixabay) ücretsiz ama hesap + anahtar ister
  (hesap açmak Scryne'ın işi) — `klip` alanı zeminde hazır, anahtar gelince bağlanır.
- Sesli içerik yargıcı: OpenCode Go uçları ses girdisini kabul etmiyor ("input_audio is not portable"); ses kalitesi
  bu yüzden akustik ölçülerle (pyin perde, resemblyzer konuşmacı benzerliği, Whisper) değerlendirildi, kulakla değil.

**Kararlar:**
- **K-42 (11-20): anlatıcı Qwen3-TTS CustomVoice "Ryan" + sahne başına ton.** Kurulum `~/tts-qwen3` (uv, torch cu128,
  faster-qwen3-tts 0.5.4, transformers 5.15.1 sabit: 5.23 tokenizer'ı kırıyor). Film hattı Chatterbox'ta kalır
  (`seslendir(motor=...)`). Ücretli yükseltme seçeneği: ElevenLabs Creator ($22/ay), Scryne karar verirse.
- **K-43: müzik her video için yerelde üretilir** (ACE-Step 1.5 turbo, dil modeli kapalı, int8; `~/ace-step`).
  Metadata'da "original score" yazar; Kevin MacLeod kalktı.
- **K-44: düz renk zemin yasak.** K-39'un "doygun renk alanı" zemini kaldırıldı; renkler yalnız vurgu, bant ve
  panel olarak kalır. Her sahnede hareketli görüntü (parallax > kamera > prosedürel leke).

**İlk v2 videosu (11-20/21, Robert Pattinson / James Bond, tamamen otomatik seçim) [Ö]:** 7:26, 55 sahne, 1080p30,
-14,1 LUFS, blackdetect 0 siyah kare; anlatım Whisper farkı ort. %1,1, perde yayılımı 5,9 yarım ton, 12 sahnede
konuşmacı benzerliği 0,88; müzik 6 bölüm parçası (gerilim/enerji/gerilim/merak/dram/umut), anlatımın ~17 dB altında;
3 kesit 48-55 sn. Koşu sırasında çıkan ve kalıcı düzeltilen kusurlar: kesit seçici kelime sınırını görmüyordu (sayılı
özet + kırpma); her sahneye görsel zorunlu olunca "en az kullanılan" ataması yanlış kişiyi gösterdi (eleştirmen P0
"anlamsız görsel" 29 → anlamla eşleştirme + kodla "adı geçmeyen kişinin fotoğrafı yok" kuralı → 4); alt yazı
görseli değişince yanlış kişinin altında kaldı (alt yazılı sahne yazarın görselini korur); "sel" geçişinin tam siyah
ilk karesi kesimde flaş gibiydi; alıntı yazısı yüzün üstünde okunmuyordu (koyu panel); "0TH" sayaç başlangıcı;
eleştirmen kareleri 4,5 GB tutup render'ın geçici alanını (~16 GB) doldurdu (kareler render öncesi silinir).

**Stok video (11-21) [Ö]:** Pexels yeni anahtar vermiyor ("New API key issuance is currently paused"); Pixabay video
API'si bağlandı (`otomat/trend/stok.py`, anahtar `.env`'de `PIXABAY_API_KEY`). Model kişiye özgü olmayan sahneleri
seçer (alıntı, alt yazılı fotoğraf, adı geçen kişi fotoğrafta kalır), arama sorgusu yazar, etiketlere bakıp klibi
seçer; "ai generated" etiketli klipler elenir. Bond videosunda 55 sahnenin 14'ü stok video. Aynı koşuda düzeltilenler:
alıntı paneli yüzün üstündeydi (alt banda), dolgulu dikey fotoğrafta derinlik hareketi kesik gibi duruyordu (dolgulu
fotoğrafa derinlik yok), tekrar sınırı alt yazılı fotoğrafın görselini değiştirip alt yazıyı yanlış görselin altında
bırakıyordu; sayı sahnesindeki etiket rakam açıklamasıdır, alt yazı korumasından çıkarıldı.

## 9. v3: "gerçek insan gibi" (11-26) [Ö/B]

Scryne (11-26): "sesi gerçek insan sesi gibi yapmalıyız, anlatımı gerçek insan gibi olmalı, videolar da en iyi halinde
değil." Tam yetkiyle, tek oturumda araştırma + ölçüm + uygulama.

**Ses: neden hâlâ AI gibiydi, ne değişti.**
- Kök nedenler: (1) model: Artificial Analysis TTS Arena (kör ikili tercih, 11-26) "Qwen3 TTS" 931 ELO (Alibaba bulut
  sürümü; açık 1.7B ayrıca listelenmiyor), açık ağırlıklılarda Kokoro bile 1060. (2) Kurgu: her sahne (1-2 cümle) ayrı
  üretilip sabit 0,38 sn sessizlikle yapıştırılıyordu; 55 kez aynı ritim. (3) Metin: "Here's the thing", "Hold that
  thought", tek satırlık dram cümleleri; konuşmacı ne kadar iyi olursa olsun yazı AI kokuyordu.
- Açık ağırlıklı sıralama (AA, 11-26): Fish Drama 3 1278 (35B, ~48 GB), Breeze TTS 2 1229 (ağırlık ticari değil),
  **Ming-3.0-tts 1181** (MIT, 0,5B), Phonon 1108, Fish S2 Pro 1104 (araştırma lisansı), Voxtral 1094 (NC), Kokoro 1060,
  Higgs V3 1035 (ticari değil), Chatterbox 1021, VibeVoice 1.5B 955. Ticari + 8 GB + bağımsız kıyas üçünü birlikte
  sağlayan tek model Ming.
- Yerel ölçüm (aynı 95 kelimelik paragraf, 4060): Ming UK_George 37 sn ses / ~60 sn üretim, ~3 GB VRAM, Whisper farkı
  0,00, 154 kelime/dk (belgesel anlatım aralığı), perde p5-p95 12,1 yarım ton. `raw_text` (tek parça) kelime düşürüyor
  (fark 0,25): kullanılmaz. Sayılar ($3.3 billion, 12.5%, 750,000, yıllar) normalleştirmesiz doğru okunuyor; "lbs" harf
  harf okunuyordu (`soylenis` birimleri açar).
- Akustik ölçüler doğallığı ayırmadı: Audiobox Aesthetics (CE/PQ) Qwen'i Ming'den yüksek puanladı, perde/duraklama
  istatistikleri benzer. TTSDS2 (arXiv 2506.19441) da MOS tahmincilerinin alan dışında zayıf olduğunu söylüyor. Karar
  insan tercih sıralamasına dayandı; kulakla doğrulama Scryne'da (örnekler `calisma/trend/ses_ornekleri/`).
- Elenenler: VibeVoice (Microsoft kodu kaldırdı, "ticari önerilmez"), Higgs V3 (ticari değil), IndexTTS 2.5 (AA'da
  yok, Windows'ta DeepSpeed), VoxCPM2 (8 GB sınırda, AA'da yok). Ücretli seçenek ElevenLabs Starter $6/ay hâlâ
  Scryne'ın kararı.

**Anlatım metni.** Yazar istemi "bir arkadaşına anlatan gerçek kişi" diline çevrildi: cümlelerin çoğu 12-25 kelime ve
bir öncekine bağlı, bölüm başına en çok bir kısa parça, slogan/üçleme/"X değil Y" yok, şaşırtıcı olduğunu söylemek
yok. YouTube kalıpları (`YASAK_IFADE`'ye 25 kalıp) kod kapısında; olgu denetçisi tekrar eden olguyu da işaretler.

**Görsel.** Bond videosu ölçümü: 55 sahnenin 36'sı yazılı kart, 19 fotoğrafın 14'ü başlıklı ("slayt"); aynı etkinliğin
fotoğrafları art arda; dikey fotoğraflar bulanık yan dolguda. Değişenler: en az yarı fotoğraf, başlıklı fotoğraf ≤ 1/3,
durağan kart ≤ 1/4, durağan karttan dönen fotoğraf başlıksız, art arda en çok üç fotoğraf; dikey fotoğraf "baskı"
düzeninde (beyaz kenar, gölge, ±1,6° eğim, kenara yakın); bütün fotoğraflara tek film derecelendirmesi; yakın kopya
(dHash + "-cropped") havuzdan elenir; bölüm kartında dev numara kişinin arkasında (kesit üstte).

**Kapak.** Eski kapak bulanık kalabalık fotoğrafıydı, yüz küçük ve yazının altında. Yeni kapak: HyperFrames
`remove-background` (0.9.19'da var, CPU'da ~1 sn) ile konu kesiti, sağda kadrajı dolduran boy, beyaz kontur + gölge +
sıcak ışık halkası, metin solda. Kesit tek ve belirgin konu değilse (kaplama %8-72, en büyük parça ≥ %80) eski düzen.

**HyperFrames 0.9.19 → 0.9.98?** Üç haftada 79 sürüm. Katalogdaki shader geçişleri (light-leak, whip-pan…) tak-çalıştır
blok değil, tek kompozisyonluk gösterim sayfaları; sahne başına alt kompozisyon yapımıza oturtmak büyük iş. Kullanılan
yeni şey (`remove-background`) eski sürümde de var. Yükseltme ertelendi; `check` (yüz üstü metin, güvenli alan) ve
`measure` sonraki adayı.

**Görsel havuzu.** Riemann (soyut konu) havuzunda 32 görselin ~19'u ilgisizdi (savaş anıtı, sınav kâğıdı, Kentucky
tarihi, alakasız matematikçiler: "yanlış kişiyi gösterme" riski). Senaryodan önce glm-5.3 başlıklara bakıp ilgisizleri
atar (`uretim.gorsel_suz`; portre yalnız adı geçen kişininse, mekân yalnız hikâyenin geçtiği yerse; 6'dan aza inerse havuz korunur, boşluğu stok video doldurur); tavan 36 → 48; makale diyagramları (SVG) 1920 px PNG olarak
alınır, saydam zemin kâğıda oturur. Süzgeç sonrası havuz küçük kalınca kart → fotoğraf dönüşümü görsel bulamıyordu:
dönüşüm "aynı tür art arda" için zorlanabilir, kelime sınırı yeni üsluba göre (fotoğraf 40, kart 26, bölüm 16).

**Sayı okuma (Ming, her biçim 3 tohum).** "$3.3 billion" 1/3 doğru ("3 billion dollars"), "three point three billion
dollars" 3/3; "007" bir koşuda anlaşılmaz, "double-oh-seven" 3/3. `soylenis` ondalığı, parayı, yüzdeyi ve 007'yi
yazıya çevirir; Whisper karşılaştırması (`kelimeler`) iki biçimi aynı birime indirir.

**Kararlar (v3):**
- **K-45 (11-26): anlatıcı Ming-3.0-tts UK_George.** Kurulum `~/tts-ming` (github.com/inclusionAI/Ming-3.0-tts, uv
  venv py3.12, torch 2.11 cu128, transformers 4.46.3; pynini yok, metin normalleştirme hatta). İşçi `film/ming_isci.py`,
  44,1 → 24 kHz süzgeçli. Film hattı Chatterbox'ta kalır. İki Ming süreci aynı anda yüklenince erişim ihlaliyle
  düşüyor: işçi üç kez yeniden çağrılır.
- **K-46: yazım dili konuşma dili.** Kalıp listesi kod kapısında; tekrar eden olgu olgu denetçisinde.
- **K-47: video görsel ağırlıklı.** Oranlar senaryo kapısında; baskı düzeni, renk ve süzgeçler `medya`/`uretim`'de.
- **K-48: kapak konu kesitiyle.** HyperFrames `remove-background` (yerel); konu belirgin değilse tam ekran fotoğraf.

**Kurgu eleştirmeni (Riemann, 11-26) ve buna göre değişenler.** İlk geçiş 156 bulgu: anlamsız görsel 35, tekrar
("kare 11 ile 12 aynı") 35, boş kadraj 24, okunmuyor 23. Değişenler: 6 sn'den uzun durağan görüntülü sahnede ortaya en
yakın kelime başında %16 yakın plan kesmesi (aynı görsel ikinci çekim olur); stokta soyut hareketli grafik etiketleri
(animation, icon, 3d render, abstract, loop…) sözcük sınırıyla elenir; baskı boyu 0,84 → 0,74 (kamera ve yakın plan
altında kenar kesilmesin); baskı zemini 46 px bulanık + %55 koyu düz gri yerine 16 px alan derinliği + vinyet. İkinci
geçiş 166 bulgu (tekrar 35 → 27; küçülen baskıyla boş kadraj 24 → 36, zemin bu yüzden yenilendi). Eleştirmenin toplam
sayısı koşudan koşuya ±%10 oynuyor (LLM); kategori yönü ve gözle kare kontrolü esas alınır.

**Render diski.** 7 dk video 4 işçiyle ~14 GB geçici kare istiyor; diskte 10 GB boştu, render düştü. `kurgu.render`
bu hatada tek işçiyle (kareler diske yazılmadan kodlayıcıya) yeniden dener: ~25-30 dk. HyperFrames `check` süreci ve
headless Chrome koşu bittikten sonra asılı kalabiliyor (proje klasörünü kilitledi); elle kapatıldı.

**Sıkı süzgeçle Riemann (v5, 11-26) [Ö].** Havuz 36 → 14 (3 SVG diyagram, 2 Riemann portresi, mezar/anıt, Göttingen
binaları, matematik modelleri); 50 sahne, 957 kelime, 6:07; -14,0 LUFS, siyah kare yok. Eleştirmen 143 bulgu: tekrar
35 → 14, anlamsız görsel 35 → 28, P0 21. Gözle kalanlar ve düzeltmeler: yıl sayacı sıfırdan sayıyordu ("0 year…"; yıl
artık sayılmaz, binlik ayırıcı almaz); stokta tanınabilir tek yüz (izleyici hikâyedeki kişi sanıyor; etiket ve istem
yasağı); Göttingen kütüphanesinin savaş yıkıntısı fotoğrafı başlığından anlaşılmadığı için süzgeçten geçti. Son
kusur başlık değil görüntü denetimi ister (sıradaki iş: görsel süzgece küçük resim vermek).
"Every one" Whisper'da "everyone" olunca sayı farkı 1,0 verip doğru parçayı düşürüyordu: karşılaştırmada birleşir.

**Sonraki tur (11-26 akşam, "her şeyi en iyi hale getir") [Ö].**
- *Görüntülü görsel süzgeci* (`gorsel_secici.py`): görseller G1… etiketli kontak sayfalarına dizilir (4×4, 1536×1024),
  gemini-4-argon başlıkla birlikte görüntüyü görüp seçer; düşerse başlıkla (glm-5.3). Riemann ham havuzu 36 → 9: savaş
  yıkıntısı (başlığı "University of Göttingen (Library)") ve adı geçmeyen kişinin gravürü yalnız görüntüyle elendi.
  Miss Universe havuzu 45 → 22 (taç fotoğrafları, yarışmanın yapıldığı kolezyum, adı geçen yarışmacılar).
- *Diyagram* (saydam ya da çoğu beyaz PNG): kâğıt zeminde kadrajın %92'si, baskı/renk/derinlik yok, beyaz kâğıtla
  çarpılıp erir. Eleştirmenin "okunmuyor" (31) ve "balık gözü ızgara" bulgularına karşı.
- *Kapak*: kesit çıkmazsa görsel sağda eğik baskı, yazı solda (diyagramın üstüne yazı binmiyor).
- *Bayat render*: `video_ham.mp4` yerinde durunca yeni plan render edilmeden eski video kullanılıyordu (sahneye yeni
  görsel atandığı halde videoda eski kaldı). Ham video projenin özetiyle damgalanır (`video_ham.proje`).
- *Kara kare*: 4 işçili render'da, GPU'yu aynı anda TTS kullanırken derinlikli (WebGL) sahneler üç yerde 2-8 sn siyah
  çizildi; aynı projenin anlık görüntüsü doğru. Render sonrası `kara_araliklar` (%90 siyah, ≥ 0,5 sn) bulursa tek
  işçiyle yeniden render.
- *Karanlık başlayan stok klip* (animasyon girişi) indirildikten sonra ölçülür ve reddedilir (YAVG < 22).
- Disk: Scryne'ın onayıyla ~/ComfyUI silindi (56 GB); render artık 4 işçiyle ~10 dk.

## 10. v4: "en iyi haline getir" (11-27) [Ö]

Scryne (11-27): "yaptığımız videoları sil, en son ve en iyi sistemle baştan atalım; önce sistemi en üst seviyeye
çıkar." Kanaldaki 5 private video (Miss Universe + 3 Short, Riemann) silindi, günlük görev kapatıldı.

**Ölçüm (Miss Universe, v3).** 10 sn'de bir kare + eleştirmen: 9:14, 72 sahne, 1452 kelime (tavan 1350), havuzda 11
görsel; bir fotoğraf 9 kez, kolezyum örnek karelerin ~%18'inde. 17 stok klibin ~10'u ilgisiz (etiketle seçim: "judges
table" → dosya dolabı, "children playing" → sabun köpüğü, "moving boxes" → havalimanı) ve "she decided to prepare"
satırında spor yapan yabancı bir kadın. Eleştirmen 174 bulgu (ilgisiz 40, tekrar 42).

**Değişenler.**
- *Süre görsel havuzuna göre* (`senaryo.kelime_hedefi`): görsel başına ~75 kelime, 700-1350; iskelet bütçesi ve bölüm
  kelimeleri orantılı küçülür; 4. kullanım son çaresi kalktı, havuz biterse sahne görselsiz kalır (stok doldurur).
- *Stok klip görüntüyle* (`stok.goruntuyle_sec`): sahne başına iki sorgu, 6 adayın küçük resmi kontak satırında,
  gemini-4-argon seçer ya da hiçbirini seçmez; zamirle belirli kişiyi anlatan satırda görünür kişi yok; Pixabay
  `isAiGenerated`/`isLowQuality` elenir; 1080p sürüm. Test (MU senaryosu, render yok): 21 sahneden 9'u klip aldı.
- *Konu görsel havuzuyla* (`uretim.konu_kaynak`): editör seçimi + 3 yedek; süzgeçten etkin 10 görsel geçmeyen konu
  yedeğe bırakılır, hiçbiri geçmezse 8+ olan en zengin, o da yoksa o gün video yok.
- *Benzer grup* (`gorsel_secici` GRUP_EN_COK 3 → 4, `senaryo.grup_siniri`): 3'lük kırpma MU havuzunu 22 → 11'e
  indirip aynı fotoğrafı döndürüyordu; grup 4 üyeyle kalır, grubun toplam kullanımı 4, üye başına 2; bütçede grup
  1,5 görsel sayılır.
- *Yazım ritmi* (`senaryo.ritim_kapisi`, `YASAK_KALIP`): A/B senaryosunda 43 sahnenin 17'si So/And/But/Because ile
  başlıyordu, "because" 9 kez, "the real question isn't whether…, it's whether…", "that gap is the story". Yazar
  istemi içerikle bağlanmayı ister; kapı bağlaç payını (≤ %22), art arda başlangıcı, because sıklığını ve karşıtlık/
  slogan kalıplarını yakalar; baştaki So/And kodla atılır; kalan ritim/kalıp bulgusu son turda uyarıdır. Kıvrık
  kesme işareti (’) yasak ifadeyi kaçırıyordu.
- *Kapak*: metin alana sığan en büyük boya büyür (MU: 94 → ~150 px), alan 570 px.
- *Shorts*: kanca paneli (620 px) ilk 2,6 sn'de yüzü örtüyordu; ilk sahne panelin altından başlar, panel kalkarken
  yerine oturur.
- *Eleştirmen* sahnelerin zaman + anlatımını görür; ilgisiz bulunan stok klip çıkarılır (fotoğrafı varsa). A/B'de
  anlatımı görmeyen eleştirmen 5 klibin 4'ünü çıkardı ("U.S. Army'de çalıştı" satırındaki helikopter dahil).
- *Görselsiz sahne* kapak görseli yerine en az kullanılan fotoğrafın koyusunu alır.
- *Yükleme güvenliği* (`yukle.yuklenebilir`): `yuklenmez` işaretli ve 48 saatten eski (yüklenmemiş) iş alınmaz.
- Openverse denendi (MU, Barreto, Riemann, GTA VI): sonuçlar çoğunlukla Commons kopyası ya da ilgisiz Flickr, en çok
  1024 px. Eklenmedi.

**A/B (aynı MU havuzu, grup ve anlatımlı eleştirmenden önce).** 5:28, 43 sahne, 840 kelime; eleştirmen 93 bulgu
(ilgisiz 15, tekrar 33); konser/yabancı kadın yok. Tekrar yoğunluğu dakikada 4,6 → 6,0 (kısa video, aynı 11 görsel):
grup düzeltmesinin gerekçesi.
