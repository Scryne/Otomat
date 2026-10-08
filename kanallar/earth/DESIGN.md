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
