---
proje: Otomat
created: 2026-10-02
type: final-dokuman
status: onaylandi
---
# Otomat — Final Doküman

Kaynak: `docs/Proje-Fikri.md` (denetlendi, D-1…D-10 ve K-1…K-8), `docs/arastirma/01–04`, `spikes/`.
Scryne yetkiyi devretti ("her şeyi sana bırakıyorum", 2026-10-02); kararlar bu yetkiyle kapandı.

## Özet

Otomat, sıfır sermayeyle çalışan otomatik gelir botlarının şemsiyesidir. İlk kol **Shorts fabrikası v2**: açık
veriden (USGS, World Bank, Eurostat) olgu paketi çıkarır, olguyu kod şablonuyla cümleye, merak çerçevesini yerel
bir LLM ile kancaya çevirir, kodla harita/grafik animasyonu üretir, yerel TTS ile seslendirir, anlamsal hakemden
geçirip YouTube'a beş dilli metadata ve altyazıyla yükler. YouTube Analytics'ten gelen geri bildirimle hangi konu
ve kancanın tuttuğunu öğrenir. GitHub Actions'ta her gün kendiliğinden çalışır; Scryne'ın haftalık yükü ≤ 10 dk.

## Teknoloji Stack

| Katman | Seçim | Gerekçe |
| --- | --- | --- |
| Dil, paket | Python 3.12, `uv` | Spike'lar Python'da çalıştı; veri, görsel ve ses kütüphaneleri Python'da en olgun |
| Çalışma yeri | GitHub Actions (private repo, cron) | K-6/D-5: bilgisayar kapalıyken de çalışır; ayda ~300 dk, bedava kota 2.000 dk. Model dosyaları Actions cache'inde |
| Veri | USGS FDSN/GeoJSON, World Bank API v2, Eurostat API (JSON-stat) | Üçü de ticari kullanıma açık (USGS kamu malı, diğerleri CC BY 4.0 + atıf); anahtarsız |
| Harita tabanı | Natural Earth 1:110m/1:50m (GeoJSON) | Kamu malı; ülke kodu (ISO A3) World Bank/Eurostat ile birleşir |
| Görsel | matplotlib (Agg) + ffmpeg (imageio-ffmpeg) rawvideo pipe | S4: 30 sn 1080×1920 video 17 sn'de, CPU. Ek bağımlılık ve tarayıcı yok |
| LLM (kanca, başlık, çeviri, hakem) | Ollama + qwen3:4b-instruct (varsayılan), gemma3:4b (yedek) | K-1 bedava, yerel; düşünmesiz model, runner'da kanca ~3,5 sn (Faz 1 ölçümü). Model kimliği `config/modeller.toml`'da (sağlık nöbeti izler) |
| Anlamsal hakem | Yerel qwen3 ile Jev arasında Faz 4 ölçümü | D-8: maliyetsiz olan ve daha çok yanlış yakalayan kazanır |
| TTS | Kokoro v1.0 ONNX (`kokoro-onnx`), tek kanal sesi `am_michael` | S3: Apache-2.0, CPU'da gerçek zamanın ~4 katı; Whisper geri dökümü birebir |
| Altyazı zamanlaması | faster-whisper (small, int8) kelime zaman damgası, bilinen metne hizalama | Ses bizim ürettiğimiz metin; Whisper yalnız zamanlamayı verir |
| Yükleme | YouTube Data API v3 (`google-api-python-client`, `google-auth-oauthlib`) | `videos.insert` 1 birim; `localizations` + `captions.insert` (400 birim) |
| Analitik | YouTube Analytics API (`yt-analytics.readonly`) | `engagedViews`, `averageViewPercentage`; 48–72 sa gecikme |
| Durum | Repo içi SQLite (`durum/otomat.db`), her koşu sonunda commit | Ek servis yok; geçmiş git'te |
| Sırlar | GitHub Actions Secrets (OAuth client + refresh token) | Koda ve repoya girmez |
| Kalite | ruff, pytest | CI: lint + test + "duman" (tek videoluk kuru koşu, yüklemesiz) |
| Audit sayfası | GitHub Pages (statik HTML: uygulama tanımı + gizlilik politikası + şartlar) | Bedava https; kişisel veri yok (D-9) |

## Mimari

Her koşu bir **boru hattı**dır; her aşama girdisini ve çıktısını diske (`calisma/<koşu-id>/`) yazar, bir aşama
düşerse koşu o videoyu bırakır, diğerine geçer, hata durumu rapora girer.

