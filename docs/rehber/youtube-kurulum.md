---
proje: Otomat
created: 2026-10-02
type: rehber
---
# YouTube kurulumu — Scryne'ın üç adımı (D1–D3)

Toplam ~20 dakika, bir kez. Her adımın sonunda bana "tamam" demen yeter; gerisini ben yaparım.
Kişisel veri notu: kanal ve uygulama "Scryne" takma adıyla değil, kanalın kendi adıyla görünür. Gerçek adın hiçbir
public yüzeye yazılmaz (Kurallar). Google'ın denetim formu iletişim bilgisi ister; o form Google'a gider, yayınlanmaz.

## D1 — Kanal için e-posta ve YouTube kanalı (≈5 dk)

1. Yeni bir Google hesabı aç (kanalın e-postası olacak; kişisel hesabını kullanma). Önerilen: `kanal-hesabi@ornek.invalid`
   (doluysa benzeri; hesapta ad olarak "Earth in Numbers" yaz, kendi adını değil).
2. Bu hesapla youtube.com'a gir → sağ üst profil → **Kanal oluştur** → kanal adı **Earth in Numbers**. Kullanıcı adı (handle) için `@earth.in.numbers` boştu (2026-10-02;
   `@EarthInNumbers` alınmış).
3. Kanal ayarlarında: **Ayarlar → Kanal → Gelişmiş ayarlar** → "Çocuklara özel değil". **Ülke alanını boş bırak**
   (Scryne kararı, 2026-10-02). Para kazanma başvurusunda doldurulur; YPP şartı "programın mevcut olduğu bir ülkede
   yaşamak" olduğundan orada gerçek ikamet ülkesi yazılır. Kitleyi kanal ülkesi değil video dili/metadata belirler.
4. **Ayarlar → Kanal → Özellik uygunluğu** → telefonla doğrulama (uzun video ve özel küçük resim için; bir kez).

## D2 — Google Cloud projesi ve izin (≈10 dk)

Bunu kanal e-postasıyla giriş yapmış tarayıcıda yap.

1. https://console.cloud.google.com → üstte proje seçici → **Yeni proje** → ad: `otomat`.
2. **API'ler ve Hizmetler → Kitaplık** → "YouTube Data API v3" → **Etkinleştir**. Aynı yerden
   "YouTube Analytics API" → **Etkinleştir**.
3. **API'ler ve Hizmetler → OAuth izin ekranı** (Google Auth Platform):
   - Kullanıcı türü: **Harici**. Uygulama adı: kanalın adı. Destek e-postası: kanal e-postası.
   - Kitle (Audience) → **Test kullanıcıları**'na kanal e-postasını ekle.
   - Ardından **Uygulamayı yayınla (Publish app → In production)**. Doğrulama istemez; bunu yapmazsan izin 7 günde
     düşer ve bot durur (docs/arastirma/03).
4. **İstemciler (Credentials) → Kimlik bilgisi oluştur → OAuth istemci kimliği → Masaüstü uygulaması** → ad: `otomat`.
   **JSON'u indir.**
5. İndirilen dosyayı `C:\Users\scryn\Documents\Projeler\Otomat\sirlar\istemci.json` olarak kaydet
   (`sirlar/` klasörü git'e girmez).
6. Proje klasöründe bir terminalde (ya da bana `! uv run --extra ses python -m otomat.yayin.youtube yetki` yaz):
   tarayıcı açılır → kanal hesabını seç → "Google bu uygulamayı doğrulamadı" uyarısında **Gelişmiş → otomat'a git
   (güvenli değil)** → izinleri onayla. Bu uyarı normal: uygulama senin, tek kullanıcısı sensin.
   Sonunda `sirlar/token.json` yazılır.

D2 bitince ben: token'ı ve istemciyi GitHub Secrets'a koyarım (`YT_ISTEMCI_JSON`, `YT_TOKEN_JSON`), `kontrol` komutuyla
kanala bağlandığımızı doğrularım.

## D3 — Denetim (audit) başvurusu (≈5 dk)

Metni ben hazırladım: `docs/rehber/audit-basvurusu.md`. Form: https://support.google.com/youtube/contact/yt_api_form

1. Formu kanal e-postasıyla aç. "Independent Developer / Sole Proprietor" seç.
2. Benim hazırladığım alanları yapıştır (proje numarası Cloud Console ana sayfasında yazar).
3. Gönder. Yanıt haftalar sürebilir; o sırada Plan B çalışır (aşağıda).

## Plan B — audit gelene kadar (haftada ~5 dk)

Bot her gün videoyu üretir ve GitHub'da haftalık paketi hazırlar. Haftada bir:
1. GitHub → Scryne/Otomat → **Releases** → bu haftanın "Teslim" sürümü → videoları indir (her gün bir `tarih_video.mp4`
   + `tarih_YUKLE.md` + altyazılar).
2. YouTube Studio → **Oluştur → Video yükle** → klasördeki mp4'leri sürükle.
3. Her video için `YUKLE.md`'deki başlık ve açıklamayı yapıştır, **Planla** ile yazan saati seç. Altyazılar `.srt` olarak
   klasörde; Studio → Altyazılar → Dosya yükle (isteğe bağlı, otomatik dublaj zaten açık).
