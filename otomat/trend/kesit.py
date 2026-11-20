"""Uzun videodan Shorts: ardışık sahneler 1080×1920 için YENİDEN kurulur (yatay video kırpılmaz).

HyperFrames types/vertical.md: üst 168 px'te ve 1330 px altında okunacak hiçbir şey yok; kare 0 kapak ve kancadır
(siyah ya da logo değil); çoğu izleyici sessiz izler → kelime kelime altyazı; çekimler 1-2 sn, 2-4 sn'de yeni vuruş.
Bizim Shorts ölçümümüz (Faz 16-19): izleyicinin ~%70'i ilk saniyelerde kaydırıyor; asıl düzeltme ilk kare.
Kanca satırı (senaryodaki `kanca`) 0. kareden itibaren ekranda, anlatım onunla birlikte başlar.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from otomat.trend import kurgu
from otomat.trend.kurgu import (
    RENK,
    _e,
    _giris_js,
    _kelime_ayir,
    _kelime_girisi,
    _kelime_spanlari,
    _ortak_css,
    _yayilim,
    ipucu_zamani,
)

W, H = 1080, 1920
UST, ALT = 200, 1300  # okunacak her şey bu bant içinde
ALTYAZI_Y = 1120  # altyazı bandının üstü
ICERIK_ALT = ALTYAZI_Y - 40  # sahne içeriği bunun altına inmez (altyazıyla çakışmasın)


def _sahne_html(sid: str, sure: float, govde: str, css: str, js: str) -> str:
    return f"""<template>
  <style>{_ortak_css()}{css}</style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
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


def _kamera(sure: float, tohum: int) -> str:
    yonler = [(1.0, 1.1, 0, 0), (1.12, 1.02, -30, 30), (1.04, 1.13, 25, -25)]
    s0, s1, x0, x1 = yonler[tohum % len(yonler)]
    return (f"tl.fromTo(S('.kat'), {{scale:{s0}, x:{x0}}}, {{scale:{s1}, x:{x1}, duration:{sure:.3f}, "
            f"ease:'none'}}, 0);")  # fmt: skip


