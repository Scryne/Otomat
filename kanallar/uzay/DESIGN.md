---
version: alpha
name: Cosmic Yardstick
description: Uzay kanalının dikey (9:16) video kimliği — yakın geçen asteroitler ve ötegezegenler, ölçekle anlatılır.
colors:
  surface: "#04050b"
  land: "#141a2e"
  land-edge: "#232b45"
  no-data: "#181d30"
  ink-primary: "#eef1ff"
  ink-secondary: "#9aa3c7"
  ink-muted: "#5d6588"
  primary: "#5ef0c8"
  data: "#8b7cf6"
  earth: "#3f86f2"
  moon: "#c9ccd8"
  seq-1: "#3b2f8f"
  seq-2: "#5444b8"
  seq-3: "#6f5fd9"
  seq-4: "#9a8ef0"
  seq-5: "#cbc4fa"
typography:
  display:
    fontFamily: Space Grotesk
    fontWeight: 700
    fontSize: 104px
    lineHeight: 1.0
  title:
    fontFamily: Space Grotesk
    fontWeight: 700
    fontSize: 58px
    lineHeight: 1.08
  label:
    fontFamily: Space Grotesk
    fontWeight: 500
    fontSize: 34px
    lineHeight: 1.2
  caption:
    fontFamily: Space Grotesk
    fontWeight: 400
    fontSize: 24px
    lineHeight: 1.2
rounded:
  bar: 0px
spacing:
  safe-top: 150px
  safe-bottom: 380px
  safe-side: 64px
  safe-right: 150px
layout:
  title-align: center
  hook-y: 0.5
  caption-y: 0.26
  attribution-align: center
---

# Cosmic Yardstick

Earth in Numbers'tan bilerek ayrışan ikinci kanal kimliği (docs/arastirma/07, K-11). Aynı motor, farklı görünüş:
farklı renk ailesi, farklı font, ortalanmış başlık ve farklı sahne yerleşimi. Global dark glassmorphism burada da
uygulanmaz (video karesi, telefon ekranı, sıkıştırma).

## Overview

- **Mood:** gece gökyüzü planetaryumu. Neredeyse siyah zemin, soğuk mor veri tonları, tek bir nane yeşili vurgu.
- **Farklılaştırıcı detay:** her şey **ölçekle** anlatılır: Ay'ın yörüngesi bir cetvel halkası, asteroit boyutu bir
  binanın yanında, gezegen boyutu Dünya ve Jüpiter'in yanında. Vurgu rengi yalnız videonun öznesinde.
- **Ses:** Kokoro `af_heart` (Earth'teki `am_michael`'dan ayrı).

## Colors

- `surface` neredeyse siyah; `earth` mavi yalnız Dünya diski; `moon` gri yalnız Ay ve yörüngesi.
- `primary` (nane) videonun öznesi: asteroitin geçiş çizgisi, öne çıkan gezegen. Başka hiçbir şey vurgulanmaz.
- `data` ve `seq-*` mor ailesi: ikincil asteroitler, listedeki diğer gezegenler, ölçek halkaları.

## Typography

Space Grotesk (OFL, `otomat/varliklar/fontlar/`). Başlık ortada, iki satırı geçmez.

## Layout

- Başlık üstte ortalı; kanca kartı tam ortada; altyazı alt güvenli alanın biraz üstünde (0,26); atıf altta ortalı.
- Güvenli alanlar Earth ile aynıdır: bunlar YouTube Shorts arayüzünün kapladığı yerlerden gelir, kimlik değildir.

## Components

- **Yakın geçiş (`yakin_gecis`):** ortada Dünya, Ay yörüngesi halkası (1 Ay mesafesi), karekök ölçekli mesafe
  halkaları ("5× Moon", "10× Moon"). Her asteroit, en yakın noktası kendi mesafesinde olan düz bir çizgiyle geçer.
  Tekil videoda sonda boyut karşılaştırması (bilinen yapılar, tahmini aralık kesik çizgiyle).
- **Ölçek (`olcek`):** gezegen kipi Dünya, Neptün, Jüpiter ve özneyi aynı ölçekte yan yana daireler olarak gösterir;
  liste kipi sekiz gezegeni boyutlarıyla daire olarak dizer, değer yanında yazılır.

## Do's and Don'ts

- Do: tahmini değerleri "estimated" diye yaz; çap her zaman aralıktır.
- Don't: çarpma, tehlike, felaket dili; kırmızı alarm rengi; sanatçı çizimi gibi gerçek görünen gezegen dokusu.
