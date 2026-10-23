# Otomat

Sıfır sermayeyle YouTube içeriği üreten ve yayınlayan hat. Bugün yayındaki tek kol **One Ticket Back**: haftada bir
8-11 dakikalık, anlatıcılı, animasyonlu tarih filmi ("What if you joined the Klondike Gold Rush in 1897?", tek kişinin
ya da olayın gerçek hikâyesi) ve her filmden üç dikey kesit.

Her film kaynaklıdır: senaryo Wikipedia'nın sabit revizyonundan yazılır, her cümle kaynakla satır satır karşılaştırılır,
bitmiş anlatım Whisper'la geri dökülüp metinle ve sayılarla eşleştirilir.

Shorts kanalları durdu: Lanternbug Tales (Orbit, K-33, 2026-10-18) ve Inkwell Oddities Stories (Earth, K-35,
2026-10-23). Shorts motoru, profilleri ve testleri duruyor; geri açma tarifi `.github/workflows/gunluk.yml` başında.

## Nasıl çalışır

Film üretimi yerelde (GPU): ComfyUI'da FLUX.2 klein karakter kartı ve sahneler, Wan 2.2 klipleri, Chatterbox anlatım,
PIL + ffmpeg kurgu (`otomat/film/`). Yükleme kendi API projemizle private + `publishAt` (`otomat/film/yukle.py`;
kanal 24 saatte 10 video kabul ettiği için günde bir film + 3 kesit, Windows Görev Zamanlayıcı'dan). Haftalık film
raporu GitHub Actions'ta kendiliğinden yazılır (`raporlar/film/`).

Mimarinin tamamı: `docs/Final-Dokuman.md` ("Güncel mimari (film)"). Fazlar ve her fazda öğrenilenler: `docs/Roadmap.md`.

## Shorts motoru (durdu)

GitHub Actions (`.github/workflows/gunluk.yml`) günde dört kez tetikleniyordu; kanal başına bir iş, kanalın pistinde
(bugün + 2 gün) boş slot varsa üretiyordu. Senaryo, sahne görselleri, kare denetimi ve çeviri Cloudflare Workers AI'ın
bedava kotasıyla; ses Kokoro, render PIL + ffmpeg; yayın Buffer + YouTube Data API. Durum `durum/*.db`'de.

## Yerelde

```bash
uv sync --extra ses --extra gorsel
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
OTOMAT_KANAL=earth uv run python -m otomat.hikaye.uretim "wiki:Great Molasses Flood"   # tek hikâye, yayın yok
```

Tek hikâye üretimi, yayın kabulü, günlük koşunun artifact'ını kare kare inceleme ve kusurlu videoyu geri çekme:
`.claude/skills/calistir/SKILL.md`. Cloudflare kotası kayan 24 saattir; Shorts durduğu için günlük koşu artık
ondan harcamıyor.

## Dizinler

| Yol | İçerik |
| --- | --- |
| `otomat/film/` | film hattı: senaryo denetimi, ComfyUI, anlatım, kurgu, kesit, yükleme, haftalık rapor |
| `filmler/<id>/` | film senaryoları (`senaryo.json`) |
| `otomat/hikaye/` | Shorts hikâye motoru (durdu): kaynaklar, senaryo + hakem, Cloudflare istemcisi, üretim, yayın kabulü |
| `otomat/yayin/` | Buffer, YouTube, çeviri, kanal kimliği, Plan B teslim sayfası |
| `otomat/gunluk.py` | günlük koşu: pist, üretim, yayın, onarımlar, alarm |
| `otomat/analitik.py`, `haydut.py`, `rapor.py`, `portfoy.py` | ölçüm, kanca kalıbı seçimi, haftalık ve portföy raporu |
| `otomat/veri/`, `anlati/`, `gorsel/`, `uretim.py` | v1 veri videosu motoru (arşiv; `kanallar/veri-*` profilleri ve testleri) |
| `kanallar/<id>/` | kanal profili (`kanal.toml`), kimlik (`DESIGN.md`, `marka.toml`), hikâye havuzu |
| `docs/` | fikir, final doküman, roadmap, araştırmalar, marka kiti, kurulum rehberleri |
| `spikes/` | karar öncesi ölçüm betikleri (ürün kodu değil) |
