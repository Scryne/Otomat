---
proje: Otomat
created: 2026-10-02
type: roadmap
status: aktif
---
# Otomat — Roadmap

Durum sütunu session-start hook'u tarafından otomatik okunur — format bozulmasın:
⏳ Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı.

| Faz | Adı | Durum | Bitti Kriteri |
| --- | --- | --- | --- |
| 1 | İskelet ve sağlık | ⏳ Bekliyor | Private repo `Scryne/Otomat`; CI (ruff + pytest + duman koşusu) yeşil; `.github/dependabot.yml` (uv); `config/modeller.toml`; Actions runner'da qwen3:4b + Kokoro + render süresi ölçülmüş ve yazılmış |
| 2 | Veri ve olgu motoru | ⏳ Bekliyor | USGS, World Bank, Eurostat adaptörleri; her biri ≥ 20 farklı olgu paketi üretir (kaynak URL, zaman, hash); sözleşme testleri kayıtlı gerçek yanıtla; tekrar engeli çalışıyor |
| 3 | Görsel motor | ⏳ Bekliyor | Nokta harita, koroplet, sıralı çubuk şablonları; 1080×1920, bölgesel zoom, atıf köşesi; her şablondan 3 gerçek-veri videosu kare kare kontrol edildi; görsel kimlik `DESIGN.md`'de |
| 4 | Anlatım ve kapılar | ⏳ Bekliyor | Olgu şablon havuzu (tip başına ≥ 5 varyant); LLM kanca/başlık (yer tutucu); anlamsal hakem seçimi 30 etiketli cümleyle ölçüldü (yerel vs Jev, D-8); TTS + kelime zamanlı altyazı; 10 uçtan uca video, kapı sonuçları raporlu |
| 5 | Yayın ve audit | ⏳ Bekliyor | Scryne D1–D3'ü yaptı; OAuth "In production"; yükleyici + planlama + 5 dilli metadata + altyazı; GitHub Pages'ta uygulama/gizlilik/şartlar; audit başvurusu gönderildi; ilk video gerçek kanalda (private-kilitli olsa bile); Plan B paketi çalışıyor |
| 6 | Geri besleme ve işletim | ⏳ Bekliyor | Analitik toplayıcı; faktörlü Thompson sampling (konu, kanca); günlük cron 3 gün kesintisiz; haftalık rapor; `invalid_grant` ve koşu hatası alarmı |
| 7 | Gerçek kullanım | ⏳ Bekliyor | Final-Doküman'daki "bitti = kullanıldı" cümlesi gerçekleşti (14 gün, kod müdahalesiz); bulgular roadmap'e işlendi |
| 8 | Öldürme kriteri değerlendirmesi (tetiklemeli) | ⏳ Bekliyor | İlk public videodan 8 hafta sonra: son 56 günde ≥ 1,2M Shorts izlenmesi veya ≥ 200 abone ölçüldü; karar (sürdür / konsept değiştir / kapat) yazıldı |
| 9 | Reels ve görsel kolları (koşullu) | ⏳ Bekliyor | Faz 8 "sürdür" derse: aynı videolar Facebook/Instagram Reels'e; medya motorundan stok görsel kolu |

## Faz Detayları

Faz 1 ve "Gerçek kullanım" şablonla gelir: biri projenin sessizce çürümesini engeller, öbürü "bitti"yi kullanıma
bağlar. Aradaki fazlar projeye özeldir. Kararların gerekçesi `docs/Final-Dokuman.md` ve `docs/Proje-Fikri.md`
(Denetim D-1…D-10).

### Faz 1: İskelet ve sağlık
- **İşler:** `uv init` paket yapısı (`otomat/` altında `veri`, `anlati`, `gorsel`, `ses`, `yayin`, `haydut`, `rapor`);
  ruff + pytest; `.github/workflows/ci.yml` (lint, test, duman: tek videoluk kuru koşu, yüklemesiz);
  `.github/dependabot.yml` (`uv`); `config/modeller.toml` (qwen3 etiketi, Kokoro sürümü + hash); Actions'ta Ollama
  kurulumu ve model cache'i; private repo + Dependabot uyarıları. Spike kodu `spikes/`te kalır, ürün kodu yeniden yazılır.
