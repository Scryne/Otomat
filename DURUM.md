# DURUM — Otomat

> Envanter, sertifika değil. Faz durumu `docs/Roadmap.md`'de; ScryneOS'taki proje notu ilişkisel kayıt.

**Ölçüm tarihi:** 2026-11-26

**Yayına hazır karnesi (2026-11-26):** Kod ✅ · Ürün ✅ (günlük üretim Actions'ta yeşil; trend v3 hattı 11-26'da Riemann
videosunu uçtan uca üretti) · Ön yüz ⚪ (arayüz yok; `site/` yalnız gizlilik/şartlar) · Belge ✅ · Kapı ✅ · Dış adımlar aşağıda.

## Ölçüm

- pytest 455 (+1 atlanan), ruff temiz, CI yeşil.
- Trend v3 (11-26): anlatıcı Ming-3.0-tts UK_George (AA kör tercih 1181 ELO; eski Qwen3 931), konuşma dili yazım
  kuralları, görsel ağırlıklı senaryo, baskı düzeni, görsel süzgeci, kesitli kapak, yakın plan kesmesi. Ayrıntı:
  `docs/arastirma/14-trend-kanali.md` bölüm 9.
- Disk dar (~7 GB boş): 7 dk'lık render 4 işçiyle ~14 GB istiyor, hat tek işçiye düşüyor (~25 dk).
- Faz 18 kararı kaydedildi (Roadmap): filmler gösterim almıyor, yeni film yok; One Ticket Back'in kaderi Faz 8'de (12-19).

## Dış adımlar (Scryne)

1. Yeni anlatıcıyı dinleyip onaylamak (`calisma/trend/ses_ornekleri/7-…` eski, `8-…` yeni). Yetmezse tek ücretli
   seçenek ElevenLabs (Starter $6/ay).
2. Trend açıklayıcı kanalının ("Why It's Everywhere") açılması ve YouTube yetkisi (Faz 20).
3. 12-19 Faz 8 öldürme ölçümünün sonucuna göre One Ticket Back için karar.

## v2 fikirleri

- Görsel süzgece küçük resim vermek (başlığı masum, içeriği alakasız fotoğraf: Göttingen kütüphanesi yıkıntısı).
- HyperFrames 0.9.19 → güncel: `check` (yüz üstü metin, güvenli alan) ve `measure` kalite kapısı olarak.
