# Otomat

Sıfır sermayeyle, insan dokunuşu olmadan her gün YouTube Shorts üreten ve yayınlayan hat. İki kanal:

- **Inkwell Oddities** (`kanallar/earth`): Wikipedia'nın "Unusual articles" listesinden gerçek, tuhaf hikâyeler.
- **Lanternbug Tales** (`kanallar/uzay`): Ezop masalları, yumuşatılmadan, yetişkinlere.

Her video kaynaklıdır: senaryodaki her olgu kaynak metinle kod kapısında ve bir hakem modelinde denetlenir. Kapıdan
ya da yayın kabulünden geçmeyen video kanala çıkmaz.

## Nasıl çalışır

GitHub Actions (`.github/workflows/gunluk.yml`) günde dört kez tetiklenir; kanal başına bir iş, kanalın pistinde
(bugün + 2 gün) boş slot varsa üretir. Senaryo, sahne görselleri, kare denetimi ve çeviri Cloudflare Workers AI'ın
bedava kotasıyla; ses Kokoro, render PIL + ffmpeg; yayın Buffer + YouTube Data API. Durum `durum/*.db`'de, her koşu
sonunda repoya yazılır. Sorun olursa "alarm" etiketli issue açılır, temiz koşu kapatır.

Mimarinin tamamı: `docs/Final-Dokuman.md` ("Güncel mimari"). Fazlar ve her fazda öğrenilenler: `docs/Roadmap.md`.

## Yerelde

```bash
uv sync --extra ses --extra gorsel
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
OTOMAT_KANAL=earth uv run python -m otomat.hikaye.uretim "wiki:Great Molasses Flood"   # tek hikâye, yayın yok
```

Tek hikâye üretimi, yayın kabulü, günlük koşunun artifact'ını kare kare inceleme ve kusurlu videoyu geri çekme:
`.claude/skills/calistir/SKILL.md`. Cloudflare kotası günlük koşuyla ortaktır (kayan 24 saat); yerel denemeler
günlük koşudan sonra yapılır.

## Dizinler

| Yol | İçerik |
| --- | --- |
| `otomat/hikaye/` | hikâye motoru: kaynaklar, senaryo + hakem, Cloudflare istemcisi, üretim, yayın kabulü |
| `otomat/yayin/` | Buffer, YouTube, çeviri, kanal kimliği, Plan B teslim sayfası |
| `otomat/gunluk.py` | günlük koşu: pist, üretim, yayın, onarımlar, alarm |
| `otomat/analitik.py`, `haydut.py`, `rapor.py`, `portfoy.py` | ölçüm, kanca kalıbı seçimi, haftalık ve portföy raporu |
| `otomat/veri/`, `anlati/`, `gorsel/`, `uretim.py` | v1 veri videosu motoru (arşiv; `kanallar/veri-*` profilleri ve testleri) |
| `kanallar/<id>/` | kanal profili (`kanal.toml`), kimlik (`DESIGN.md`, `marka.toml`), hikâye havuzu |
| `docs/` | fikir, final doküman, roadmap, araştırmalar, marka kiti, kurulum rehberleri |
| `spikes/` | karar öncesi ölçüm betikleri (ürün kodu değil) |
