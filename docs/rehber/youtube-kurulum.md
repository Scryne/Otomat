---
proje: Otomat
created: 2026-10-02
type: rehber
---
# YouTube kurulumu — Scryne'ın üç adımı (D1–D3)

Toplam ~20 dakika, bir kez. Her adımın sonunda bana "tamam" demen yeter; gerisini ben yaparım.
Kişisel veri notu: kanal ve uygulama "Scryne" takma adıyla değil, kanalın kendi adıyla görünür. Gerçek adın hiçbir
public yüzeye yazılmaz (Kurallar). Google'ın denetim formu iletişim bilgisi ister; o form Google'a gider, yayınlanmaz.

## D1 — Marka hesabı olarak YouTube kanalı (≈5 dk)

> **2026-10-03 değişikliği:** ilk denemede yeni açılan `kanal-hesabi@ornek.invalid` hesabı aynı gün Cloud projesi +
> doğrulanmamış OAuth + API yüklemesi yapınca Google'ın otomatik güvenlik sistemine takıldı (girişte telefon istiyor,
> her numarayı reddediyor; OAuth istemcisi `disabled_client`). Yeni yol: kanal, Scryne'ın **eski ve doğrulanmış kendi
> Google hesabının altında marka hesabı** (Brand Account). Kanalda yalnız "Earth in Numbers" görünür; hesap sahibinin
> adı/e-postası kanalda, videolarda ve sitede görünmez.

1. Kendi (eski) Google hesabınla youtube.com'a giriş yap.
2. https://www.youtube.com/channel_switcher → **Create a channel / Kanal oluştur** → ad: **Earth in Numbers** →
   **Create / Oluştur**. Bu bir marka hesabı açar; kişisel kanalından ayrıdır.
3. Kanal açılınca sağ üst profil resminde bu kanala geçili olduğunu kontrol et (gerekirse **Hesap değiştir →
   Earth in Numbers**).
4. Kullanıcı adı: YouTube Studio → **Özelleştirme → Temel bilgiler → Herkese açık kullanıcı adı** → `@earth.in.numbers`
   (2026-10-02'de boştu; `@EarthInNumbers` alınmış).
5. Kanal ayarlarında: **Ayarlar → Kanal → Gelişmiş ayarlar** → "Çocuklara özel değil". **Ülke alanını boş bırak**
   (Scryne kararı, 2026-10-02). Para kazanma başvurusunda doldurulur; YPP şartı "programın mevcut olduğu bir ülkede
   yaşamak" olduğundan orada gerçek ikamet ülkesi yazılır. Kitleyi kanal ülkesi değil video dili/metadata belirler.
6. Telefon doğrulaması gerekmez (kendi hesabın zaten doğrulanmış). Aynı günde her şeyi yapmak yerine kanal açıldıktan
   sonra D2'ye geçmek yeterli; ilk yüklemeyi hemen yapmıyoruz.

## D2 — Google Cloud projesi ve izin (≈10 dk)

**Ne için:** botun senin kanalına video yükleyebilmesi için Google'dan bir "anahtar" alıyoruz. Bu anahtar yalnız senin
kanalına çalışır. Google bu ekranları 2025'te yeniden düzenledi; menüde arama, aşağıdaki **doğrudan bağlantıları** aç.

Bütün bağlantıları **kendi (eski) Google hesabınla** giriş yapılmış tarayıcıda aç. Cloud Console'da marka hesabına
geçilmez; proje senin hesabında durur, kanal seçimi Adım 6'daki izin ekranında yapılır. Konsol Türkçe açılabilir;
düğmeleri İngilizce / Türkçe yazdım. Destek ve iletişim e-postası olarak kendi e-postan görünür; bu ekranı yalnız sen
görürsün (uygulamanın tek kullanıcısı sensin).

**Adım 1 — Proje aç.** https://console.cloud.google.com/projectcreate
- "Project name / Proje adı" kutusuna `otomat` yaz → **Create / Oluştur**. 10–20 sn bekle.
- Sağ üstte bildirim çıkar, **Select project / Projeyi seç** de. Sayfanın üstündeki proje kutusunda `otomat` yazmalı;
  aşağıdaki her adımda bunu kontrol et.

**Adım 2 — İki API'yi aç.**
- https://console.cloud.google.com/apis/library/youtube.googleapis.com → mavi **Enable / Etkinleştir**.
- https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com → **Enable / Etkinleştir**.

**Adım 3 — Uygulamayı tanıt.** https://console.cloud.google.com/auth/overview
- **Get started / Başlayın** düğmesine bas. Dört kısa ekran gelir:
  1. App information: App name `Otomat` (sitedeki ve denetim formundaki adla aynı olmalı), User support email: kendi
     e-postan → Next.
  2. Audience / Kitle: **External / Harici** → Next.
  3. Contact information: kendi e-postan → Next.
- Sonra **Branding** sayfasında (https://console.cloud.google.com/auth/branding): App logo **boş**; Home page
  `https://scryne.github.io/otomat-site/`, Privacy `.../privacy.html`, Terms `.../terms.html`; Authorized domains →
  `scryne.github.io` → **Save**.
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
- Kendi Google hesabını seç. Ardından **"Choose an account or brand account / Hesap veya marka hesabı seçin"** ekranı
  gelir: **Earth in Numbers**'ı seç (kişisel kanalını değil). Yanlış seçilirse bot kişisel kanalına yükler; `kontrol`
  komutu kanal adını yazdığı için bunu hemen yakalarım.
- "Google hasn't verified this app / Google bu uygulamayı doğrulamadı" uyarısı çıkar. Normal: uygulama senin, tek
  kullanıcısı sensin. **Advanced / Gelişmiş** → **Go to Otomat (unsafe)** → izinlerin hepsini işaretle →
  **Continue**. "The authentication flow has completed" yazısını görünce sekmeyi kapat.

Takılırsan ekranın görüntüsünü bu sohbete at; nerede olduğuna bakıp sonraki tıklamayı söylerim.

D2 bitince ben: token'ı ve istemciyi GitHub Secrets'a koyarım (`YT_ISTEMCI_JSON`, `YT_TOKEN_JSON`), `kontrol` komutuyla
kanala bağlandığımızı doğrularım.

## D3 — Denetim (audit) başvurusu (≈5 dk)

Metni ben hazırladım: `docs/rehber/audit-basvurusu.md`. Form: https://support.google.com/youtube/contact/yt_api_form

1. Formu kendi Google hesabınla aç (Cloud projesinin sahibi). "Independent Developer / Sole Proprietor" seç.
2. Benim hazırladığım alanları yapıştır (proje numarası Cloud Console ana sayfasında yazar).
3. Gönder. Yanıt haftalar sürebilir; o sırada Plan B çalışır (aşağıda).

## Plan B — audit gelene kadar (haftada ~5 dk)

Bot her gün videoyu üretir ve GitHub'da haftalık paketi hazırlar. Haftada bir:
1. GitHub → Scryne/Otomat → **Releases** → bu haftanın "Teslim" sürümü → videoları indir (her gün bir `tarih_video.mp4`
   + `tarih_YUKLE.md` + altyazılar).
2. YouTube Studio → **Oluştur → Video yükle** → klasördeki mp4'leri sürükle.
3. Her video için `YUKLE.md`'deki başlık ve açıklamayı yapıştır, **Planla** ile yazan saati seç. Altyazılar `.srt` olarak
   klasörde; Studio → Altyazılar → Dosya yükle (isteğe bağlı, otomatik dublaj zaten açık).
