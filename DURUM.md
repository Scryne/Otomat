# DURUM — Otomat

> Envanter, sertifika değil. Faz durumu `docs/Roadmap.md`'de; ScryneOS'taki proje notu ilişkisel kayıt.

**Ölçüm tarihi:** 2026-11-26

**Yayına hazır karnesi (2026-11-26):** Kod ✅ · Ürün ✅ (günlük üretim Actions'ta yeşil; trend v3 hattı 11-26'da Riemann
videosunu uçtan uca üretti) · Ön yüz ⚪ (arayüz yok; `site/` yalnız gizlilik/şartlar) · Belge ✅ · Kapı ✅ · Dış adımlar aşağıda.

## Ölçüm

- pytest 461 (+1 atlanan), ruff temiz, CI yeşil.
- Trend v3 hattı 11-26 akşamı yeni bir konuda (Miss Universe) gözetimsiz uçtan uca koştu: 9:14 video, kesitli kapak,
  3 Shorts, kara kare yok, -14 LUFS. Hazır iki video `calisma/trend/2026-11-26-1400-*` (Riemann) ve `-1959-*` (Miss Universe).
- Trend v3 (11-26): anlatıcı Ming-3.0-tts UK_George (AA kör tercih 1181 ELO; eski Qwen3 931), konuşma dili yazım
  kuralları, görsel ağırlıklı senaryo, baskı düzeni, görsel süzgeci, kesitli kapak, yakın plan kesmesi. Ayrıntı:
  `docs/arastirma/14-trend-kanali.md` bölüm 9.
- 11-26: Scryne'ın onayıyla ~/ComfyUI (56 GB) silindi, disk 58 GB boş. Film hattı (`otomat/film/comfy.py`:
  FLUX.2 klein + Wan 2.2) ve Matbaa'nın çizim/giyim adımları ComfyUI yeniden kurulmadan çalışmaz.
- Faz 18 kararı kaydedildi (Roadmap): filmler gösterim almıyor, yeni film yok; One Ticket Back'in kaderi Faz 8'de (12-19).

## Dış adımlar (Scryne)

1. Yeni anlatıcıyı dinleyip onaylamak (`calisma/trend/ses_ornekleri/7-…` eski, `8-…` yeni). Yetmezse tek ücretli
   seçenek ElevenLabs (Starter $6/ay).
2. Trend kanalı açıldı ve yetkilendirildi (11-27). Miss Universe ve Riemann yüklü, private: kapak için kanalın telefon
   doğrulaması (T3) bekleniyor; sonra `yukle son` ilk boş yayın günlerine zamanlar. Görev `Otomat-Trend-gunluk`
   Pzt/Çar/Cmt 09:00 (K-49).
3. 12-19 Faz 8 öldürme ölçümünün sonucuna göre One Ticket Back için karar.

## v2 fikirleri

- Stok klipte tanımadık tek kişi orta planda (izleyici hikâyedeki kişi sanabilir): etiket/istem yetmiyor, görüntüye bakan seçim.
- Soyut konularda aynı diyagram 4-5 kez: konuya göre üretilen hareketli grafik sahnesi.
- HyperFrames 0.9.19 → güncel: `check` (yüz üstü metin, güvenli alan) ve `measure` kalite kapısı olarak.

## 2026-11-27 akşam: v4 ("en iyi haline getir", yayın durduruldu)

- Kanaldaki 5 private video (Miss Universe + 3 Short, Riemann) Scryne'ın isteğiyle silindi; `Otomat-Trend-gunluk`
  görevi **kapalı** (hat en iyi hale gelince yeniden açılır: `schtasks /Change /TN \Otomat-Trend-gunluk /ENABLE`).
- v4 (commit 11b6158…b68a566, pytest 487): süre görsel havuzuna göre, stok klip görüntüyle seçilir (kişili satırda görünür
  kişi yok, 1080p), zayıf havuzlu konu yedeğe bırakılır, benzer görsel grubu 4 üye + toplam 4 kullanım, yazım ritmi
  kapısı (bağlaç zinciri, "isn't X, it's Y", slogan), kapak metni alana sığan en büyük boy, Shorts ilk sahnesi kanca
  panelinin altından başlar, eleştirmen sahne anlatımını görür, `yukle son` bayat/`yuklenmez` işi almaz.
- A/B (aynı Miss Universe havuzu, `calisma/trend/2026-11-27-ab-miss-universe`, yüklenmez): 9:14 → 5:28, eleştirmen
  174 → 93 bulgu, ilgisiz görsel 40 → 15; tekrar yoğunluğu hâlâ yüksek (grup düzeltmesi ve anlatımlı eleştirmen bu
  koşudan sonra geldi).
- **Sıradaki:** bugünün konusuyla (11-27 deneme seçimi: Wu-Tang Clan NFL Şükran Günü şovu) tam v4 hattında video üret,
  kareleri ve eleştirmen sayılarını A/B ile kıyasla; iyiyse yükle (ilk boş Pzt/Çar/Cmt 21:50 UTC) ve görevi aç.
  Scryne'da: Ming anlatıcısını dinleyip onaylamak.
