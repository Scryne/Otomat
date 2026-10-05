# Audit'siz yükleme: üçüncü taraf yolu (2026-10-05)

Soru (Scryne): "başka yerden API alamıyor muyuz?" Resmî yol tek (YouTube Data API); kilit yükleyen Google projesindedir
(28.07.2020 sonrası doğrulanmamış her proje → private; yeni proje açmak işe yaramaz). Meşru alternatif: audit'li bir
üçüncü tarafın bağlantısı üzerinden yüklemek.

## Adaylar (ücretsiz + programatik)
| Aday | Durum |
|---|---|
| **Buffer API** (öncelik 1) | Her planda API, ücretsizde 1 anahtar / 3.000 istek / 30 gün (support.buffer.com/article/859, 05.10 kendim okudum); YouTube destekli; ücretsiz kuyruk kanal başına 10 zamanlı gönderi; video genel URL ile. Altyazı/localizations yok. |
| **Zernio** (yedek) | public/unlisted/private, planlı yayın, Shorts otomatik algı (docs.zernio.com/platforms/youtube, 05.10 okudum). Altyazı yükleyemiyor; localizations yok; ücretsiz limit net değil. |
| Elenen | Make (ücretsizde 5 MB), Zapier (5 video/24 sa, ücretsizde webhook yok), Upload-Post (10/ay), n8n cloud (Google doğrulaması yok, 403), Metricool/Publer/Later/Hootsuite/Ayrshare/IFTTT (API ücretli/yok). |

**Doğrulanmayan:** hiçbir aday için "ücretsiz planda public çıktı" diye bağımsız kanıt yok, yalnız satıcı beyanı.

## Test sonucu (2026-10-05 18:42 TR) — Buffer yolu çalışıyor
- Medya: `https://scryne.github.io/otomat-site/media/2026-10-05.mp4` (public site reposu, noreply kimlik, `217272e`).
- Buffer `createPost` (shareNow, `metadata.youtube.privacy: unlisted`, title, categoryId 28, isAiGenerated false) →
  `sent`; video `JXSEMofyS3k` kendi API'mizden okununca **unlisted / processed**, kilit yok.
- Kendi (doğrulanmamış) projemizden aynı videoya: `videos.update` snippet (etiket, defaultLanguage) ✅, `captions.insert`
  5 dil ✅, `videos.update` status → private + `publishAt 2026-10-12T14:00Z` ✅. Kilit yalnız `videos.insert`'te.
- Açık: planlı yayının 12.10 17:00'de gerçekten public'e döndüğü (o gün doğrula); localizations henüz denenmedi.
- Buffer ücretsiz: tek kanal bağlı (Earth in Numbers), org `6ac3c2e9eab1d137f7e5290d`, kanal `6ac3c3346a5c39ccb620b6af`.

## Plan (ilk hali)
1. Tek test videosu Buffer'dan (release asset URL'si) → kanalda Public mi? Değilse Zernio.
2. Hipotez: Buffer'ın yüklediği videoya kendi projemizle `videos.update` (localizations) + `captions.insert`. Kilidin bu
   çağrılara uygulanıp uygulanmadığı bilinmiyor; testte ölç.
3. Geçerse `OTOMAT_YAYIN=buffer` gibi ayrı yayın adaptörü; audit gelince API'ye dönülebilir.