```
cron (Actions, günde 1)
  └─ seçici ── haydut (konu kolu, kanca kalıbı) ← analitik (geçmiş videolar, SQLite)
       └─ adaptör (USGS | World Bank | Eurostat) → olgu paketi (JSON, kaynak URL + çekim zamanı + hash)
            └─ tekrar kontrolü (aynı olgu/aynı açı son 60 günde var mı)
                 └─ anlatım: olgu cümleleri (kod şablonu, çeşitli) + kanca/başlık (LLM, yer tutucu)
                      └─ kapılar: (1) sayı/tutucu kapısı (2) anlamsal hakem (3) politika listesi
                           └─ görsel şablon (nokta harita | koroplet | sıralı çubuk) → sessiz video
                                └─ TTS → ses; Whisper → kelime zamanları → yakılmış altyazı + SRT
                                     └─ ffmpeg birleştirme → video.mp4 + kapak karesi
                                          └─ metadata: başlık/açıklama/etiket EN + ES/PT/DE/FR çeviri (LLM) + atıf
                                               └─ yayın: API yükleme + planlama (audit varsa)
                                                    │   ya da Plan B: Actions artifact (haftalık paket)
                                                    └─ kayıt: SQLite + rapor
cron (Actions, günde 1, ayrı iş) → analitik toplayıcı → SQLite → haydut parametreleri
cron (haftalık) → raporlar/YYYY-WW.md (üretilen, düşen, yüklenen, en iyi/kötü video, haydut durumu, dokunuş süresi)
```

Önemli tasarım kararları:
- **K-4 Olgu koddan, çerçeve modelden.** LLM hiçbir sayı ya da özel ad üretmez; `{yer_tutucu}` yazar. Olgu cümleleri her
  olgu tipi için en az 5 varyantlı şablon havuzundan seçilir (politika: şablon tekrarı riski).
- **Kapı başarısızsa yayın yok** (K-3). Aynı koşuda bir kez yeniden üretilir; ikinci kez düşerse video bırakılır.
- **Tekrar engeli:** olgu paketi hash'i + (kol, ülke/bölge, gösterge) üçlüsü 60 gün içinde tekrar edilmez (videodaki
  botun %91 benzerlik eşiğinin bizdeki karşılığı, ama veride).
- **Hacim:** günde 1 video (v1). Artış, öldürme kriteri penceresindeki veriye göre karar olur.
- **Çok dil:** metin katmanı bizde (5 dil), ses katmanı YouTube'un otomatik dublajında (K-8).
- **Atıf:** her videonun alt köşesinde "Data: <kaynak>", açıklamada kaynak bağlantısı ve lisans (D-10).

## Kapsam (v1)

- **Süre tavanı:** ~4 hafta (Faz 1–6). Faz 7 takvim olarak 14 gün sürer.
- **Bitti = kullanıldı:** Bot 14 gün boyunca kod müdahalesi olmadan her gün en az bir video üretti, doğrulama kapısından
  geçenleri gerçek kanala yükledi (audit varsa otomatik; yoksa Plan B ile Scryne'ın haftalık toplu yüklemesi); analitik
  geri beslemesi en az bir seçimi değiştirdi (logda görünür); iki haftalık rapor repoya düştü. Scryne'ın toplam dokunuş
  süresi raporda yazar ve haftada 10 dakikayı geçmez.
- **Kollar:** USGS deprem (gerçek veriyle çerçeve), World Bank (duygusal çerçeveli sıralama), Eurostat (Avrupa ülke ülke).
- **Kanca kalıpları:** soru, "your country / each country", duygusal etiket, ölçek/çarpıtma.

## Riskler ve Doğrulamalar

| Risk | Durum | Önlem |
| --- | --- | --- |
| Görsel üretim yavaş/ağır | ✅ S4: 17 sn, CPU | — |
| TTS anlaşılmaz | ✅ S3: üç dilde birebir geri döküm | Doğallık Faz 4'te ilk 10 videoda kulakla (Scryne'a opsiyonel örnek) |
| LLM uydurur | ⚠️ S5/S6: sayı kapısı geçti, anlam hatası sürdü | K-4 + anlamsal hakem (Faz 4 ölçümü) |
| API yükleme kilidi | ⚠️ S2: audit olmadan private | Faz 5'te audit başvurusu; Plan B haftalık toplu yükleme; Studio otomasyonu yok |
| Audit reddi ya da sessizlik | açık | Plan B kalıcı olabilir; dokunuş haftada ≤ 10 dk sınırı içinde |
| "Inauthentic content" | açık | Veri + farklı açı, şablon varyantı, günde 1, tekrar engeli; atıf |
| Düz veri izlenmez | ✅ S1: çerçeve şart | Haydut konu × kanca öğrenir; öldürme kriteri 8. hafta |
| Actions runner LLM'i kaldırmaz | açık | Faz 1 ölçümü; qwen3:4b varsayılan; gerekirse kanca/başlık üretimi daha küçük modele |
| OAuth token 7 günde düşer | ✅ S2 araştırması | OAuth uygulaması "In production" (unverified ekranı tek kullanıcıya meşru); `invalid_grant` alarmı |
| Veri kaynağı değişir | açık | Adaptör başına sözleşme testi (gerçek yanıt şeması); kırılırsa o kol durur, diğerleri sürer |

## Kapsam Dışı

- Facebook/Instagram Reels çapraz yayını, stok görsel ve baskı tasarım kolları (v2, aynı medya motoru).
- NOAA GHCN rekorları, uzay ölçeği, "what if" senaryoları (D-2, D-3).
- Kokpit/vault rapor entegrasyonu (D-7).
- Oyun fabrikası, Apify mağazası, Telegram Stars botu (ayrı motorlar, sonraki projeler).
- TikTok, trade botu, ücretli her şey (K-1).
