---
version: alpha
name: Earth (true stories)
description: Gerçek tuhaf hikâyeler kanalının dikey (9:16) video kimliği — masal kitabı illüstrasyonu, büyük altyazı.
colors:
  ink-primary: "#ffffff"
  ink-stroke: "#000000"
  highlight: "#FFD84D"
typography:
  caption:
    fontFamily: Barlow Condensed
    fontWeight: 700
    fontSize: 104px
    lineHeight: 1.0
    textTransform: uppercase
---
# Earth — gerçek tuhaf hikâyeler

> **Kart biçimi (2026-10-14, K-25):** Earth artık aşağıdaki sahneli anlatımı değil kartı yayınlar (`bicim = "kart"`).
> 1080×1920, 8 sn, anlatıcısız: koyu zemin (#0C0C0E); en üstte kanal adı (Barlow Medium 34, gri); kanca (Barlow
> Condensed Bold 92→68, büyük harf, sarı, en çok iki satır); 3-5 cümlelik paragraf (Barlow Medium 56→40, beyaz,
> `[[vurgu]]`lar sırayla sarı #FFD84D / turuncu #FF8A3D / yeşil #7FE07A, ince siyah kontur); altında makalenin Commons
> görseli (yoksa tek AI illüstrasyonu), üst ve alt kenarı zemine 60 px geçişli, ekranın %78'ine kadar; altında atıf
> satırı (Barlow Regular 24, gri). Alt ~420 px Shorts arayüzüne bırakılır. Görsel 8 sn'de yaklaşıp başa döner (cos):
> döngüde sıçrama yok. Müzik tek ses, -16 LUFS. Gerekçe: `docs/arastirma/10-rakip-kart.md`. Aşağısı sahne biçimidir
> (Orbit aynı motoru kendi kimliğiyle kullanır).

**Ne:** Wikipedia'nın "Unusual articles" listesinden tek bir gerçek olay, 7-8 sahnede, ~35 sn.

**Görsel dil:** Her sahne kendi illüstrasyonu (flux-2-klein-4b, 768×1344): mürekkep çizgi + soluk suluboya, sıcak kâğıt
dokusu, sinematik kadraj. Stil metni `kanal.toml`'daki `stil`; dönem/mekân/kıyafet hikâye başına `world` cümlesiyle
sabitlenir, tekrar eden karakterler `cast` tarifleriyle. Gerçekçi değil, açıkça illüstrasyon: YouTube'un sentetik içerik
bildirimi gerekmez (docs/arastirma/08).

**Hareket:** Sahne başına yavaş Ken Burns (%10 yakınlaş/uzaklaş, sırayla), sert kesme. Kâğıt kenarı görünmesin diye
%16 kırpma.

**Altyazı:** Barlow Condensed Bold, büyük harf, beyaz + kalın siyah kontur, ekranın %66'sında; aynı anda en çok 3
kelime, o an söylenen kelime sarı (`highlight`). İlk karede ilk kelime ekranda: kaydırmayı durduracak olan ilk görüntü
ve ilk cümle.

**Ses:** Kokoro `bm_george` (İngiliz anlatıcı), 1,08×. Müzik hikâyenin ruh hâline göre Kevin MacLeod (CC BY 4.0), sesin
altında (-30 LUFS; anlatıcı -14, karışım limiter sonrası ≈ -14 LUFS), sonda 1,5 sn sönüş.
