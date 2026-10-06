---
proje: Otomat
created: 2026-10-06
type: arastirma
---
# S7 — Çok kanal: platform sınırları, konu seçimi, kararlar

İki `arastirmaci` kolu, 2026-10-06. Scryne: "farklı kanallarda farklı konulu kanallar… projeyi en üst seviyeye
çıkaracak her şey, tamamen sana bırakıyorum."

## Platform sınırları (kaynaklı, 2026-10-06)

| Sınır | Değer | Sonuç |
|---|---|---|
| Buffer Free | aynı anda **3 kanal**, kanal başı kuyrukta 10 gönderi; ağ başına ömür boyu 8 bağlantı | en fazla 2 yeni kanal; bağla-kopar yapma |
| Buffer API (Free) | anahtar başına 30 günde 3.000, 24 sa'te 250, 15 dk'da 100 istek | 3 kanal × 30 gönderi → gönderi başı ≤ ~30 istek. Yoklama 15 → 45 sn, kanal kimliği profilde |
| Buffer bağlantısı | kanal **sahibi** olarak bağlanır (Manager olmaz); yeni kanal 1–2 gün beklemek zorunda kalabilir | kanal açılışı ile bağlantı ayrı günlere |
| YouTube Data API | proje başına 10.000 birim/gün; `videos.update` 50, `captions.insert` **400**; `videos.insert` ayrı kova (100/gün) | kanal başı ~2.050 birim/gün (5 altyazı izi) → 3 kanal ~6.200; 4. kanal sığmaz |
| Audit | form proje başına, kanal sayısı sormuyor | aynı OAuth istemcisi, kanal başına ayrı token |
| GitHub Actions | private repo 2.000 dk/ay | kanal başı ~420 dk → 3 kanal ~1.260 dk |
| YPP (1 Şubat 2027'den sonra yeni başvuru) | 1.000 abone + 8.000 saat ya da 90 günde 20M Shorts izlenmesi (blog.youtube, 10 Ağustos 2026) | yeni kanallar için para eşiği yüksek; ölçü izlenme ve abone |

## Asıl risk: kanal kümesi

- YouTube'un "inauthentic content" kuralı (15 Temmuz 2025) şablonla seri üretimi ve minimal varyasyonu hedefliyor;
  değerlendirme kanalın bütününe uygulanıyor. Spam kuralı "koordineli kanal ağlarını" kapsıyor.
- İkincil kaynaklar (Fstoppers, Bottle Rocket, Haziran–Ağustos 2026): Google'ın küme kapatma sistemi (S-CTS), ortak
  şablon/anlatı, eşzamanlı yükleme takvimi ve ortak altyapıyla kanalları kümeleyip birlikte kapatıyor. Üretimde
  çalıştığı doğrulanmadı.
- Resmî: kapatılan kişi başka kanal açamaz/sahip olamaz. Kanallar Scryne'ın kişisel Google hesabının marka hesapları:
  küme cezası kişisel hesaba dokunabilir. Scryne'a 2026-10-06'da bir kez söylendi.

**Önlemler (K-11):** her kanalın konusu, veri kaynağı, görsel şablonu, kimliği (renk, font), sesi, yükleme saati ve
adı ayrı. Kanal adında ortak kalıp yok ("… in Numbers" yok). Kanallar birer birer açılır.

## Konu seçimi

| Aday | Talep kanıtı | Veri | Günlük çeşitlilik | Earth'ten farkı | Yanlış bilgi riski | Karar |
|---|---|---|---|---|---|---|
| Uzay: yakın geçiş + ölçek | SolarBalls ölçek 1,2–1,4M; Cosmoknowledge medyan ~40K; asteroit için haber talebi | JPL CAD, Fireball, Exoplanet Archive (anahtarsız) | CAD günlerin ~%55'i, kalanı ötegezegen/ölçek | tam | düşük (çap "tahmini") | **Kanal 2** |
| İklim/okyanus | yalnız kendi 1,3M bulgumuz; NASA Climate 1–16K | ERA5 (ARCO/CDS), OISST ERDDAP; Open-Meteo tek bağımlılık olmaz (ücretsiz katman ticari değil, runner'da 429) | yüksek | "senin ülken" çakışıyor → küresel/okyanus/yıllar içi sıra | düşük | **Kanal 3, koşullu** |
| Tarih/sınır | güçlü (130K–17M) | CShapes ticari değil (NC-SA), basemaps "doğrulamadan kullanma" diyor | statik | tam | yüksek (tartışmalı sınırlar) | elendi |
| Enerji şebekesi | yok | Energy-Charts, UK Carbon | yüksek | tam | düşük | yedek |
| Spor, demografi, uçuş, biyoçeşitlilik | zayıf / kopya / OpenSky ticari değil / lisans karışık | | | | | elendi |

Veri tabanlı Shorts'ta tek başına grafik zayıf (F1Visualized, Visual Capitalist 1–5K): çerçeve belirleyici
(ölçek, "yanılsama", haber çıpası). Bu Earth için de geçerli: 10-05 başlığı "How Much Forest Cover Grew in Guam…"
04'teki zayıf kümeye düşüyor.

## Kararlar

- **K-10 Çok kanal = aynı motor, kanal profili.** `kanallar/<id>/kanal.toml`; motor kanaldan habersiz. Earth eski
  yollarını korur. Actions'ta kanal başına matris işi; alarm ve Plan B Release kanal başına.
- **K-11 Kanallar birbirinden ayrışır** (yukarıdaki önlemler); kopya kanal, çeviri kanalı yok.
- **K-12 En fazla 3 kanal** (Buffer Free, API kotası). 4. kanal ancak audit gelip `api` moduna geçilirse ve kota
  hesabı yeniden yapılırsa.
- **K-13 Birer birer.** Kanal 3, kanal 2'nin ilk 7 günü alarmsız geçmeden açılmaz.
- **K-14 Kanal başına öldürme kriteri.** Her kanal kendi ilk public videosundan 56 gün sonra Faz 8 ölçüsüyle
  değerlendirilir; bir kanalın kapanması diğerlerini etkilemez.
