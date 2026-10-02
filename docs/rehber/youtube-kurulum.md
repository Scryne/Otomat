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

**Ne için:** botun senin kanalına video yükleyebilmesi için Google'dan bir "anahtar" alıyoruz. Bu anahtar yalnız senin
kanalına çalışır. Google bu ekranları 2025'te yeniden düzenledi; menüde arama, aşağıdaki **doğrudan bağlantıları** aç.

Bütün bağlantıları **kanal hesabıyla** (D1'de açtığın Gmail) giriş yapılmış tarayıcıda aç. Kişisel hesabınla açıksan
sağ üstteki profil resminden kanal hesabına geç. Konsol Türkçe açılabilir; düğmeleri İngilizce / Türkçe yazdım.

**Adım 1 — Proje aç.** https://console.cloud.google.com/projectcreate
- "Project name / Proje adı" kutusuna `otomat` yaz → **Create / Oluştur**. 10–20 sn bekle.
- Sağ üstte bildirim çıkar, **Select project / Projeyi seç** de. Sayfanın üstündeki proje kutusunda `otomat` yazmalı;
  aşağıdaki her adımda bunu kontrol et.

**Adım 2 — İki API'yi aç.**
- https://console.cloud.google.com/apis/library/youtube.googleapis.com → mavi **Enable / Etkinleştir**.
- https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com → **Enable / Etkinleştir**.

**Adım 3 — Uygulamayı tanıt.** https://console.cloud.google.com/auth/overview
- **Get started / Başlayın** düğmesine bas. Dört kısa ekran gelir:
  1. App information: App name `Earth in Numbers`, User support email: kanal e-postası → Next.
  2. Audience / Kitle: **External / Harici** → Next.
  3. Contact information: kanal e-postası → Next.
  4. Kutuyu işaretle (Google politikalarını kabul) → **Continue** → **Create / Oluştur**.

**Adım 4 — Uygulamayı "yayında" yap.** https://console.cloud.google.com/auth/audience
- "Publishing status: Testing" yazar. **Publish app / Uygulamayı yayınla** → **Confirm / Onayla**.
  Durum "In production" olmalı. Bu Google incelemesi başlatmaz; yapmazsak izin 7 günde düşer ve bot durur.

**Adım 5 — Anahtar dosyasını indir.** https://console.cloud.google.com/auth/clients
- **Create client / İstemci oluştur** → Application type: **Desktop app / Masaüstü uygulaması** → Name: `otomat`
  → **Create / Oluştur**.
- Açılan pencerede **Download JSON / JSON'u indir**. (Kapattıysan: listede `otomat`'a tıkla → sağda indirme simgesi.)
- İnen dosyanın adı `client_secret_....json` gibidir. Adını **`istemci.json`** yap ve şu klasöre koy:
  `C:\Users\scryn\Documents\Projeler\Otomat\sirlar\` (klasör yoksa oluştur). Bu klasör git'e hiç girmez.

**Adım 6 — İzni ver (birlikte yaparız).** Bana "anahtar hazır" de; komutu ben veririm ya da sen bu sohbete
`! uv run --extra ses python -m otomat.yayin.youtube yetki` yazarsın. Tarayıcı açılır:
- Kanal hesabını seç.
- "Google hasn't verified this app / Google bu uygulamayı doğrulamadı" uyarısı çıkar. Normal: uygulama senin, tek
  kullanıcısı sensin. **Advanced / Gelişmiş** → **Go to Earth in Numbers (unsafe)** → izinlerin hepsini işaretle →
  **Continue**. "The authentication flow has completed" yazısını görünce sekmeyi kapat.

Takılırsan ekranın görüntüsünü bu sohbete at; nerede olduğuna bakıp sonraki tıklamayı söylerim.

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
