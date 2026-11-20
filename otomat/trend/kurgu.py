"""Trend açıklayıcı videonun HyperFrames projesi: plan (sahneler + kelime zamanları) → HTML kompozisyon → MP4.

Neden HyperFrames (docs/arastirma/14-trend-kanali.md): film hattının PIL kamerası tek görsel üstünde yavaş kaydırma
yapıyordu ("slayt" hissi). Burada her sahne anlatımın kelime zamanlarına bağlı hareketli grafik: görünen her parça
anlatıcı onu söylediğinde gelir (HyperFrames film.md: "her şey sahnenin ilk çeyreğinde gelip donarsa slayt olur").

Sahne türleri (plan["sahneler"][i]["tur"]) ve beklenen alanlar:
  foto      gorsel, kredi, [baslik], [vurgu], [etiket]      tam ekran fotoğraf + yavaş kamera + kinetik başlık
  manset    gorsel?, manşetler[{kaynak, baslik, ipucu?}]      haber kupürleri sırayla düşer
  sayi      deger, [on], [son], etiket, [renk]              renk zemininde büyük sayı sayarak gelir
  alinti    metin, kim, [gorsel]                             alıntı posteri, kelimeler griden beyaza
  zaman     olaylar[{tarih, olay, ipucu?}]                   zaman çizgisi, kamera düğümden düğüme gider
  bolum     no, baslik                                       bölüm kartı (renk seli)
  ikili     sol{etiket, deger}, sag{etiket, deger}, [baslik] iki taraf karşılaştırma
  ifade     metin, [gorsel], [vurgu]                         tek büyük cümle (soru / tez), kelime kelime
  kapanis   metin, kanal                                     son fikir + kanal adı

Ortak: her sahnede `anlatim` (seslendirilen metin), zamanlamadan gelen `bas`, `sure`, `kelimeler` [{w, s, e}]
(sahne başına göreli saniye). `ipucu` bir kelime ya da öbek: o parça anlatıcı onu söylediğinde görünür.

Kural kaynakları: HyperFrames paketindeki skills/hyperframes/references (story, motion, film, captions, review).
"""

from __future__ import annotations

import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

GENISLIK, YUKSEKLIK = 1920, 1080
FPS = 30
HF_SURUM = "0.9.19"  # sabit (2026-11-06); güncellemek bilinçli bir karar
HF_ORTAM = {"HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1",
            "HYPERFRAMES_SKIP_SKILLS": "1"}  # fmt: skip

# Kimlik (kanal DESIGN.md'si gelince oradan okunacak): yayın grafiği; zemin hep içerik ya da doygun renk alanı.
RENK = {"murekkep": "#0F0F10", "kagit": "#F4F2EC", "vurgu": "#FFD60A", "kirmizi": "#FF3B2F", "mavi": "#1F6FEB",
        "gri": "#8A8A8E"}  # fmt: skip
GOVDE_FONT = "Roboto"
BASLIK_FONT = "League Gothic"

GECISLER = ("savur", "zoom", "perde", "kesme", "savur", "sel")  # dönüşümlü; kesme en çok üçte bir


def _e(s: str) -> str:
    return html.escape(str(s), quote=True)


def _kelime_ayir(metin: str) -> list[str]:
    return [k for k in re.split(r"\s+", metin.strip()) if k]


