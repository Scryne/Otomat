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