- **Ölçülecek:** runner'da qwen3:4b ile 5 kanca üretim süresi, Kokoro 30 sn ses süresi, render süresi, cache geri yükleme
  süresi, toplam koşu dakikası → ayda dakika bütçesi.
- **Bitti Kriteri:** tablodaki gibi; ölçümler bu bölüme yazılır.
- **Notlar:**

### Faz 2: Veri ve olgu motoru
- **İşler:** adaptör arayüzü (`olgu_paketleri() -> list[OlguPaketi]`); USGS (son 30 gün, ülke bazında en güçlü,
  yıllık sayım), World Bank (askerî harcama/GSYH, borç, yaşam süresi, nüfus… gösterge listesi config'te), Eurostat
  (eğitim, GSYH, nüfus göstergeleri); ülke kodu eşleme (ISO A3 ↔ Natural Earth ↔ Eurostat geo); SQLite şeması;
  tekrar engeli (60 gün).
- **Bitti Kriteri:** tablodaki gibi.
- **Notlar:**

### Faz 3: Görsel motor
- **İşler:** üç şablon; kamera/zoom; ilk 1 sn'de kancayı görsel olarak taşıyan açılış; tipografi (OFL font) ve renk
  kimliği (`DESIGN.md`); kapak karesi; atıf köşesi.
- **Bitti Kriteri:** tablodaki gibi; kareler `gorsel-dogrulama` mantığıyla (taşma, okunurluk) gözle kontrol.
- **Notlar:**

### Faz 4: Anlatım ve kapılar
- **İşler:** olgu tipi → cümle şablon havuzu; LLM istemleri (kanca kalıbı parametreli); sayı/tutucu kapısı; anlamsal
  hakem (olgu paketi + cümle → destekleniyor mu); politika listesi (yasak ifade, tıbbi/siyasi iddia); Kokoro;
  Whisper kelime zamanları; yakılmış altyazı + SRT.
- **Ölçüm (D-8):** 30 cümle (15 doğru, 15 bilerek bozulmuş: yanlış nicelik, yanlış bağlam, veride olmayan iddia) →
  yerel hakem ve Jev'in yakalama/yanlış alarm oranı. Maliyetli seçenek K-1 gereği elenir.
- **Bitti Kriteri:** tablodaki gibi.
- **Notlar:**

### Faz 5: Yayın ve audit
- **Scryne dokunuşları:** D1 kanal + kanal e-postası, D2 Google Cloud projesi + OAuth onayı, D3 audit formu
  (`docs/Dokunus-Noktalari.md`; her biri için adım adım rehber bu fazda yazılır).
- **İşler:** OAuth akışı (yerelde bir kez, refresh token → Actions Secret); yükleyici (`videos.insert` + `publishAt`);
  `localizations` (EN, ES, PT, DE, FR); `captions.insert` (5 dil); GitHub Pages; audit başvuru metni; Plan B: haftanın
  videoları + metadata dosyası Actions artifact'ı olarak, Studio'da toplu yükleme rehberi.
- **Bitti Kriteri:** tablodaki gibi.
- **Notlar:**

### Faz 6: Geri besleme ve işletim
- **İşler:** analitik toplayıcı (günlük; `engagedViews`, `averageViewPercentage`; 72 sa olgunlaşma); ödül tanımı;
  konu ve kanca için ayrı Beta posteriorları; seçim logu; haftalık rapor şablonu; alarm.
- **Bitti Kriteri:** tablodaki gibi.
- **Notlar:**

### Faz 7: Gerçek kullanım
- **İşler:** 14 günlük koşu; Scryne'ın dokunuş süresinin kaydı; her gün kapı/yükleme sonuçlarının raporu.
- **Bitti Kriteri:** "bitti = kullanıldı" cümlesi.
- **Notlar:**
