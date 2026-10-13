---
name: calistir
description: Otomat'ı yerelde çalıştırma ve bir üretimi doğrulama tarifi — tek hikâyenin uçtan uca üretimi, yayın kabulü, günlük koşunun artifact'ını indirip kare kare inceleme, kanaldaki planlı videoların durumu. "çalıştır", "bir video üret", "son koşuyu incele", "kareleri göster", "kanalda ne planlı" dendiğinde kullan.
---

# Otomat'ı çalıştırma

Sunucu yok; ürün günlük GitHub Actions koşusu (`.github/workflows/gunluk.yml`). Yerelde üç iş yapılır.

## 1. Tek hikâyeyi uçtan uca üret (yayın yok)

```bash
OTOMAT_KANAL=uzay uv run python -m otomat.hikaye.uretim "ezop:The Fox And The Grapes"
OTOMAT_KANAL=earth uv run python -m otomat.hikaye.uretim "wiki:Great Molasses Flood"
```

Çıktı `calisma/hikaye_deneme/<kanal>/<anahtar>/` (video.mp4, sahne_*.jpg, meta.json, senaryo.json). Cloudflare
kotası harcar (~1.500-2.200 neuron; günlük 10.000, iki kanal ve Actions koşularıyla ORTAK, kayan 24 saat). Kota
doluysa `KotaHatasi` döner: kayan pencere açılana kadar bekle, Actions koşusunun slotunu yakma.

Kabul kapısı (yayından önceki son kontrol):

```bash
OTOMAT_KANAL=uzay uv run python -m otomat.hikaye.kabul calisma/hikaye_deneme/uzay/<anahtar>/meta.json
```

`KABUL` ya da `RED: <neden>`.

## 2. Günlük koşunun ürettiğini incele

```bash
gh run list --workflow gunluk.yml --limit 5
gh run download <run_id> -D <scratchpad>/kosu     # uretim-<kanal>-<run_id>-<deneme> artifact'ları (4 gün)
```

Her klasörde `senaryo.json` (satırlar, sahne tarifleri, `degisimler`), `meta.json` (`durum`, `yazi`, `referans`,
`hakem_turlari`), `sahne_*.jpg`. Kareleri tek sayfada görmek için 4 sütunlu bir kontak sayfası çıkar (PIL) ve
Read ile aç. Bakılacaklar: hikâyede değişen görünüş (kuyruk, taç) karede tutuyor mu, karakter kareden kareye aynı
mı, anlamsız yazı, masalda olmayan nesne/canlı, başlık ile hikâyenin tutarlılığı.

Kusurlu planlı videoyu geri çek (private, plan kalkar, slot boşalır; sonraki koşu yeniden üretir):

```bash
OTOMAT_KANAL=<kanal> uv run python -m otomat.yayin.youtube geri <video_id> "<neden>"
```

## 3. Kanalda ne planlı, durum veritabanıyla uyuşuyor mu

```bash
OTOMAT_KANAL=uzay uv run python -c "import datetime as dt, sqlite3; from otomat import durum, kanal; db=sqlite3.connect(f'file:{kanal.aktif().durum.as_posix()}?mode=ro', uri=True); s=dt.datetime.now(dt.UTC); print(durum.yayin_slotu(db, s), durum.pist_dolu(db, s, 'buffer'))"
```

Veritabanı salt okunur açılır: `durum.baglan()` şema göçü yazabilir, yerelde değişen `durum/*.db` botun commit'iyle
çakışır (iş akışı çakışmada koşunun sürümünü alır, yereldeki değişiklik kaybolur). Yerelde veritabanına yazan tek
komut `youtube geri`; ondan sonra hemen commit + push.

Günlük koşu her üretimde pist denetimi yapar (planı düşen videoyu yeniden planlar, kaybolanı alarm yapar) ve
çevirisi atlanan planlı videonun eksik dillerini tamamlar (pist doluysa bakım koşusunda); sonuç kanalın günlük
kaydında (`raporlar/gunluk.jsonl` Earth, `raporlar/uzay/gunluk.jsonl` Orbit) `pist` ve `ceviri_onarimi` alanlarında.

## Testler

```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```

Testler gerçek ağa çıkmaz; `durum/`, `raporlar/`, `sirlar/` dosyalarına yazmaz ve onları okumaz (tmp_path,
monkeypatch); kabuktaki `OTOMAT_KANAL`/`OTOMAT_YAYIN` ve sırlar `tests/conftest.py`'de ezilir. Hikâye hattının uçtan
uca testi (`tests/test_hikaye_uctan_uca.py`) gerçek render, karışım ve kabulle ~20 sn sürer.