def d_foto(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    baslik = sh.get("baslik") or ""
    govde = f"""
    <div class="icerik tam">
      <div class="kat"><img src="{_e(sh["gorsel"])}" alt=""></div>
      <div class="karart tam"></div>
      {f'<h1 class="gb baslik" id="{sid}-baslik">{_kelime_spanlari(baslik, sh.get("vurgu"), sid)}</h1>' if baslik else ""}
      {f'<div class="kredi" data-layout-ignore>{_e(sh["kredi"])}</div>' if sh.get("kredi") else ""}
    </div>{perde}"""
    css = f"""
    .karart {{ background: linear-gradient(180deg, rgba(0,0,0,.55) 0%, rgba(0,0,0,0) 32%, rgba(0,0,0,0) 55%,
               rgba(0,0,0,.6) 100%); }}
    .baslik {{ position:absolute; left:70px; right:70px; top:{UST + 40}px; font-size:118px; color:#fff;
               text-shadow:0 4px 26px rgba(0,0,0,.6); }}
    .kredi {{ bottom:auto; top:{ALT + 20}px; right:30px; font-size:20px; }}
    """
    js = [giris, _kamera(sure, tohum)]
    if baslik:
        js.append(_kelime_girisi(f"#{sid}-baslik", ipucu_zamani(sh, sh.get("ipucu"), 0.2)))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_manset(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    ms = (sh.get("mansetler") or [])[:3]
    kartlar = []
    for i, m in enumerate(ms):
        y = UST + 120 + i * 300
        a = [-2.5, 2.0, -1.5][i]
        kartlar.append(f'<div class="kart" id="{sid}-k{i}" style="top:{y}px; --a:{a}deg"><div class="kaynak">'
                       f'{_e(m["kaynak"])}</div><div class="kb">{_e(m["baslik"])}</div></div>')  # fmt: skip
    arka = (f'<div class="kat"><img src="{_e(sh["gorsel"])}" alt=""></div><div class="tam" '
            f'style="background:rgba(10,10,12,.6)"></div>' if sh.get("gorsel") else "")  # fmt: skip
    govde = f'<div class="icerik tam" style="background:{RENK["murekkep"]}">{arka}{"".join(kartlar)}</div>{perde}'
    css = f"""
    .kart {{ position:absolute; left:60px; right:60px; background:{RENK["kagit"]}; color:#141414; padding:24px 30px 28px;
             box-shadow:0 18px 40px rgba(0,0,0,.45); rotate:var(--a); }}
    .kart .kaynak {{ font-size:30px; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
                     color:{RENK["kirmizi"]}; margin-bottom:8px; }}
    .kart .kb {{ font-size:50px; font-weight:700; line-height:1.12; }}
    """
    zam = _yayilim(sure, len(ms), 0.04, 0.55)
    js = [giris] + ([_kamera(sure, tohum)] if sh.get("gorsel") else [])
    for i, m in enumerate(ms):
        t = ipucu_zamani(sh, m.get("ipucu"), zam[i])
        js += [
            f"tl.set('#{sid}-k{i}', {{opacity:0}}, 0);",
            f"tl.set('#{sid}-k{i}', {{opacity:1}}, {t:.3f});",
            f"tl.fromTo('#{sid}-k{i}', {{x:{-900 if i % 2 else 900}}}, {{x:0, duration:.38, ease:'expo.out'}}, {t:.3f});",
        ]
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_sayi(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis if gecis != "perde" else "sel", sid)
    zemin = sh.get("renk") or ("vurgu" if tohum % 2 == 0 else "kirmizi")
    yazi = "#111" if zemin == "vurgu" else "#fff"
    deger = float(sh["deger"])
    ondalik = 0 if deger.is_integer() else min(2, len(str(sh["deger"]).split(".")[1]))
    uzun = len(f"{deger:,.{ondalik}f}") + len(sh.get("on") or "") + len(sh.get("son") or "")
    boy = 300 if uzun <= 5 else (240 if uzun <= 8 else 180)
    govde = f"""
    <div class="icerik tam" style="background:{RENK.get(zemin, RENK["vurgu"])}; color:{yazi}">
      <div class="sayi gb"><span class="on">{_e(sh.get("on") or "")}</span><span class="deger">0</span><span
        class="son">{_e(sh.get("son") or "")}</span></div>
      <div class="etk" id="{sid}-etk">{_kelime_spanlari(sh.get("etiket", ""), sh.get("vurgu"), sid)}</div>
    </div>{perde}"""
    css = f"""
    .sayi {{ position:absolute; left:60px; right:60px; top:{UST + 150}px; font-size:{boy}px; white-space:nowrap; }}
    .sayi .on, .sayi .son {{ font-size:.55em; }}
    .etk {{ position:absolute; left:66px; right:80px; top:{UST + 200 + boy}px; font-size:64px; font-weight:700;
            line-height:1.15; }}
    .etk .vurgu {{ background:#111; color:{RENK["vurgu"]}; padding:0 10px; }}
    """
    t0 = ipucu_zamani(sh, sh.get("ipucu"), 0.15)
    sayac = max(1.0, min(1.4, sure * 0.3))
    js = [giris, "const d = S('.deger'); const p = {v:0};",
          f"const yaz = () => {{ d.textContent = p.v.toLocaleString('en-US', {{minimumFractionDigits:{ondalik}, "
          f"maximumFractionDigits:{ondalik}}}); }};",
          f"tl.fromTo(p, {{v:0}}, {{v:{deger}, duration:{sayac:.2f}, ease:'power3.out', onUpdate: yaz}}, {t0:.3f});",
          _kelime_girisi(f"#{sid}-etk", t0 + sayac * 0.6, 0.06)]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_alinti(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    foto = sh.get("gorsel")
    govde = f"""
    <div class="icerik tam" style="background:{RENK["murekkep"]}">
      {f'<div class="foto"><div class="kat"><img src="{_e(foto)}" alt=""></div></div>' if foto else ""}
      <div class="tirnak gb">“</div>
      <blockquote class="metin" id="{sid}-metin">{_kelime_spanlari(sh["metin"], sh.get("vurgu"), sid)}</blockquote>
      <div class="kim">— {_e(sh.get("kim", ""))}</div>
    </div>{perde}"""
    css = f"""
    .foto {{ position:absolute; left:0; right:0; top:0; height:760px; overflow:hidden; }}
    .tirnak {{ position:absolute; left:60px; top:{620 if foto else UST}px; font-size:260px; color:{RENK["vurgu"]}; }}
    .metin {{ position:absolute; left:70px; right:70px; top:{820 if foto else UST + 230}px; font-size:64px;
              font-weight:700; line-height:1.18; margin:0; color:#fff; }}
    .kim {{ position:absolute; left:72px; right:72px; top:{ICERIK_ALT - 70}px; font-size:38px; color:{RENK["vurgu"]};
            font-weight:700; }}
    """
    t0 = ipucu_zamani(sh, sh.get("ipucu"), 0.15)
    n = max(1, len(_kelime_ayir(sh["metin"])))
    aralik = max(0.04, min(0.15, (sure * 0.6) / n))
    js = [giris] + ([_kamera(sure, tohum)] if foto else [])
    js += [
        f"tl.fromTo(SA('#{sid}-metin .w'), {{opacity:.18}}, {{opacity:1, duration:.12, stagger:{aralik:.3f}}}, {t0:.3f});",
        f"tl.fromTo(S('.kim'), {{opacity:0}}, {{opacity:1, duration:.3}}, {min(sure - 0.5, t0 + n * aralik):.3f});",
    ]
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_zaman(sh: dict, gecis: str, tohum: int) -> str:
    """Dikey zaman çizgisi: yukarıdan aşağı akar."""
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    ol = (sh.get("olaylar") or [])[:4]
    adim = (ICERIK_ALT - UST - 260) / max(1, len(ol) - 1) if len(ol) > 1 else 0
    dug = []
    for i, o in enumerate(ol):
        y = UST + 60 + i * adim
        dug.append(
            f'<div class="dugum" id="{sid}-d{i}" style="top:{y:.0f}px"><div class="nokta"></div><div class="kutu">'
            f'<div class="tarih gb">{_e(o["tarih"])}</div><div class="olay">{_e(o["olay"])}</div></div></div>'
        )
    govde = f'<div class="icerik tam" style="background:{RENK["kagit"]}; color:#111"><div class="hat"></div>{"".join(dug)}</div>{perde}'
    css = f"""
    .hat {{ position:absolute; left:150px; width:8px; top:{UST + 40}px; height:{ICERIK_ALT - UST - 100}px; background:#111;
            transform-origin:50% 0; }}
    .dugum {{ position:absolute; left:154px; }}
    .nokta {{ position:absolute; left:-26px; top:-4px; width:52px; height:52px; border-radius:50%;
              background:{RENK["kirmizi"]}; border:8px solid #111; }}
    .kutu {{ position:absolute; left:70px; top:-30px; width:760px; }}
    .tarih {{ font-size:120px; }}
    .olay {{ font-size:48px; font-weight:700; line-height:1.15; }}
    """
    zam = _yayilim(sure, len(ol), 0.05, 0.65)
    js = [
        giris,
        f"tl.fromTo(S('.hat'), {{scaleY:0}}, {{scaleY:1, duration:{max(0.8, sure * 0.75):.2f}, ease:'none'}}, 0);",
    ]
    for i, o in enumerate(ol):
        t = ipucu_zamani(sh, o.get("ipucu"), zam[i])
        js += [f"tl.fromTo('#{sid}-d{i} .nokta', {{scale:0}}, {{scale:1, duration:.3, ease:'back.out(2)'}}, {t:.3f});",
               f"tl.fromTo('#{sid}-d{i} .kutu', {{opacity:0, x:-40}}, {{opacity:1, x:0, duration:.35, ease:'expo.out'}}, "
               f"{t + 0.06:.3f});"]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_ikili(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    sol, sag = sh["sol"], sh["sag"]
    govde = f"""
    <div class="icerik tam">
      <div class="yari ust"><div class="ic"><div class="etk">{_e(sol["etiket"])}</div><div class="dg gb">{_e(sol["deger"])}</div></div></div>
      <div class="yari alt"><div class="ic"><div class="etk">{_e(sag["etiket"])}</div><div class="dg gb">{_e(sag["deger"])}</div></div></div>
    </div>{perde}"""
    css = f"""
    .yari {{ position:absolute; left:0; right:0; display:flex; }}
    .yari.ust {{ top:0; height:{UST + 430}px; background:{RENK["murekkep"]}; align-items:flex-end; padding-bottom:40px; }}
    .yari.alt {{ top:{UST + 430}px; height:{ICERIK_ALT - UST - 400}px; background:{RENK["vurgu"]}; color:#111;
                 align-items:center; }}
    .ic {{ padding:0 70px; }}
    .etk {{ font-size:52px; font-weight:700; margin-bottom:10px; }}
    .dg {{ font-size:200px; line-height:.95; }}
    """
    t1 = ipucu_zamani(sh, sol.get("ipucu"), sure * 0.1)
    t2 = ipucu_zamani(sh, sag.get("ipucu"), sure * 0.45)
    js = [giris,
          f"tl.fromTo(S('.yari.ust .ic'), {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.4, ease:'expo.out'}}, {t1:.3f});",
          f"tl.fromTo(S('.yari.alt'), {{clipPath:'inset(100% 0 0 0)'}}, {{clipPath:'inset(0% 0 0 0)', duration:.45, ease:'expo.out'}}, {max(0, t2 - .1):.3f});",
          f"tl.fromTo(S('.yari.alt .ic'), {{opacity:0}}, {{opacity:1, duration:.3}}, {t2:.3f});"]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_ifade(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    foto = sh.get("gorsel")
    metin = sh["metin"]
    boy = 150 if len(metin) < 30 else (124 if len(metin) < 55 else 100)
    arka = (f'<div class="kat"><img src="{_e(foto)}" alt=""></div><div class="tam" style="background:rgba(8,8,10,.62)"></div>'
            if foto else "")  # fmt: skip
    govde = f"""
    <div class="icerik tam" style="background:{RENK["murekkep"]}">{arka}
      <h1 class="gb cumle" id="{sid}-c" style="font-size:{boy}px">{_kelime_spanlari(metin, sh.get("vurgu"), sid)}</h1>
    </div>{perde}"""
    css = f".cumle {{ position:absolute; left:70px; right:70px; top:{UST + 220}px; margin:0; color:#fff; }}"
    n = max(1, len(_kelime_ayir(metin)))
    js = [giris] + ([_kamera(sure, tohum)] if foto else [])
    js.append(_kelime_girisi(f"#{sid}-c", ipucu_zamani(sh, sh.get("ipucu"), 0.1), max(0.06, min(0.2, sure * 0.5 / n))))
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_bolum(sh: dict, gecis: str, tohum: int) -> str:
    # Shorts'ta bölüm kartı yerine aynı satır büyük ifade olarak geçer
    return d_ifade({**sh, "metin": sh.get("baslik", ""), "gorsel": sh.get("gorsel")}, gecis, tohum)


def d_kapanis(sh: dict, gecis: str, tohum: int) -> str:
    sid, sure = sh["id"], sh["sure"]
    govde = f"""
    <div class="icerik tam" style="background:{RENK["murekkep"]}">
      <h1 class="gb son" id="{sid}-son">{_kelime_spanlari(sh["metin"], sh.get("vurgu"), sid)}</h1>
      <div class="cta">Full story on the channel</div>
    </div>"""
    css = f"""
    .son {{ position:absolute; left:70px; right:70px; top:{UST + 200}px; font-size:130px; margin:0; color:#fff; }}
    .cta {{ position:absolute; left:70px; top:{ALT - 260}px; font-size:52px; font-weight:700; color:#111;
            background:{RENK["vurgu"]}; padding:14px 26px; }}
    """
    js = [_kelime_girisi(f"#{sid}-son", 0.15, 0.09),
          f"tl.fromTo(S('.cta'), {{clipPath:'inset(0 100% 0 0)'}}, {{clipPath:'inset(0 0% 0 0)', duration:.45, "
          f"ease:'expo.out'}}, {max(0.6, sure - 2.4):.3f});"]  # fmt: skip
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


def d_harita(sh: dict, gecis: str, tohum: int) -> str:
    """Yatay uydu uçuşu dikeyde ortadan kırpılır: hedef zaten kadraj merkezinde."""
    sid, sure = sh["id"], sh["sure"]
    perde, giris = _giris_js(gecis, sid)
    govde = f"""
    <div class="icerik tam">
      <video id="{sid}-v" class="clip" src="{_e(sh["video"])}" data-start="0" data-duration="{sure:.3f}" muted playsinline
             style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover"></video>
      <div class="nokta" id="{sid}-n"></div>
      <div class="yer gb" id="{sid}-yer">{_e(sh.get("yer", ""))}</div>
      <div class="kredi" data-layout-ignore>{_e(sh.get("kredi", ""))}</div>
    </div>{perde}"""
    css = f"""
    .nokta {{ position:absolute; left:{W // 2 - 16}px; top:{H // 2 - 16}px; width:32px; height:32px; border-radius:50%;
              background:{RENK["kirmizi"]}; border:6px solid #fff; }}
    .yer {{ position:absolute; left:70px; right:70px; top:{UST + 60}px; font-size:130px; color:#111; text-align:center; }}
    .yer {{ background:{RENK["vurgu"]}; }}
    .kredi {{ bottom:auto; top:{ICERIK_ALT - 40}px; right:30px; font-size:20px; }}
    """
    t = max(0.4, sure * 0.6)
    js = [
        giris,
        f"tl.fromTo('#{sid}-n', {{scale:0}}, {{scale:1, duration:.35, ease:'back.out(2.2)'}}, {t:.3f});",
        f"tl.fromTo('#{sid}-yer', {{clipPath:'inset(0 100% 0 0)'}}, {{clipPath:'inset(0 0% 0 0)', duration:.45, ease:'expo.out'}}, {t + 0.1:.3f});",
    ]
    return _sahne_html(sid, sure, govde, css, "\n".join(js))


DIKEY = {"harita": d_harita, "foto": d_foto, "manset": d_manset, "sayi": d_sayi, "alinti": d_alinti, "zaman": d_zaman, "bolum": d_bolum,
         "ikili": d_ikili, "ifade": d_ifade, "kapanis": d_kapanis}  # fmt: skip


def altyazi_html(kelimeler: list[dict], sure: float) -> str:
    """Kelime kelime vurgulu altyazı: 2-4 kelimelik gruplar, 150 ms duraklamada ya da cümle sonunda kırılır
    (captions.md). Etkin kelime vurgu renginde; grup bitince sert kapanır."""
    gruplar, simdiki = [], []
    for i, k in enumerate(kelimeler):
        simdiki.append(k)
        sonraki = kelimeler[i + 1] if i + 1 < len(kelimeler) else None
        kir = len(simdiki) >= 3 or k["w"][-1:] in ".!?," or sonraki is None or sonraki["s"] - k["e"] > 0.15
        if kir:
            gruplar.append(simdiki)
            simdiki = []
    govde, js = [], []
    baslar = []
    for g in gruplar:  # tekdüze artan açılış anları: iki grup aynı anda görünmez
        baslar.append(max(0.05, g[0]["s"] - 0.05, (baslar[-1] + 0.1) if baslar else 0.05))
    for gi, g in enumerate(gruplar):
        bas = baslar[gi]
        son = min(sure, baslar[gi + 1] if gi + 1 < len(gruplar) else g[-1]["e"] + 0.4)  # sonraki açılırken kapanır
        kel = " ".join(f'<span class="k" id="a{gi}-{wi}">{_e(w["w"].upper())}</span>' for wi, w in enumerate(g))
        govde.append(f'<div class="grup" id="a{gi}">{kel}</div>')
        js.append(f"tl.set('#a{gi}', {{opacity:1, visibility:'visible'}}, {bas:.3f});")
        js.append(f"tl.fromTo('#a{gi}', {{scale:.92}}, {{scale:1, duration:.12, ease:'power2.out'}}, {bas:.3f});")
        for wi, w in enumerate(g):
            js.append(f"tl.set('#a{gi}-{wi}', {{color:'{RENK['vurgu']}'}}, {max(bas, w['s']):.3f});")
            js.append(f"tl.set('#a{gi}-{wi}', {{color:'#ffffff'}}, {min(son, max(w['e'], w['s'] + 0.12)):.3f});")
        js.append(f"tl.set('#a{gi}', {{opacity:0, visibility:'hidden'}}, {son:.3f});")
    return f"""<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    .grup {{ position:absolute; left:40px; right:40px; top:{ALTYAZI_Y}px; text-align:center; opacity:0;
             visibility:hidden; font-family:'Archivo Black', sans-serif; font-size:76px; line-height:1.05; color:#fff;
             -webkit-text-stroke: 10px #000; paint-order: stroke fill; }}
    .k {{ display:inline-block; margin:0 8px; }}
  </style>
  <div id="root" data-composition-id="altyazi" data-width="{W}" data-height="{H}">
    {"".join(govde)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join(js)}
    tl.set({{}}, {{}}, {sure:.3f});
    window.__timelines["altyazi"] = tl;
  </script>
</template>
"""


def kanca_html(metin: str, sure: float) -> str:
    """0. karede ekranda duran kanca satırı (kapak karesi da budur); ilk ~2,6 sn sonra çekilir."""
    return f"""<template>
  <style>
    #root {{ position:absolute; inset:0; }}
    .panel {{ position:absolute; left:0; right:0; top:0; height:{UST + 420}px; background:{RENK["murekkep"]}; }}
    .kanca {{ position:absolute; left:50px; right:50px; top:{UST + 10}px; font-family:'League Gothic', sans-serif;
              text-transform:uppercase; font-size:120px; line-height:.95; color:#111; }}
    .kanca span {{ background:{RENK["vurgu"]}; padding:0 16px; box-decoration-break:clone; -webkit-box-decoration-break:clone; }}
  </style>
  <div id="root" data-composition-id="kanca" data-width="{W}" data-height="{H}">
    <div class="panel" id="kanca-panel" data-layout-allow-occlusion></div>
    <div class="kanca" id="kanca-satir" data-layout-allow-overlap><span>{_e(metin)}</span></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo('#kanca-satir', {{opacity:1}}, {{opacity:1, duration:{sure - 0.25:.2f}}}, 0);
    tl.to('#kanca-satir', {{opacity:0, y:-30, duration:.25, ease:'power2.in'}}, {sure - 0.25:.2f});
    tl.to('#kanca-panel', {{yPercent:-101, duration:.3, ease:'power3.in'}}, {sure - 0.3:.2f});
    window.__timelines["kanca"] = tl;
  </script>
</template>
"""


def kesit_plani(plan: dict, sahne_idx: list[int]) -> tuple[dict, float]:
    """Yatay plandan kesitin sahneleri, kesit başına göre yeniden zamanlanmış. Dönüş: (alt plan, kaynak başlangıcı)."""
    secili = [plan["sahneler"][i] for i in sahne_idx]
    t0 = secili[0]["bas"]
    sahneler = []
    for j, sh in enumerate(secili):
        yeni = dict(sh)
        yeni["id"] = f"k{j + 1:02d}"
        yeni["bas"] = round(sh["bas"] - t0, 3)
        if j == len(secili) - 1:  # son sahne anlatım bitince 0,6 sn tutar
            son_kelime = max((k["e"] for k in sh.get("kelimeler") or []), default=sh["sure"])
            yeni["sure"] = round(min(sh["sure"], son_kelime + 0.6), 3) if sh["tur"] != "kapanis" else sh["sure"]
        sahneler.append(yeni)
    toplam = round(sahneler[-1]["bas"] + sahneler[-1]["sure"], 3)
    return {"sure": toplam, "sahneler": sahneler, "muzik": plan.get("muzik")}, t0


def proje_yaz(plan: dict, kesit: dict, dizin: Path, varlik: dict[str, Path], dikey_gorsel: dict[str, Path]) -> Path:
    """Bir kesitin HyperFrames projesi. `dikey_gorsel`: yatay görsel yolu → 1080×1920 hazırlanmış karşılığı."""
    alt, t0 = kesit_plani(plan, kesit["sahneler"])
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "compositions").mkdir(exist_ok=True)
    for hedef, kaynak in {**varlik, **dikey_gorsel}.items():
        h = dizin / hedef
        h.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kaynak, h)
    onceki = None
    kelimeler = []
    for i, sh in enumerate(alt["sahneler"]):
        g = "kesme" if i == 0 else kurgu.gecis_sec(i + 1, sh["tur"], onceki)
        onceki = g
        if sh.get("gorsel"):
            sh["gorsel"] = sh["gorsel"].replace("assets/img/", "assets/dikey/")
        if i == 0 and sh["tur"] == "foto":
            sh.pop("baslik", None)  # kanca satırı üst bandı tutuyor
        elif i == 0 and sh["tur"] in ("ifade", "bolum"):
            sh = {**sh, "tur": "foto"} if sh.get("gorsel") else sh
        (dizin / "compositions" / f"{sh['id']}.html").write_text(DIKEY[sh["tur"]](sh, g, i * 5 + 1), encoding="utf-8")
        kelimeler += [{"w": k["w"], "s": round(sh["bas"] + k["s"], 3), "e": round(sh["bas"] + k["e"], 3)}
                      for k in sh.get("kelimeler") or []]  # fmt: skip
    sure = alt["sure"]
    (dizin / "compositions" / "altyazi.html").write_text(altyazi_html(kelimeler, sure), encoding="utf-8")
    kanca_sure = min(2.6, sure)
    (dizin / "compositions" / "kanca.html").write_text(kanca_html(kesit["kanca"], kanca_sure), encoding="utf-8")
    hostlar = [
        f'<div id="{sh["id"]}" data-composition-id="{sh["id"]}" data-composition-src="compositions/{sh["id"]}.html" '
        f'data-start="{sh["bas"]:.3f}" data-duration="{sh["sure"]:.3f}" data-track-index="1" '
        f'data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>'
        for sh in alt["sahneler"]
    ]
    hostlar.append(
        f'<div id="kanca" data-composition-id="kanca" data-composition-src="compositions/kanca.html" '
        f'data-start="0" data-duration="{kanca_sure:.3f}" data-track-index="3" data-track-kind="graphics" '
        f'data-width="{W}" data-height="{H}" style="z-index:20"></div>'
    )
    hostlar.append(
        f'<div id="altyazi" data-composition-id="altyazi" data-composition-src="compositions/altyazi.html" '
        f'data-start="0" data-duration="{sure:.3f}" data-track-index="2" data-track-kind="captions" '
        f'data-width="{W}" data-height="{H}" style="z-index:30"></div>'
    )
    sesler = [
        f'<audio id="anlatim" class="clip" src="assets/ses/anlatim.wav" data-start="0" data-media-start="{t0:.3f}" '
        f'data-duration="{sure:.3f}" data-track-index="10" data-volume="1" data-fade-out="0.3"></audio>'
    ]
    if alt.get("muzik"):
        sesler.append(
            f'<audio id="muzik" class="clip" src="{alt["muzik"]["dosya"]}" data-start="0" '
            f'data-media-start="{t0 % 60:.3f}" data-duration="{sure:.3f}" data-track-index="11" '
            f'data-volume="{alt["muzik"].get("ses", 0.11)}" data-fade-in="0.2" data-fade-out="0.8"></audio>'
        )
    (dizin / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>* {{ margin:0; padding:0; box-sizing:border-box; }} html, body {{ width:{W}px; height:{H}px; overflow:hidden;
background:{RENK['murekkep']}; }} #root {{ position:relative; width:100%; height:100%; }}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{sure:.3f}" data-width="{W}"
data-height="{H}" data-fps="{kurgu.FPS}">
{chr(10).join(hostlar)}
{chr(10).join(sesler)}
</div><script>window.__timelines = window.__timelines || {{}}; window.__timelines["main"] = gsap.timeline({{ paused: true }});</script>
</body></html>
""", encoding="utf-8")  # fmt: skip
    (dizin / "kesit.json").write_text(json.dumps({"kesit": kesit, "t0": t0, "sure": sure}, ensure_ascii=False, indent=1),
                                      encoding="utf-8")  # fmt: skip
    return dizin
