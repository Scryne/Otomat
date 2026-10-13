---
version: alpha
name: Otomat
description: Açık veriden kodla üretilen dikey (9:16) harita ve sıralama Shorts'larının görsel kimliği.
colors:
  surface: "#0b1220"
  land: "#1a2434"
  land-edge: "#26334a"
  no-data: "#1f2a3b"
  ink-primary: "#f2f5f9"
  ink-secondary: "#a9b4c4"
  ink-muted: "#6b7890"
  primary: "#ee5a2a"
  data: "#4a8fe6"
  seq-1: "#184f95"
  seq-2: "#256abf"
  seq-3: "#3987e5"
  seq-4: "#6da7ec"
  seq-5: "#b7d3f6"
typography:
  display:
    fontFamily: Barlow Condensed
    fontWeight: 700
    fontSize: 112px
    lineHeight: 1.0
  title:
    fontFamily: Barlow Condensed
    fontWeight: 600
    fontSize: 64px
    lineHeight: 1.05
  label:
    fontFamily: Barlow
    fontWeight: 500
    fontSize: 36px
    lineHeight: 1.2
  caption:
    fontFamily: Barlow
    fontWeight: 400
    fontSize: 24px
    lineHeight: 1.2
rounded:
  bar: 4px
spacing:
  safe-top: 150px
  safe-bottom: 380px
  safe-side: 64px
  safe-right: 150px
---

# Otomat

> **Arşiv kimliği.** Bu dosya v1 veri videolarının (harita, koroplet, sıralı çubuk) görsel kimliğidir; bugün yalnız
> arşiv profili `kanallar/veri-earth` okur (`kanal.toml` `tasarim`, `test_kanal.py` kilitler). Yayındaki hikâye
> kanallarının kimliği `kanallar/earth/DESIGN.md` (Inkwell Oddities) ve `kanallar/uzay/DESIGN.md` (Lanternbug Tales).

## Overview

Bu proje web arayüzü değil, **video karesi** üretir: 1080×1920, 30 fps, matplotlib ile kodla çizilen harita ve
sıralama animasyonları. Global dark glassmorphism kuralları burada uygulanmaz. Cam, blur ve gradient mesh bir telefon
ekranında, sıkıştırılmış ve 1 saniyede kaydırılan bir videoda okunurluğu düşürür. Bu dosya o varsayılanı ezer.

- **Mood:** gece görevi gören bir harita masası. Sakin, lacivert, tek bir sıcak sinyal. Belgesel ciddiyeti, ama
  ilk saniyede büyük ve iri bir rakamla merak uyandırır.
- **Farklılaştırıcı detay:** her videoda tek bir turuncu vurgu, yalnız "bakman gereken şey" için (en güçlü deprem,
  1. sıradaki ülke, şu an beliren olay). Geri kalan her şey mavi ya da gri. Rakip harita kanallarının bayrak ve
  gökkuşağı paletinden bilerek ayrılır.

## Colors

- `surface` saf siyah değil, lacivert. Sıkıştırmada siyah bloklaşır, lacivert yumuşak kalır.
- `primary` ve `data` dataviz doğrulayıcısından geçti (koyu mod, `surface` üzerinde): açıklık bandı, chroma, renk körlüğü
  ayrımı ΔE 26, normal görüş ΔE 32, kontrast ≥ 3:1. Aynı karede ikisinden başka doygun renk yok.
- Koroplet tek tonlu sıralı rampa kullanır: `seq-1` (düşük) → `seq-5` (yüksek). Koyu zeminde büyüklük
  **parlaklıkla** artar, rampa bu yüzden koyudan açığa gider. Veri olmayan ülke `no-data`, hiçbir rampa adımıyla
  karışmaz.
- Metin her zaman `ink-*` tonlarında yazılır, seri rengini taşımaz. Turuncu bir değerin yanında turuncu bir işaret
  durur, metnin kendisi beyazdır.

## Typography

- Barlow Condensed (başlık, büyük rakam) + Barlow (etiket, açıklama), ikisi de OFL ve `otomat/varliklar/fontlar/`
  içinde gelir (runner'da sistem fontu yok). Dar kesim, dikey kadrajda uzun ülke adlarını tek satıra sığdırır.
- `display` yalnız tek bir kahraman rakam içindir (sayaç, 1. sıradaki değer). Karede iki `display` olmaz.
- Rakamlar binlik ayraçlı yazılır (`1,047`). Birim rakamdan sonra `label` boyutunda gelir.

## Components

- **Güvenli alan:** YouTube Shorts arayüzü altta ~%20'yi (başlık, kanal adı, abone düğmesi) ve sağda ~%14'ü (beğeni,
  yorum, paylaş) örter. Önemli içerik `safe-*` sınırlarının içinde kalır. Altyazı alt güvenli sınırın hemen üstünde,
  ortalı, `title` boyutunun %85'i, zemin renginde kalın kontur; kanca kartı açıkken gösterilmez.
- **Kanca kartı:** kanca seslendirilirken (1,5–3 sn) ekranın üst yarısında kanca cümlesi `title` boyutunda, harita arkada `surface`
  üstünde %40 karartılmış. Kart kalkınca veri hareketi başlar. Kaydırma kararı ilk saniyede verilir.
- **Nokta harita:** olay `data` ile değil `primary` ile belirir (halka genişleyip söner), sonra `primary` %35 opaklıkta
  nokta olarak kalır. Büyüklük alanla kodlanır. Bölge videosunda kamera olayların kutusuna yakınlaşır.
- **Sıralı çubuk:** geri sayım: 10. sıradan 1. sıraya doğru birer birer gelir. Çubuklar `data`, yalnız 1. sıra
  `primary`. Çubuk uçları 4 px yuvarlak, çubuklar arası 2 px+ boşluk. Ortanca değer ince `ink-muted` kesikli çizgi.
- **Koroplet:** ülkeler değere göre rampadan dolar. İlk 3 ülke `primary` kenar çizgisi ve etiketle işaretlenir.
  Haritada çizilemeyecek kadar küçük ülke (Singapur, Bahreyn) merkez noktasında daire ile gösterilir.
- **Atıf:** her karede sol altta, güvenli alanın içinde `caption`, `ink-muted`: "Data: USGS" vb.

## Do's and Don'ts

- Gökkuşağı ya da bayrak renkleriyle koroplet yapma.
- Turuncuyu ikinci bir şey için kullanma. İki vurgu hiç vurgu olmamaktır.
- Glassmorphism, blur, gradient mesh, parıltı efekti kullanma (bkz. Overview).
- Altta %20'lik ve sağda %14'lük Shorts arayüz bölgesine metin ya da kilit veri koyma.
- Ekranda okunamayacak kadar küçük metin yazma: 1080 genişlikte en küçük boyut `caption` (24 px).