def _sade(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", k.lower())


def ipucu_zamani(sahne: dict, ipucu: str | None, yedek: float) -> float:
    """`ipucu` öbeğinin anlatımda söylendiği an (sahneye göre saniye); bulunamazsa `yedek`."""
    if not ipucu:
        return yedek
    hedef = [_sade(k) for k in _kelime_ayir(ipucu)]
    hedef = [h for h in hedef if h]
    kel = sahne.get("kelimeler") or []
    sade = [_sade(k["w"]) for k in kel]
    if not hedef:
        return yedek
    for i in range(len(sade) - len(hedef) + 1):
        if sade[i : i + len(hedef)] == hedef:
            return max(0.0, kel[i]["s"] - 0.08)
    for i, s in enumerate(sade):  # tek kelime yakalaması (ilk anlamlı kelime)
        if s == hedef[0] and len(s) > 3:
            return max(0.0, kel[i]["s"] - 0.08)
    return yedek


def _yayilim(sure: float, n: int, bas_oran: float = 0.12, son_oran: float = 0.72) -> list[float]:
    """İpucu yoksa parçalar sahnenin bas..son aralığına yayılır (ilk çeyrekte hepsi birden gelmesin)."""
    if n <= 0:
        return []
    if n == 1:
        return [sure * bas_oran]
    a, b = sure * bas_oran, sure * son_oran
    return [a + (b - a) * i / (n - 1) for i in range(n)]


# ---------------------------------------------------------------------------------------------- ortak CSS
def _ortak_css() -> str:
    return f"""
    #root {{ position:absolute; inset:0; overflow:hidden; background:{RENK["murekkep"]};
             font-family:'{GOVDE_FONT}', sans-serif; color:{RENK["kagit"]}; }}
    .tam {{ position:absolute; inset:0; }}
    .kat {{ position:absolute; inset:0; will-change:transform; }}
    .kat img, img.kapla {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
    .kredi {{ position:absolute; right:40px; bottom:28px; font-size:18px; letter-spacing:.02em;
              color:rgba(255,255,255,.82); background:rgba(0,0,0,.45); padding:4px 10px; border-radius:3px; }}
    .gb {{ font-family:'{BASLIK_FONT}', 'Oswald', sans-serif; font-weight:400; text-transform:uppercase;
           line-height:.92; letter-spacing:.005em; }}
    .w {{ display:inline-block; white-space:pre; }}
    .vurgu {{ color:{RENK["vurgu"]}; }}
    .perde {{ position:absolute; inset:0; z-index:50; }}
    """


ILK_EN_GEC = 0.12  # sahnenin ilk öğesi en geç bu anda (11-20: ipucu geç gelince sayı sahnesi 5 sn boş kaldı)


def ilk_an(sh: dict, ipucu: str | None, yedek: float = 0.3) -> float:
    """Sahnenin ilk (ana) öğesinin anı: ipucu erken söyleniyorsa o, değilse ILK_EN_GEC."""
    return min(ipucu_zamani(sh, ipucu, yedek), ILK_EN_GEC)


def rakam_ani(sh: dict, yedek: float) -> float:
    """Anlatımda ilk rakamlı kelimenin söylendiği an (sayı o an iner); sahnenin üçte birinden geç olamaz."""
    for k in sh.get("kelimeler") or []:
        if re.search(r"\d", k["w"]):
            return max(0.0, min(k["s"] - 0.08, sh["sure"] * 0.33))
    return yedek


def _itis(sure: float) -> str:
    """Durağan grafik sahnesinde tek, yavaş kamera itişi (film.md: sakin bölümde 1.0 → 1.04-1.08); başlık kaymaz,
    bütün kare yaklaşır. 3 sn'den uzun 'hiçbir şey değişmiyor' (dead_stretch) olmasın."""
    return f"tl.fromTo(S('.icerik'), {{scale:1}}, {{scale:1.04, duration:{max(0.5, sure - 0.45):.3f}, ease:'none'}}, 0.45);"


def _sahne_html(sid: str, sure: float, govde: str, css: str, js: str, kok_stil: str = "") -> str:
    return f"""<template>
  <style>{_ortak_css()}{css}</style>
  <div id="root" data-composition-id="{sid}" data-width="{GENISLIK}" data-height="{YUKSEKLIK}" style="{kok_stil}">
{govde}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const S = (q) => document.querySelector('[data-composition-id="{sid}"] ' + q);
    const SA = (q) => document.querySelectorAll('[data-composition-id="{sid}"] ' + q);
{js}
    tl.set({{}}, {{}}, {sure:.3f});
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def _giris_js(gecis: str, sid: str) -> tuple[str, str]:
    """Sahnenin giriş geçişi: (gövdeye eklenecek HTML, JS). Her geçişin ekranda bir nedeni var (motion.md)."""
    if gecis == "savur":  # whip: içerik yatay bulanıkla gelir
        return "", ("tl.fromTo(S('.icerik'), {x: 160, filter:'blur(18px)'}, "
                    "{x: 0, filter:'blur(0px)', duration: .32, ease: 'expo.out'}, 0);")  # fmt: skip
    if gecis == "zoom":
        return "", ("tl.fromTo(S('.icerik'), {scale: 1.18, filter:'blur(14px)'}, "
                    "{scale: 1, filter:'blur(0px)', duration: .42, ease: 'power3.out'}, 0);")  # fmt: skip
    if gecis == "perde":  # vurgu renginde perde soldan açılır
        return (
            f'<div class="perde" id="{sid}-perde" style="background:{RENK["vurgu"]}"></div>',
            "tl.fromTo(S('.perde'), {xPercent: 0}, {xPercent: 101, duration: .38, ease: 'power3.inOut'}, 0);",
        )
    if gecis == "sel":  # mürekkep seli: karartıp açılır (dip cut)
        return (
            f'<div class="perde" id="{sid}-perde" style="background:{RENK["murekkep"]}"></div>',
            "tl.fromTo(S('.perde'), {opacity: 1}, {opacity: 0, duration: .28, ease: 'power2.out'}, 0);",
        )
    return "", ""


def _kelime_spanlari(metin: str, vurgu: list[str] | None, onek: str) -> str:
    vurgu_s = {_sade(v) for v in (vurgu or [])}
    parcalar = []
    for i, k in enumerate(_kelime_ayir(metin)):
        sinif = "w vurgu" if _sade(k) in vurgu_s else "w"
        parcalar.append(f'<span class="{sinif}" id="{onek}-w{i}">{_e(k)}</span>')
    return " ".join(parcalar)


def _kelime_girisi(sec: str, bas: float, aralik: float = 0.075) -> str:
    """Kelime kelime bulanıktan netleşme (motion.md: per word blur 6px→0, 0.13 s, ~0.067 s arayla)."""
    return (f"tl.fromTo(SA('{sec} .w'), {{opacity:0, filter:'blur(8px)'}}, "
            f"{{opacity:1, filter:'blur(0px)', duration:.16, ease:'power2.out', stagger:{aralik}}}, {bas:.3f});")  # fmt: skip


def _kamera(sid: str, sure: float, tohum: int) -> str:
    """Fotoğrafta tek yavaş kamera hareketi; yön tohuma göre değişir (her sahne aynı hareket etmesin)."""
    yonler = [(1.0, 1.09, -30, 30, 0, 0), (1.10, 1.0, 40, -20, 0, 0), (1.04, 1.12, 0, 0, 20, -20),
              (1.12, 1.03, -40, 10, -10, 10)]  # fmt: skip
    s0, s1, x0, x1, y0, y1 = yonler[tohum % len(yonler)]
    return (f"tl.fromTo(S('.kat'), {{scale:{s0}, x:{x0}, y:{y0}}}, "
            f"{{scale:{s1}, x:{x1}, y:{y1}, duration:{sure:.3f}, ease:'none'}}, 0);")  # fmt: skip


# ---------------------------------------------------------------------------------------------- sahne türleri
def sahne_foto(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    baslik = sh.get("baslik") or ""
    etiket = sh.get("etiket") or ""
    yer = "ust" if (tohum % 2 or sh.get("etiket")) else "alt"
    govde = f"""
    <div class="icerik tam">
      <div class="kat"><img src="{_e(sh["gorsel"])}" alt=""></div>
      <div class="karart tam {yer}"></div>
      {'<div class="tam" style="background:rgba(0,0,0,.38)"></div>' if sh.get("koyu") else ""}
      {
        f'<h1 class="gb baslik {yer}" id="{sid}-baslik">{_kelime_spanlari(baslik, sh.get("vurgu"), sid)}</h1>'
        if baslik
        else ""
    }
      {
        f'<div class="etiket" id="{sid}-etiket"><span class="cizgi"></span><span class="et">{_e(etiket)}</span></div>'
        if etiket
        else ""
    }
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if sh.get("kredi") else ""}
    </div>{perde}"""
    css = """
    .karart.alt { background: linear-gradient(180deg, rgba(0,0,0,0) 30%, rgba(0,0,0,.78) 100%); }
    .karart.ust { background: linear-gradient(0deg, rgba(0,0,0,0) 35%, rgba(0,0,0,.78) 100%); }
    .baslik { position:absolute; left:110px; right:110px; font-size:124px; color:#fff; line-height:1.02; }
    .baslik .w { background:rgba(15,15,16,.84); padding:4px 14px 0; margin-right:-6px;
                 box-decoration-break:clone; -webkit-box-decoration-break:clone; }
    .baslik .w.vurgu { background:#FFD60A; color:#111; }
    .baslik.alt { bottom:120px; } .baslik.ust { top:110px; }
    .etiket { position:absolute; left:110px; bottom:120px; display:flex; align-items:center; gap:22px; }
    .etiket .cizgi { display:block; width:10px; height:64px; background:#FFD60A; transform-origin: 50% 100%; }
    .etiket .et { font-size:46px; font-weight:700; color:#fff; background:rgba(15,15,16,.86); padding:10px 22px; }
    """
    js = [giris, _kamera(sid, sure, tohum)]
    if baslik:
        js.append(_kelime_girisi(f"#{sid}-baslik", ipucu_zamani(sh, sh.get("ipucu"), min(0.35, sure * 0.1))))
    if etiket:
        t = ipucu_zamani(sh, sh.get("etiket_ipucu"), sure * 0.25)
        js.append(f"tl.fromTo(S('.etiket .cizgi'), {{scaleY:0}}, {{scaleY:1, duration:.3, ease:'expo.out'}}, {t:.3f});")
        js.append(f"tl.fromTo(S('.etiket .et'), {{clipPath:'inset(0 100% 0 0)'}}, "
                  f"{{clipPath:'inset(0 0% 0 0)', duration:.45, ease:'expo.out'}}, {t + 0.12:.3f});")  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_manset(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    mansetler = sh.get("mansetler") or []
    kartlar = []
    acilar = [-2.2, 1.8, -1.2]
    konumlar = [(120, 140), (760, 410), (200, 680)] if not sh.get("gorsel") else [(150, 150), (900, 420), (230, 690)]
    for i, m in enumerate(mansetler[:3]):
        x, y = konumlar[i]
        kartlar.append(
            f'<div class="kart" id="{sid}-k{i}" style="left:{x}px; top:{y - 60}px; --a:{acilar[i]}deg">'
            f'<div class="kaynak">{_e(m["kaynak"])}</div><div class="kb">{_e(m["baslik"])}</div></div>'
        )
    arka = (f'<div class="kat"><img src="{_e(sh["gorsel"])}" alt=""></div><div class="karart tam"></div>'
            if sh.get("gorsel") else '<div class="tam doku"></div>')  # fmt: skip
    govde = f"""
    <div class="icerik tam">
      {arka}
      {"".join(kartlar)}
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if sh.get("kredi") else ""}
    </div>{perde}"""
    css = f"""
    .karart {{ background: rgba(10,10,12,.62); }}
    .doku {{ background:{RENK["kirmizi"]}; }}
    .kart {{ position:absolute; width:{1000 if not sh.get("gorsel") else 800}px; background:{RENK["kagit"]}; color:#141414; padding:26px 34px 30px;
             box-shadow: 0 18px 40px rgba(0,0,0,.45); rotate: var(--a); }}
    .kart .kaynak {{ font-size:30px; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
                     color:{RENK["kirmizi"]}; margin-bottom:10px; }}
    .kart .kb {{ font-size:48px; font-weight:700; line-height:1.12; }}
    """
    zamanlar = _yayilim(sure, len(kartlar), 0.02, 0.4)
    js = [giris]
    if sh.get("gorsel"):
        js.append(_kamera(sid, sure, tohum))
    for i, m in enumerate(mansetler[:3]):
        t = ilk_an(sh, m.get("ipucu")) if i == 0 else min(ipucu_zamani(sh, m.get("ipucu"), zamanlar[i]), sure * 0.45)
        yon = -1 if i % 2 else 1
        js.append(f"tl.fromTo('#{sid}-k{i}', {{y:{yon * -420}, opacity:1, scale:1.06}}, "
                  f"{{y:0, scale:1, duration:.42, ease:'expo.out'}}, {t:.3f});")  # fmt: skip
        js.append(f"tl.set('#{sid}-k{i}', {{opacity:0}}, 0);")
        js.append(f"tl.set('#{sid}-k{i}', {{opacity:1}}, {t:.3f});")
    if not sh.get("gorsel"):
        js.append(_itis(sure))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def _sayi_bicim(deger: float) -> tuple[int, str]:
    """Ondalık basamak sayısı ve binlik ayırıcı biçimi."""
    if float(deger).is_integer():
        return 0, ","
    return min(2, len(str(deger).split(".")[1])), ","


def kisalt(deger: float, son: str) -> tuple[float, str]:
    """Ekranda 10 milyon ve üstü kısaltılır (1,800,000,000 → 1.8B); son ek zaten verilmişse dokunulmaz."""
    if son:
        return deger, son
    for esik, ek in ((1e12, "T"), (1e9, "B"), (1e7, "M")):
        if abs(deger) >= esik:
            return round(deger / (esik if ek != "M" else 1e6), 1), ek
    return deger, son


def sahne_sayi(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis if gecis != "perde" else "sel", sid)
    zemin = sh.get("renk") or ("vurgu" if tohum % 2 == 0 else "kirmizi")
    zemin_hex = RENK.get(zemin, RENK["vurgu"])
    yazi = "#111" if zemin == "vurgu" else "#fff"
    deger = float(sh["deger"])
    on, son = sh.get("on") or "", sh.get("son") or ""
    deger, son = kisalt(deger, son)
    ondalik, _ = _sayi_bicim(deger)
    uzunluk = len(f"{deger:,.{ondalik}f}") + 0.55 * (len(on) + len(son))
    boy = int(min(430, 1600 / (0.46 * max(uzunluk, 1))))
    govde = f"""
    <div class="icerik tam" style="background:{zemin_hex}; color:{yazi}">
      <div class="sayi gb" id="{sid}-sayi"><span class="on">{_e(on)}</span><span class="deger">0</span><span
        class="son">{_e(son)}</span></div>
      <div class="etk" id="{sid}-etk">{_kelime_spanlari(sh.get("etiket", ""), sh.get("vurgu"), sid)}</div>
    </div>{perde}"""
    css = f"""
    .sayi {{ position:absolute; left:120px; right:120px; top:150px; font-size:{boy}px; white-space:nowrap; }}
    .sayi .on, .sayi .son {{ font-size:.55em; }}
    .etk {{ position:absolute; left:126px; right:200px; top:640px; font-size:62px; font-weight:700; line-height:1.15; }}
    .etk .vurgu {{ background:#111; color:#FFD60A; padding:0 10px; }}
    """
    t0 = rakam_ani(sh, ilk_an(sh, sh.get("ipucu")))
    sayac = max(1.2, min(1.6, sure * 0.3))
    js = [giris,
          "const d = S('.deger'); const p = {v:0};",
          f"const yaz = () => {{ d.textContent = p.v.toLocaleString('en-US', {{minimumFractionDigits:{ondalik}, "
          f"maximumFractionDigits:{ondalik}}}); }};",
          f"tl.fromTo(p, {{v:0}}, {{v:{deger}, duration:{sayac:.2f}, ease:'power3.out', onUpdate: yaz}}, {t0:.3f});",
          "tl.fromTo(S('.sayi'), {y:60, opacity:0}, {y:0, opacity:1, duration:.35, ease:'expo.out'}, 0.06);",
          _kelime_girisi(f"#{sid}-etk", min(t0 + sayac * 0.7, 0.35), 0.06)]  # fmt: skip
    if True:
        js.append(_itis(sure))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_alinti(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    foto = sh.get("gorsel")
    govde = f"""
    <div class="icerik tam">
      {f'<div class="foto"><div class="kat"><img src="{_e(foto)}" alt=""></div></div>' if foto else ""}
      <div class="tirnak gb">“</div>
      <blockquote class="metin {"dar" if foto else ""}" id="{sid}-metin">{_kelime_spanlari(sh["metin"], sh.get("vurgu"), sid)}</blockquote>
      <div class="kim" id="{sid}-kim">— {_e(sh.get("kim", ""))}</div>
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if sh.get("kredi") else ""}
    </div>{perde}"""
    css = f"""
    .icerik {{ background:{RENK["murekkep"]}; }}
    .foto {{ position:absolute; right:0; top:0; bottom:0; width:760px; overflow:hidden; }}
    .tirnak {{ position:absolute; left:96px; top:40px; font-size:340px; color:{RENK["vurgu"]}; line-height:1; }}
    .metin {{ position:absolute; left:120px; right:140px; top:280px; font-size:80px; font-weight:700;
              line-height:1.18; margin:0; }}
    .metin.dar {{ right:860px; font-size:66px; }}
    .metin .w {{ color:#fff; }}
    .kim {{ position:absolute; left:124px; bottom:110px; font-size:36px; color:{RENK["vurgu"]}; font-weight:700;
            letter-spacing:.04em; }}
    """
    t0 = ilk_an(sh, sh.get("ipucu"), 0.25)
    n = max(1, len(_kelime_ayir(sh["metin"])))
    aralik = max(0.04, min(0.16, (sure * 0.6) / n))
    js = [giris]
    if foto:
        js.append(_kamera(sid, sure, tohum))
    js += ["tl.fromTo(S('.tirnak'), {scale:.6, opacity:0}, {scale:1, opacity:1, duration:.4, ease:'back.out(1.6)'}, .05);",
           f"tl.fromTo(SA('#{sid}-metin .w'), {{opacity:.18}}, {{opacity:1, duration:.12, stagger:{aralik:.3f}}}, {t0:.3f});",
           f"tl.fromTo(S('.kim'), {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:.4, ease:'expo.out'}}, "
           f"{min(sure - 0.6, t0 + n * aralik):.3f});"]  # fmt: skip
    if not foto:
        js.append(_itis(sure))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def kronolojik(olaylar: list[dict]) -> list[dict]:
    """Her tarihte 4 haneli yıl varsa olaylar yıla göre sıralanır (yazar 2023'ü 2015'ten önce koymuştu, 11-20)."""
    yillar = [re.search(r"(1[5-9]|20)[0-9]{2}", str(o.get("tarih", ""))) for o in olaylar]
    if olaylar and all(yillar):
        return [o for _, o in sorted(zip([int(y.group(0)) for y in yillar], olaylar, strict=True), key=lambda t: t[0])]
    return olaylar


def sahne_zaman(sh: dict, gecis: str, tohum: int) -> str:
    """Zaman çizgisi: 4 olaya kadar tek kadrajda (kaydırma yok, eşit aralık); fazlası kamera kaydırmalı."""
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    olaylar = kronolojik(sh.get("olaylar") or [])
    n = max(1, len(olaylar))
    kenar = 230
    adim = (GENISLIK - 2 * kenar - 420) / max(1, n - 1) if n <= 4 else 560
    dugumler = []
    for i, o in enumerate(olaylar):
        x = kenar + i * adim
        ust = i % 2 == 0
        dugumler.append(
            f'<div class="dugum" id="{sid}-d{i}" style="left:{x:.0f}px">'
            f'<div class="nokta"></div>'
            f'<div class="kutu {"ust" if ust else "alt"}"><div class="tarih gb">{_e(o["tarih"])}</div>'
            f'<div class="olay">{_e(o["olay"])}</div></div></div>'
        )
    genislik = max(GENISLIK, kenar * 2 + adim * (n - 1) + 600)
    govde = f"""
    <div class="icerik tam">
      <div class="ray" style="width:{genislik:.0f}px">
        <div class="hat"></div>
        {"".join(dugumler)}
      </div>
    </div>{perde}"""
    css = f"""
    .icerik {{ background:{RENK["kagit"]}; color:#111; }}
    .ray {{ position:absolute; left:0; top:0; height:100%; }}
    .hat {{ position:absolute; left:{kenar - 120}px; right:0; top:540px; height:8px; background:#111;
            transform-origin:0 50%; }}
    .dugum {{ position:absolute; top:540px; }}
    .nokta {{ position:absolute; left:-22px; top:-18px; width:44px; height:44px; border-radius:50%;
              background:{RENK["kirmizi"]}; border:8px solid #111; }}
    .kutu {{ position:absolute; left:-30px; width:{min(600, adim + 80 if n > 1 else 900):.0f}px; }}
    .kutu.ust {{ bottom:70px; }} .kutu.alt {{ top:80px; }}
    .tarih {{ font-size:170px; color:#111; }}
    .olay {{ font-size:50px; font-weight:700; line-height:1.15; margin-top:6px; }}
    """
    zamanlar = _yayilim(sure, len(olaylar), 0.05, 0.45)
    js = [giris, f"tl.fromTo(S('.hat'), {{scaleX:0}}, {{scaleX:1, duration:{max(0.8, sure * 0.8):.2f}, "
                 f"ease:'power1.inOut'}}, 0);"]  # fmt: skip
    onceki_x = 0.0
    for i, o in enumerate(olaylar):
        t = ilk_an(sh, o.get("ipucu")) if i == 0 else ipucu_zamani(sh, o.get("ipucu"), zamanlar[i])
        if n > 4:  # kamera etkin düğümü ortalar
            hedef_x = -max(0.0, kenar + i * adim - GENISLIK / 2 + 150)
            if hedef_x != onceki_x:
                js.append(
                    f"tl.to(S('.ray'), {{x:{hedef_x:.0f}, duration:.7, ease:'power2.inOut'}}, {max(0, t - 0.35):.3f});"
                )
                onceki_x = hedef_x
        js.append(
            f"tl.fromTo('#{sid}-d{i} .nokta', {{scale:0}}, {{scale:1, duration:.35, ease:'back.out(2)'}}, {t:.3f});"
        )
        js.append(f"tl.fromTo('#{sid}-d{i} .kutu', {{opacity:0, y:{30 if i % 2 else -30}}}, "
                  f"{{opacity:1, y:0, duration:.4, ease:'expo.out'}}, {t + 0.08:.3f});")  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_bolum(sh: dict, gecis: str, tohum: int) -> str:
    """Bölüm kartı: görsel varsa fotoğraf + renk bandı, yoksa renk alanı; numara dolu mürekkeple, başlık kelime kelime."""
    sid, sure = sh["id"], sh["sure"]
    zemin = ["vurgu", "kirmizi", "mavi"][tohum % 3]
    yazi = "#111" if zemin == "vurgu" else "#fff"
    foto = sh.get("gorsel")
    arka = (f'<div class="kat"><img src="{_e(foto)}" alt=""></div><div class="tam" style="background:rgba(10,10,12,.55)"></div>'
            if foto else "")  # fmt: skip
    govde = f"""
    <div class="icerik tam" style="background:{RENK["murekkep"] if foto else RENK[zemin]}">
      {arka}
      <div class="bant" style="background:{RENK[zemin]}; color:{yazi}">
        <div class="no gb" id="{sid}-no">{_e(sh.get("no", ""))}</div>
        <h1 class="gb bb" id="{sid}-bb">{_kelime_spanlari(sh["baslik"], None, sid)}</h1>
      </div>
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if foto and sh.get("kredi") else ""}
    </div>"""
    css = f"""
    .bant {{ position:absolute; left:0; right:0; {"top:330px; height:420px;" if foto else "top:0; bottom:0;"}
             display:flex; align-items:center; gap:70px; padding:0 120px; }}
    .no {{ font-size:{"300px" if foto else "420px"}; line-height:.8; }}
    .bb {{ font-size:{"150px" if foto else "180px"}; margin:0; flex:1; }}
    """
    js = ["tl.fromTo(S('.bant'), {clipPath:'inset(0 100% 0 0)'}, "
          "{clipPath:'inset(0 0% 0 0)', duration:.5, ease:'expo.inOut'}, 0);",
          "tl.fromTo(S('.no'), {y:120, opacity:0}, {y:0, opacity:1, duration:.55, ease:'expo.out'}, .2);",
          _kelime_girisi(f"#{sid}-bb", 0.38, 0.09)]  # fmt: skip
    if foto:
        js.append(_kamera(sid, sure, tohum))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_ikili(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    sol, sag = sh["sol"], sh["sag"]
    govde = f"""
    <div class="icerik tam">
      <div class="yari sol"><div class="ic"><div class="etk">{_e(sol["etiket"])}</div>
        <div class="dg gb">{_e(sol["deger"])}</div></div></div>
      <div class="yari sag"><div class="ic"><div class="etk">{_e(sag["etiket"])}</div>
        <div class="dg gb">{_e(sag["deger"])}</div></div></div>
      {f'<div class="ust gb">{_e(sh["baslik"])}</div>' if sh.get("baslik") else ""}
    </div>{perde}"""
    css = f"""
    .yari {{ position:absolute; top:0; bottom:0; width:50%; display:flex; align-items:center; }}
    .yari.sol {{ left:0; background:{RENK["murekkep"]}; }}
    .yari.sag {{ right:0; background:{RENK["vurgu"]}; color:#111; }}
    .ic {{ padding:0 100px; }}
    .etk {{ font-size:48px; font-weight:700; margin-bottom:18px; }}
    .dg {{ font-size:220px; }}
    .ust {{ position:absolute; left:0; right:0; top:0; padding:34px 0 22px; text-align:center; font-size:84px;
            color:#fff; background:{RENK["murekkep"]}; z-index:5; }}
    """
    t1 = ilk_an(sh, sol.get("ipucu"))
    t2 = ipucu_zamani(sh, sag.get("ipucu"), sure * 0.45)
    js = [
        giris,
        f"tl.fromTo(S('.yari.sol'), {{xPercent:-100}}, {{xPercent:0, duration:.5, ease:'expo.out'}}, {max(0, t1 - 0.1):.3f});",
        f"tl.fromTo(S('.yari.sol .ic'), {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.4, ease:'expo.out'}}, {t1:.3f});",
        f"tl.fromTo(S('.yari.sag'), {{xPercent:100}}, {{xPercent:0, duration:.5, ease:'expo.out'}}, {max(0, t2 - 0.1):.3f});",
        f"tl.fromTo(S('.yari.sag .ic'), {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.4, ease:'expo.out'}}, {t2:.3f});",
    ]
    if sh.get("baslik"):
        js.append("tl.fromTo(S('.ust'), {opacity:0}, {opacity:1, duration:.3}, .05);")
    if True:
        js.append(_itis(sure))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_ifade(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    foto = sh.get("gorsel")
    arka = (f'<div class="kat"><img src="{_e(foto)}" alt=""></div><div class="karart tam"></div>' if foto
            else f'<div class="tam" style="background:{RENK["murekkep"]}"></div>')  # fmt: skip
    metin = sh["metin"]
    boy = 170 if len(metin) < 40 else (140 if len(metin) < 70 else 112)
    govde = f"""
    <div class="icerik tam">
      {arka}
      <h1 class="gb cumle" id="{sid}-c" style="font-size:{boy}px">{_kelime_spanlari(metin, sh.get("vurgu"), sid)}</h1>
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if sh.get("kredi") else ""}
    </div>{perde}"""
    css = """
    .karart { background: rgba(8,8,10,.66); }
    .cumle { position:absolute; left:120px; right:120px; top:50%; transform:translateY(-50%); margin:0; color:#fff; }
    """
    t0 = ilk_an(sh, sh.get("ipucu"), 0.2)
    n = max(1, len(_kelime_ayir(metin)))
    aralik = max(0.06, min(0.22, (sure * 0.55) / n))
    js = [giris]
    if foto:
        js.append(_kamera(sid, sure, tohum))
    js.append(_kelime_girisi(f"#{sid}-c", t0, aralik))
    if not foto:
        js.append(_itis(sure))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_kapanis(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    govde = f"""
    <div class="icerik tam">
      <h1 class="gb son" id="{sid}-son">{_kelime_spanlari(sh["metin"], sh.get("vurgu"), sid)}</h1>
      <div class="kanal" id="{sid}-kanal"><span class="blok"></span><span class="ad gb">{_e(sh.get("kanal", ""))}</span></div>
    </div>"""
    css = f"""
    .icerik {{ background:{RENK["murekkep"]}; }}
    .son {{ position:absolute; left:120px; right:120px; top:230px; font-size:150px; margin:0; color:#fff; }}
    .kanal {{ position:absolute; left:120px; bottom:130px; display:flex; align-items:center; gap:26px; }}
    .kanal .blok {{ width:70px; height:70px; background:{RENK["vurgu"]}; display:block; }}
    .kanal .ad {{ font-size:96px; color:#fff; }}
    """
    js = [_kelime_girisi(f"#{sid}-son", 0.25, 0.1),
          f"tl.fromTo(S('.kanal .blok'), {{scale:0, rotation:-90}}, {{scale:1, rotation:0, duration:.5, "
          f"ease:'back.out(1.7)'}}, {max(0.8, sure - 3.2):.3f});",
          f"tl.fromTo(S('.kanal .ad'), {{clipPath:'inset(0 100% 0 0)'}}, {{clipPath:'inset(0 0% 0 0)', duration:.5, "
          f"ease:'expo.out'}}, {max(0.95, sure - 3.0):.3f});"]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def sahne_harita(sh: dict, gecis: str, tohum: int) -> str:
    """Pişirilmiş uydu uçuşu (harita.py) + hedefte işaret ve yer etiketi; uçuş sürenin %60'ında biter."""
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    govde = f"""
    <div class="icerik tam">
      <video id="{sid}-v" class="clip kapla" src="{_e(sh["video"])}" data-start="0" data-duration="{sure:.3f}"
             muted playsinline></video>
      <div class="pin" id="{sid}-pin"><div class="halka"></div><div class="nokta"></div></div>
      <div class="yer gb" id="{sid}-yer">{_e(sh.get("yer", ""))}</div>
      <div class="kredi" data-layout-ignore>{_e(sh.get("kredi", ""))}</div>
    </div>{perde}"""
    css = f"""
    video.kapla {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
    .pin {{ position:absolute; left:{GENISLIK // 2 - 30}px; top:{YUKSEKLIK // 2 - 30}px; width:60px; height:60px; }}
    .pin .nokta {{ position:absolute; left:18px; top:18px; width:24px; height:24px; border-radius:50%;
                   background:{RENK["kirmizi"]}; border:5px solid #fff; }}
    .pin .halka {{ position:absolute; inset:0; border-radius:50%; border:5px solid {RENK["kirmizi"]}; }}
    .yer {{ position:absolute; left:{GENISLIK // 2 + 50}px; top:{YUKSEKLIK // 2 - 70}px; font-size:110px; color:#111;
            background:{RENK["vurgu"]}; padding:4px 22px 0; }}
    """
    t = max(0.4, sure * 0.6)
    js = [giris,
          f"tl.fromTo('#{sid}-pin .nokta', {{scale:0}}, {{scale:1, duration:.35, ease:'back.out(2.2)'}}, {t:.3f});",
          f"tl.fromTo('#{sid}-pin .halka', {{scale:.3, opacity:1}}, {{scale:1.8, opacity:0, duration:.9, ease:'power2.out'}}, {t:.3f});",
          f"tl.fromTo('#{sid}-yer', {{clipPath:'inset(0 100% 0 0)'}}, {{clipPath:'inset(0 0% 0 0)', duration:.45, ease:'expo.out'}}, {t + 0.15:.3f});"]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


SAHNELER = {"foto": sahne_foto, "manset": sahne_manset, "sayi": sahne_sayi, "alinti": sahne_alinti,
            "zaman": sahne_zaman, "bolum": sahne_bolum, "ikili": sahne_ikili, "ifade": sahne_ifade,
            "kapanis": sahne_kapanis, "harita": sahne_harita}  # fmt: skip


def gecis_sec(i: int, tur: str, onceki: str | None) -> str:
    if i == 0:
        return "kesme"  # kare 0 kapak karesi: hiçbir şey perde arkasında olmasın
    if tur in ("bolum", "kapanis"):
        return "kesme"  # kendi girişleri var
    g = GECISLER[i % len(GECISLER)]
    return GECISLER[(i + 1) % len(GECISLER)] if g == onceki else g


# ---------------------------------------------------------------------------------------------- kök + ses
def kok_html(plan: dict, sfx: list[dict]) -> str:
    sahneler = plan["sahneler"]
    toplam = plan["sure"]
    hostlar = []
    for sh in sahneler:
        hostlar.append(
            f'      <div id="{sh["id"]}" data-composition-id="{sh["id"]}" data-composition-src="compositions/{sh["id"]}.html" '
            f'data-start="{sh["bas"]:.3f}" data-duration="{sh["sure"]:.3f}" data-track-index="1" '
            f'data-track-kind="graphics" data-width="{GENISLIK}" data-height="{YUKSEKLIK}"></div>'
        )
    sesler = [f'      <audio id="anlatim" class="clip" src="assets/ses/anlatim.wav" data-start="0" '
              f'data-duration="{toplam:.3f}" data-track-index="10" data-volume="1"></audio>']  # fmt: skip
    if plan.get("muzik"):
        m = plan["muzik"]
        sesler.append(f'      <audio id="muzik" class="clip" src="{_e(m["dosya"])}" data-start="0" '
                      f'data-duration="{toplam:.3f}" data-track-index="11" data-volume="{m.get("ses", 0.13)}" '
                      f'data-fade-in="0.6" data-fade-out="2.5"></audio>')  # fmt: skip
    for i, s in enumerate(sfx):
        sesler.append(
            f'      <audio id="sfx{i}" class="clip" src="{_e(s["dosya"])}" data-start="{s["t"]:.3f}" '
            f'data-duration="{s["sure"]:.3f}" data-track-index="{12 + i % 4}" data-volume="{s["ses"]}"></audio>'
        )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={GENISLIK}, height={YUKSEKLIK}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{GENISLIK}px; height:{YUKSEKLIK}px; overflow:hidden; background:{RENK["murekkep"]}; }}
      #root {{ position:relative; width:100%; height:100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{toplam:.3f}"
         data-width="{GENISLIK}" data-height="{YUKSEKLIK}" data-fps="{FPS}">
{chr(10).join(hostlar)}
{chr(10).join(sesler)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""


SFX_DIZIN = Path(__file__).resolve().parent / "varlik" / "sfx"


def sfx_plani(plan: dict) -> list[dict]:
    """Geçişlere whoosh (iki-üç take dönüşümlü), sayı inişine pop, bölüm kartına impact. Her ses ekranda bir nedene bağlı."""
    out = []
    whoosh = ["whoosh.mp3", "whoosh-short.mp3", "whoosh-cinematic.mp3"]
    sureler = {"whoosh.mp3": 0.9, "whoosh-short.mp3": 0.6, "whoosh-cinematic.mp3": 1.6, "pop.mp3": 0.72,
               "impact-bass-1.mp3": 2.12, "click-soft.mp3": 0.37}  # fmt: skip
    for i, sh in enumerate(plan["sahneler"]):
        g = sh.get("gecis")
        if sh["tur"] == "bolum":
            out.append({"dosya": "assets/sfx/impact-bass-1.mp3", "t": sh["bas"] + 0.02, "sure": 2.12, "ses": 0.32})
        elif g in ("savur", "zoom", "perde"):
            f = whoosh[i % len(whoosh)]
            out.append({"dosya": f"assets/sfx/{f}", "t": max(0, sh["bas"] - 0.12), "sure": sureler[f], "ses": 0.22})
        if sh["tur"] == "sayi":
            t0 = ipucu_zamani(sh, sh.get("ipucu"), min(0.3, sh["sure"] * 0.08))
            out.append({"dosya": "assets/sfx/pop.mp3", "t": sh["bas"] + t0 + 1.3, "sure": 0.72, "ses": 0.3})
        if sh["tur"] == "manset":
            for m in (sh.get("mansetler") or [])[:5]:
                t = ipucu_zamani(sh, m.get("ipucu"), 0.3)
                out.append({"dosya": "assets/sfx/click-soft.mp3", "t": sh["bas"] + t, "sure": 0.37, "ses": 0.25})
    # çakışan aynı-anlık sesleri sil (0.15 sn içinde ikinci ses)
    out.sort(key=lambda s: s["t"])
    temiz = []
    for s in out:
        if temiz and s["t"] - temiz[-1]["t"] < 0.15:
            continue
        temiz.append(s)
    return [s for s in temiz if s["t"] + 0.05 < plan["sure"]]


def proje_yaz(plan: dict, dizin: Path, varliklar: dict[str, Path]) -> Path:
    """HyperFrames projesini yazar. `varliklar`: proje içi yol → kaynak dosya (görseller, ses, müzik)."""
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "compositions").mkdir(exist_ok=True)
    for hedef, kaynak in varliklar.items():
        h = dizin / hedef
        h.parent.mkdir(parents=True, exist_ok=True)
        if not h.exists() or h.stat().st_mtime < Path(kaynak).stat().st_mtime:
            shutil.copy2(kaynak, h)
    onceki = None
    for i, sh in enumerate(plan["sahneler"]):
        g = gecis_sec(i, sh["tur"], onceki)
        sh["gecis"] = g
        onceki = g
        tohum = int(sh.get("tohum", i * 7 + 3))
        (dizin / "compositions" / f"{sh['id']}.html").write_text(SAHNELER[sh["tur"]](sh, g, tohum), encoding="utf-8")
    sfx = sfx_plani(plan)
    for s in sfx:
        ad = Path(s["dosya"]).name
        h = dizin / "assets" / "sfx" / ad
        if not h.exists():
            h.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SFX_DIZIN / ad, h)
    (dizin / "index.html").write_text(kok_html(plan, sfx), encoding="utf-8")
    (dizin / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    (dizin / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "assets": "assets"}}),
                                            encoding="utf-8")  # fmt: skip
    return dizin


# ---------------------------------------------------------------------------------------------- CLI sarmalayıcı
MOTOR_DIZIN = Path(__file__).resolve().parents[2] / "araclar" / "hyperframes"


def _hf(args: list[str], dizin: Path, zaman_asimi: int = 3600) -> subprocess.CompletedProcess:
    import os

    bin_ = MOTOR_DIZIN / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    if not bin_.exists():
        raise RuntimeError(f"HyperFrames kurulu değil: {MOTOR_DIZIN} içinde `npm ci` (sürüm {HF_SURUM})")
    ortam = {**os.environ, **HF_ORTAM}
    return subprocess.run(["node", str(bin_), *args], cwd=dizin, env=ortam, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=zaman_asimi)  # fmt: skip


def denetle(dizin: Path) -> dict:
    r = _hf(["check", "--json"], dizin, 900)
    try:
        return json.loads(r.stdout[r.stdout.find("{") :])
    except ValueError:
        return {"ham": r.stdout[-4000:], "hata": r.stderr[-2000:], "kod": r.returncode}


def _son_snapshot(dizin: Path) -> Path | None:
    kok = dizin / ".hyperframes" / "artifacts" / "snapshots"
    dizinler = [p for p in kok.glob("*") if p.is_dir()] if kok.exists() else []
    return max(dizinler, key=lambda p: p.stat().st_mtime) if dizinler else None


def kareler(dizin: Path, anlar: list[float]) -> list[Path]:
    """Verilen anlarda PNG kareler (HyperFrames snapshot); en yeni snapshot klasöründeki frame-*.png."""
    r = _hf(["snapshot", "--at", ",".join(f"{a:.2f}" for a in anlar)], dizin, 900)
    son = _son_snapshot(dizin)
    if r.returncode or son is None:
        raise RuntimeError(r.stderr[-2000:] or r.stdout[-2000:])
    return sorted(son.glob("frame-*.png"))


def inceleme_sayfalari(dizin: Path) -> list[Path]:
    """`snapshot --review`: sahne başı/ortası, kesim şeritleri ve telefon genişliği sayfaları (review.md)."""
    r = _hf(["snapshot", "--review"], dizin, 1800)
    son = _son_snapshot(dizin)
    if r.returncode or son is None:
        raise RuntimeError(r.stderr[-2000:] or r.stdout[-2000:])
    return sorted(son.glob("*.jpg")) + sorted(son.glob("*sheet*.png"))


def render(dizin: Path, cikti: Path, kalite: str = "standard", isci: int = 4) -> Path:
    r = _hf(["render", "-o", str(cikti), "-q", kalite, "-w", str(isci), "-f", str(FPS)], dizin, 4 * 3600)
    if r.returncode or not cikti.exists():
        raise RuntimeError((r.stderr or r.stdout)[-3000:])
    return cikti


def sure_toplam(plan: dict) -> float:
    return math.fsum(sh["sure"] for sh in plan["sahneler"])
