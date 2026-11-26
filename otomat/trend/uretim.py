"""Trend videosu uçtan uca: seçim → kaynak → senaryo → ses+zaman → kurgu → render → ses seviyesi → metadata.

Her aşama çıktısını `calisma/trend/<id>/` altına yazar; yeniden koşunca biten aşama atlanır (uzun işlerde yarıda
kalınca baştan başlamasın). Kullanım:

    uv run --extra ses python -m otomat.trend.uretim           # radar + editör günün konusunu seçer
    uv run python -m otomat.trend.uretim --konu "Grand Theft Auto VI"   # konu elle
    uv run python -m otomat.trend.uretim --id 2026-11-20-gta-vi        # var olan işi sürdür
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from otomat.ayarlar import KOK
from otomat.trend import kurgu, medya
from otomat.trend.llm import Oturum

CALISMA = KOK / "calisma" / "trend"
GECMIS = KOK / "durum" / "trend_gecmis.json"
KANAL_ADI = "Why It's Everywhere"  # çalışma adı (K-38); kanal açılınca kanallar/trend/kanal.toml


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def _yaz(yol: Path, veri) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def _oku(yol: Path):
    return json.loads(yol.read_text(encoding="utf-8"))


def gecmis() -> list[str]:
    return _oku(GECMIS) if GECMIS.exists() else []


# ------------------------------------------------------------------------------------------------- aşamalar
def asama_secim(d: Path, oturum: Oturum, konu: str | None) -> dict:
    yol = d / "secim.json"
    if yol.exists():
        return _oku(yol)
    if konu:
        secim = {"secim": {"hikaye": konu, "wiki_baslik": konu, "ilgili": [], "neden": "", "aci": "",
                           "gorsel_aramalari": [konu]}}  # fmt: skip
        _yaz(yol, secim)
        return secim
    from otomat.trend import secici

    zengin = secici.adaylar()
    secim = secici.sec(oturum, zengin, gecmis())
    secici.kaydet(d / "adaylar.json", zengin, secim)
    _yaz(yol, secim)
    return secim


def asama_kaynak(d: Path, secim: dict) -> dict:
    yol = d / "kaynak.json"
    if yol.exists():
        return _oku(yol)
    from otomat.trend import kaynak

    s = secim["secim"]
    wiki = kaynak.wiki_metin(s["wiki_baslik"])
    ilgili = []
    for b in s.get("ilgili", [])[:3]:
        try:
            ilgili.append(kaynak.wiki_metin(b))
        except Exception:  # noqa: BLE001
            pass
    haber = kaynak.haberler(s.get("hikaye") or wiki.baslik, gun=4, en_cok=20)
    if len(haber) < 5:
        haber += [h for h in kaynak.haberler(wiki.baslik, gun=4, en_cok=20) if h.url not in {x.url for x in haber}]
    # görseller: makalelerdeki serbest dosyalar + editörün aramaları
    dosyalar = list(dict.fromkeys(wiki.dosyalar + [f for w in ilgili for f in w.dosyalar]))
    gruplar = [kaynak.commons_dosyalar(dosyalar) if dosyalar else []]
    for q in (s.get("gorsel_aramalari") or [])[:8]:
        try:
            gruplar.append(kaynak.commons_ara(q, n=12))
        except Exception:  # noqa: BLE001
            gruplar.append([])
    # çeşitlilik: makale görselleri en çok 10, her arama en çok 4; kalan yer sırayla doldurulur
    gorulen, gorseller = set(), []
    for tur in range(3):
        for gi, grup in enumerate(gruplar):
            kota = (10 if gi == 0 else 4) if tur == 0 else 3
            alinan = 0
            for g in grup:
                if alinan >= kota or len(gorseller) >= 48:  # süzgeç (gorsel_suz) ilgisizleri sonra atar
                    break
                if g.dosya in gorulen or not kaynak.gorsel_uygun(g):
                    continue
                gorulen.add(g.dosya)
                gorseller.append(g)
                alinan += 1
    ham = d / "gorsel_ham"
    indirilen = []
    for g in gorseller:
        try:
            yol_g = kaynak.gorsel_indir(g, ham)
            indirilen.append({**g.__dict__, "yerel": str(yol_g)})
        except Exception:  # noqa: BLE001
            pass
    indirilen = medya.yakin_kopyalari_ele(indirilen)
    veri = {"wiki": wiki.__dict__, "ilgili": [w.__dict__ for w in ilgili],
            "haberler": [h.__dict__ for h in haber], "gorseller": indirilen}  # fmt: skip
    _yaz(yol, veri)
    return veri


SISTEM_GORSEL_SUZ = """You are the picture researcher of a documentary explainer. You get the STORY and a list of
freely licensed images found by keyword search (id: file title). Keyword search drags in unrelated files that only share
a word (a war memorial at the same university, a 1914 book scan, an exam sheet). Keep every image that could honestly
illustrate a moment of THIS story: its named people, the places where it happens, its objects, documents, events,
or its subject shown directly (a diagram of the actual thing). Drop: portraits of anyone who is not named in the story
(an unnamed or different person is the wrong person on screen), places that only share a city or institution with the
story, and anything from an unrelated era or event (war ruins, an old book scan). When unsure, drop. Return ONLY JSON:
{"tut": ["G1", ...]}"""


def gorsel_suz(oturum: Oturum, hikaye: str, kay: dict, en_az: int = 6) -> dict:
    """Konuyla ilgisiz görselleri senaryodan önce havuzdan atar (11-26 Riemann havuzu: 32 görselin ~10'u Kentucky
    tarihi, 1914 havacıları, aynı savaş anıtının dört karesi). Eşleştirici anlamca en yakını seçse de ilgili görsel
    yoksa ilgisizi gösteriyordu. Model yanıt vermezse ya da 6'dan az bırakırsa havuz olduğu gibi kalır; az ama doğru
    görselin boşluğunu stok video doldurur."""
    from otomat.trend import senaryo as senaryo_m

    g = kay["gorseller"]
    liste = senaryo_m.gorsel_listesi([_gorsel_nesne(x) for x in g])
    try:
        y = oturum.json_sor(SISTEM_GORSEL_SUZ, f"STORY: {hikaye}\n\nIMAGES:\n{liste}", model="glm-5.3",
                            en_cok=1500, sicaklik=0.0, dusun=False)  # fmt: skip
        tut = {int(str(k)[1:]) - 1 for k in (y.get("tut") or []) if str(k)[1:].isdigit()}  # type: ignore[union-attr]
    except Exception as e:  # noqa: BLE001
        print(f"görsel süzme atlandı: {str(e)[:120]}", flush=True)
        return {**kay, "suzuldu": True}
    kalan = [x for i, x in enumerate(g) if i in tut]
    if len(kalan) < en_az:
        print(f"görsel süzme {len(kalan)} bırakıyordu (< {en_az}), havuz korunur", flush=True)
        return {**kay, "suzuldu": True}
    print(f"görsel süzme: {len(g)} → {len(kalan)}", flush=True)
    return {**kay, "gorseller": kalan, "suzuldu": True}


def _wiki_nesne(dct: dict):
    from otomat.trend.kaynak import WikiMetin

    return WikiMetin(**dct)


def _haber_nesne(dct: dict):
    from otomat.trend.kaynak import Haber

    return Haber(**{**dct, "zaman": dt.datetime.fromisoformat(str(dct["zaman"]))})


def _gorsel_nesne(dct: dict):
    from otomat.trend.kaynak import Gorsel

    return Gorsel(**{k: v for k, v in dct.items() if k not in ("yerel", "hazir")})


def asama_senaryo(d: Path, oturum: Oturum, secim: dict, kay: dict) -> dict:
    yol = d / "senaryo.json"
    if yol.exists():
        return _oku(yol)
    from otomat.trend import senaryo

    wiki = _wiki_nesne(kay["wiki"])
    haber = [_haber_nesne(h) for h in kay["haberler"]]
    ek = [(f"https://en.wikipedia.org/wiki/{w['baslik'].replace(' ', '_')}", w["metin"][:5000]) for w in kay["ilgili"]]
    metin, bag = senaryo.kaynak_paketi(wiki, haber, ek)
    gorsel = [_gorsel_nesne(g) for g in kay["gorseller"]]
    gmetin = senaryo.gorsel_listesi(gorsel)
    s = secim["secim"]
    kayit: list = []
    sen = senaryo.uret(oturum, {"ad": s["hikaye"], "neden": s.get("neden", ""), "aci": s.get("aci", "")}, metin, gmetin,
                       len(gorsel), kayit=kayit, dizin=d)  # fmt: skip
    _yaz(d / "senaryo_kayit.json", {"kayit": kayit, "kaynak_bag": bag, "kullanim": oturum.kullanim})
    (d / "kaynak_paketi.txt").write_text(metin + "\n\n" + gmetin, encoding="utf-8")
    son = kayit[-1] if kayit else {}
    if any("kesit" in k for k in son.get("kod") or []):  # kesit eksiği Shorts sayısını azaltır, videoyu durdurmaz
        from otomat.trend.senaryo import kesit_sec

        sen["kesitler"] = kesit_sec(oturum, sen["sahneler"])
        son["kod"] = [k for k in son["kod"] if "kesit" not in k]
    if son.get("kod"):
        _yaz(d / "senaryo_kusurlu.json", sen)
        raise RuntimeError(f"senaryo kod kapısından geçmedi: {son['kod'][:6]}")
    _yaz(yol, sen)
    return sen


def asama_ses(d: Path, sen: dict) -> dict:
    yol = d / "zaman.json"
    if yol.exists():
        return _oku(yol)
    from otomat.trend import zamanla

    z = zamanla.seslendir_ve_zamanla(sen["sahneler"], d / "ses")
    _yaz(yol, z)
    return z


def plan_kur(sen: dict, kay: dict, z: dict, secim: dict, kategori: str) -> tuple[dict, dict[str, Path]]:
    from otomat.trend import derinlik, stok

    gorsel = kay["gorseller"]
    varlik: dict[str, Path] = {"assets/ses/anlatim.wav": Path(z["wav"])}
    sahneler = []
    for i, (sh, zz) in enumerate(zip(sen["sahneler"], z["sahneler"], strict=True)):
        p = dict(sh)
        p["id"] = f"s{i + 1:02d}"
        p.update(bas=zz["bas"], sure=zz["sure"], kelimeler=zz["kelimeler"], tohum=i * 7 + 3)
        if g := sh.get("gorsel"):
            gi = int(str(g)[1:]) - 1
            if 0 <= gi < len(gorsel):
                hedef = f"assets/img/g{gi + 1:02d}.jpg"
                hazir = Path(gorsel[gi]["hazir"])
                varlik[hedef] = hazir
                p["gorsel"] = hedef
                p["kredi"] = gorsel[gi]["kredi_satiri"]
                # 2.5D parallax için derinlik haritası (kurgu.zemin): düz kare + yavaş zoom "slayt" gibiydi (11-20)
                # dolgulu (dikey) fotoğrafta derinlik yok: fotoğrafla bulanık dolgu ayrı kayıp kesik gibi duruyordu
                if not medya.dolgulu(Path(gorsel[gi]["yerel"])):
                    dh = derinlik.harita(hazir, hazir.parent.parent / "derinlik" / f"g{gi + 1:02d}.png")
                    varlik[f"assets/derinlik/g{gi + 1:02d}.png"] = dh
                    p["derinlik"] = f"assets/derinlik/g{gi + 1:02d}.png"
                    if sh["tur"] == "bolum":  # bölüm numarası kişinin arkasında (kurgu.sahne_bolum)
                        from otomat.trend import kesik

                        if k := kesik.kes(hazir, hazir.parent.parent / "kesit" / f"h{gi + 1:02d}.png"):
                            varlik[f"assets/kesit/h{gi + 1:02d}.png"] = k
                            p["kesit"] = f"assets/kesit/h{gi + 1:02d}.png"
            else:
                p.pop("gorsel")
        p.pop("klip", None)
        if stok.gecerli_klip(sh):
            k = sh["klip"]
            try:
                hit = {"id": k["id"], "duration": k.get("sure"), "videos": {"medium": {"url": k["url"]}}}
                yol = stok.hazirla(hit, zz["sure"], Path(z["wav"]).parent.parent / "klip")
                varlik[f"assets/klip/{yol.name}"] = yol
                p["klip"] = f"assets/klip/{yol.name}"
                p["kredi"] = "Video: Pixabay"
            except Exception as e:  # noqa: BLE001 — klip inmezse sahne fotoğrafta kalır
                print(f"stok klip düştü ({k.get('id')}): {str(e)[:120]}", flush=True)
        if sh["tur"] == "kapanis":
            p["kanal"] = KANAL_ADI
        if sh["tur"] == "harita":
            from otomat.trend import harita

            k = harita.koordinat(sh.get("yer_wiki") or sh.get("yer", ""))
            try:
                if not k:
                    raise RuntimeError("koordinat yok")
                hd = KOK / "calisma" / "trend" / "harita"
                v = harita.pisir(k[0], k[1], sh.get("yakinlik", "city"), zz["sure"], hd)
                hedef = f"assets/harita/{v.name}"
                varlik[hedef] = v
                p.update(video=hedef, kredi=harita.KREDI)
            except Exception as e:  # noqa: BLE001 — harita olmazsa yer adı büyük ifade olur
                print(f"harita düştü ({sh.get('yer')}): {str(e)[:120]}", flush=True)
                p.update(tur="ifade", metin=sh.get("yer", ""))
        sahneler.append(p)
    # müzik anlatıma önceden karıştırılır (asama_muzik): kökte ayrı müzik izi yok
    plan = {"sure": z["sure"], "sahneler": sahneler, "muzik": None}
    return plan, varlik


def asama_muzik(d: Path, sen: dict, plan: dict, z: dict) -> Path:
    """Bölüm başına üretilen müzik + kısılma zarfı, anlatımla tek WAV (muzik.py)."""
    from otomat.trend import muzik

    hedef = d / "ses" / "karisim.wav"
    bolumler = muzik.bolumler(plan["sahneler"], sen.get("muzik_plani"), plan["sure"])
    tohum = sum(map(ord, d.name)) % 1000
    parcalar = muzik.uret(bolumler, d / "muzik", tohum)
    if not hedef.exists() or any(p.stat().st_mtime > hedef.stat().st_mtime for p in parcalar):
        muzik.karistir(Path(z["wav"]), parcalar, bolumler, plan["sahneler"], plan["sure"], hedef)
    _yaz(d / "muzik" / "bolumler.json", bolumler)
    print("müzik: " + ", ".join(f"{b['ruh']} {b['son'] - b['bas']:.0f} sn" for b in bolumler), flush=True)
    return hedef


def gorselleri_hazirla(d: Path, kay: dict) -> None:
    for g in kay["gorseller"]:
        if "hazir" in g and Path(g["hazir"]).exists():
            continue
        g["hazir"] = str(medya.hazirla(Path(g["yerel"]), d / "gorsel" / (Path(g["yerel"]).stem + ".jpg")))
    _yaz(d / "kaynak.json", kay)


def ses_seviyesi(video: Path, hedef: Path, lufs: float = -14.0) -> Path:
    """İki geçişli loudnorm (-14 LUFS, -1 dBTP); görüntü kopyalanır."""
    olc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af",
                          f"loudnorm=I={lufs}:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")  # fmt: skip
    j = json.loads(olc.stderr[olc.stderr.rfind("{") : olc.stderr.rfind("}") + 1])
    af = (
        f"loudnorm=I={lufs}:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
        f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
    )
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(hedef)], check=True)  # fmt: skip
    return hedef


def bolum_zamanlari(plan: dict) -> list[tuple[float, str]]:
    out = [(0.0, "Intro")]
    for sh in plan["sahneler"]:
        if sh["tur"] == "bolum":
            out.append((sh["bas"], sh["baslik"].title()))
    return out


def _dk(t: float) -> str:
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def metadata(sen: dict, plan: dict, kay: dict, bag: dict) -> dict:
    kullanilan = {sh.get("gorsel") for sh in plan["sahneler"] if sh.get("gorsel")}
    krediler = []
    for i, g in enumerate(kay["gorseller"]):
        if f"assets/img/g{i + 1:02d}.jpg" in kullanilan:
            krediler.append(f"- {g['dosya'].removeprefix('File:')}: {g['yazar'] or 'Wikimedia Commons'}, {g['lisans']} "
                            f"({g['sayfa']})")  # fmt: skip
    stok_kredi = sorted({f"{sh['klip']['yazar']} ({sh['klip']['sayfa']})" for sh in sen["sahneler"]
                         if isinstance(sh.get("klip"), dict) and sh["klip"].get("sayfa")})  # fmt: skip
    kaynaklar = [f"- Wikipedia, \"{kay['wiki']['baslik']}\" (revision {kay['wiki']['revid']}): "
                 f"https://en.wikipedia.org/w/index.php?oldid={kay['wiki']['revid']} (CC BY-SA 4.0)"]  # fmt: skip
    kullanilan_n = sorted({k for sh in sen["sahneler"] for k in (sh.get("kaynak") or []) if str(k).startswith("N")})
    for k in kullanilan_n[:12]:
        if k in bag:
            kaynaklar.append(f"- {bag[k]}")
    bolumler = "\n".join(f"{_dk(t)} {b}" for t, b in bolum_zamanlari(plan))
    aciklama = (f"{sen.get('aciklama', '').strip()}\n\n{bolumler}\n\nSources:\n" + "\n".join(kaynaklar) +
                "\n\nPhotos (Wikimedia Commons):\n" + "\n".join(krediler) +
                ("\nStock footage (Pixabay Content License): " + ", ".join(stok_kredi) if stok_kredi else "") +
                ("\nSatellite imagery: Esri, Maxar, Earthstar Geographics."
                 if any(sh["tur"] == "harita" for sh in plan["sahneler"]) else "") +
                "\n\nMusic: original score composed for this video (ACE-Step 1.5, MIT)."
                "\nSound effects: Pixabay Content License."
                "\nNarration is AI-generated (synthetic voice). Script researched from the sources above and "
                "fact-checked line by line against them.")  # fmt: skip
    return {
        "basliklar": sen.get("baslik_adaylari", []),
        "baslik": (sen.get("baslik_adaylari") or [""])[0],
        "aciklama": aciklama[:4900],
        "kapak_metni": sen.get("kapak_metni", ""),
        "tez": sen.get("tez", ""),
    }


def calistir(konu: str | None = None, is_id: str | None = None, render_yap: bool = True) -> Path:
    if is_id:
        d = CALISMA / is_id
    else:
        ad = f"{dt.date.today():%Y-%m-%d}-{_slug(konu)}" if konu else f"{dt.datetime.now():%Y-%m-%d-%H%M}-gunun-konusu"
        d = CALISMA / ad
    d.mkdir(parents=True, exist_ok=True)
    oturum = Oturum(d.name)
    secim = asama_secim(d, oturum, konu)
    print("seçim:", secim["secim"]["hikaye"], "|", secim["secim"].get("aci", ""), flush=True)
    kay = asama_kaynak(d, secim)
    print(f"kaynak: wiki {len(kay['wiki']['metin'])} karakter, {len(kay['haberler'])} haber, "
          f"{len(kay['gorseller'])} görsel", flush=True)  # fmt: skip
    if not kay.get("suzuldu") and not (d / "senaryo.json").exists():  # kimlikler (G1…) senaryodan önce sabitlenir
        kay = gorsel_suz(oturum, secim["secim"]["hikaye"], kay)
        _yaz(d / "kaynak.json", kay)
    gorselleri_hazirla(d, kay)
    sen = asama_senaryo(d, oturum, secim, kay)
    if not sen.get("gorsel_eslendi"):  # anlamla görsel ataması (yanlış kişiyi göstermesin); bir kez, kayıtlı
        from otomat.trend import senaryo as senaryo_m

        gmetin = senaryo_m.gorsel_listesi([_gorsel_nesne(g) for g in kay["gorseller"]])
        degisen = senaryo_m.gorsel_eslestir(
            oturum, sen, gmetin, len(kay["gorseller"]), konu=secim["secim"].get("wiki_baslik", "")
        )
        _yaz(d / "senaryo.json", sen)
        print(f"görsel eşleştirme: {len(degisen)} değişiklik", flush=True)
    n = sum(len(s["anlatim"].split()) for s in sen["sahneler"])
    print(f"senaryo: {len(sen['sahneler'])} sahne, {n} kelime | tez: {sen.get('tez')}", flush=True)
    z = asama_ses(d, sen)
    print(f"ses: {z['sure']:.1f} sn", flush=True)
    if not sen.get("stok_secildi"):  # kişiye özgü olmayan sahnelere stok video (stok.py); bir kez, kayıtlı
        from otomat.trend import stok

        sureler = {i: zz["sure"] for i, zz in enumerate(z["sahneler"])}
        yapilan = stok.uygula(oturum, sen["sahneler"], sureler)
        sen["stok_secildi"] = True
        _yaz(d / "senaryo.json", sen)
        print(f"stok video: {len([y for y in yapilan if y.startswith('sahne')])} sahne", flush=True)
    kategori = "other"
    if (d / "adaylar.json").exists():
        for a in _oku(d / "adaylar.json")["adaylar"]:
            if a.get("wiki") and a["wiki"].replace("_", " ") == secim["secim"]["wiki_baslik"]:
                kategori = (a.get("ts") or {}).get("kategori", "other")
    plan, varlik = plan_kur(sen, kay, z, secim, kategori)
    varlik["assets/ses/anlatim.wav"] = asama_muzik(d, sen, plan, z)
    if (d / "elestiri.json").exists():  # önceki eleştirinin düzeltmeleri her koşuda yeniden uygulanır
        from otomat.trend import elestirmen

        elestirmen.duzelt(plan, _oku(d / "elestiri.json")["bulgular"])
    proje = kurgu.proje_yaz(plan, d / "proje", varlik)
    rapor = kurgu.denetle(proje)
    _yaz(d / "denetim.json", rapor)
    if not (d / "elestiri.json").exists():
        from otomat.trend import elestirmen

        sayfalar = kurgu.inceleme_sayfalari(proje)
        bulgular = elestirmen.sahneye_bagla(elestirmen.incele(sayfalar, sen.get("tez", ""), oturum), plan)
        yapilan = elestirmen.duzelt(plan, bulgular)
        _yaz(d / "elestiri.json", {"bulgular": bulgular, "duzeltmeler": yapilan})
        if yapilan:  # düzeltilen sahneler yeniden yazılır
            proje = kurgu.proje_yaz(plan, d / "proje", varlik)
            _yaz(d / "denetim.json", kurgu.denetle(proje))
        print(f"eleştirmen: {len(bulgular)} bulgu, {len(yapilan)} düzeltme", flush=True)
        # inceleme kareleri ~4,5 GB tutuyor; render ise geçici kare için ~16 GB istiyor (11-20 disk dolup render düştü)
        shutil.rmtree(proje / ".hyperframes" / "artifacts" / "snapshots", ignore_errors=True)
    bag = _oku(d / "senaryo_kayit.json")["kaynak_bag"] if (d / "senaryo_kayit.json").exists() else {}
    _yaz(d / "meta.json", metadata(sen, plan, kay, bag))
    if not render_yap:
        return proje
    ham = d / "video_ham.mp4"
    if not ham.exists():
        kurgu.render(proje, ham)
    son = d / "video.mp4"
    if not son.exists():
        ses_seviyesi(ham, son)
    print("video:", son, flush=True)
    hikaye = secim["secim"]["hikaye"]
    if hikaye not in (g := gecmis()):  # editör aynı hikâyeyi yeniden seçmesin (secici.sec)
        _yaz(GECMIS, (g + [hikaye])[-60:])
    asama_kapak(d, sen, kay)
    asama_kesitler(d, sen, plan, varlik, kay)
    return son


def asama_kapak(d: Path, sen: dict, kay: dict) -> Path:
    from otomat.trend import kapak

    hedef = d / "kapak" / "kapak.jpg"
    if hedef.exists():
        return hedef
    from otomat.trend import kesik

    n = len(kay["gorseller"])

    def _gi(g: object) -> int:
        g = str(g or "G1")
        return min(max(int(g[1:]) - 1 if g[1:].isdigit() else 0, 0), n - 1)

    # kesitli kapak için aday: yazarın kapak görseli, sonra açılış sahnelerinin görselleri (konunun kendisi)
    acilis = [_gi(sh["gorsel"]) for sh in sen["sahneler"][:8] if sh.get("gorsel")]
    adaylar = list(dict.fromkeys([_gi(sen.get("kapak_gorsel")), *acilis]))[:5]
    secilen = adaylar[0]
    for gi in adaylar:
        if kesik.kes(Path(kay["gorseller"][gi]["yerel"]), d / "kesit" / f"g{gi + 1:02d}.png"):
            secilen = gi
            break
    g = kay["gorseller"][secilen]
    yol = kapak.uret(sen.get("kapak_metni") or "", Path(g["hazir"]), d / "kapak", ham=Path(g["yerel"]))
    print("kapak:", yol, flush=True)
    return yol


def asama_kesitler(d: Path, sen: dict, plan: dict, varlik: dict, kay: dict) -> list[Path]:
    """Senaryodaki kesitler: dikey yeniden kurulum, render, ses seviyesi. Kesit başına en çok ~58 sn."""
    from otomat.trend import derinlik, kesit

    out = []
    dikey = {}
    kullanilan = {sh["gorsel"].rsplit("/", 1)[-1] for sh in plan["sahneler"] if sh.get("gorsel")}
    for i, g in enumerate(kay["gorseller"]):
        ad = f"g{i + 1:02d}"
        if f"{ad}.jpg" not in kullanilan:
            continue
        hedef = medya.hazirla(Path(g["yerel"]), d / "gorsel_dikey" / f"{ad}.jpg", (1080, 1920))
        dikey[f"assets/dikey/{ad}.jpg"] = hedef
        if not medya.dolgulu(Path(g["yerel"]), (1080, 1920)):
            dikey[f"assets/dikey_derinlik/{ad}.png"] = derinlik.harita(hedef, d / "derinlik_dikey" / f"{ad}.png")
    for ki, k in enumerate(sen.get("kesitler") or []):
        idx = [int(x) for x in k.get("sahneler", []) if 0 <= int(x) < len(plan["sahneler"])]
        if not idx:
            continue
        idx = list(range(min(idx), max(idx) + 1))
        while len(idx) > 1 and (plan["sahneler"][idx[-1]]["bas"] + plan["sahneler"][idx[-1]]["sure"]
                                - plan["sahneler"][idx[0]]["bas"]) > 58:  # fmt: skip
            idx.pop()
        kd = d / f"kesit{ki + 1}"
        son = kd / "kesit.mp4"
        if son.exists():
            out.append(son)
            continue
        kesit.proje_yaz(plan, {**k, "sahneler": idx}, kd / "proje", varlik, dikey)
        _yaz(kd / "denetim.json", kurgu.denetle(kd / "proje"))
        ham = kd / "kesit_ham.mp4"
        if not ham.exists():
            kurgu.render(kd / "proje", ham)
        ses_seviyesi(ham, son)
        print(f"kesit {ki + 1}:", son, flush=True)
        out.append(son)
    return out


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--konu")
    a.add_argument("--id")
    a.add_argument("--render-yok", action="store_true")
    g = a.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    try:
        calistir(g.konu, g.id, not g.render_yok)
    finally:
        if n := kurgu.artiklari_kapat():
            print(f"asılı HyperFrames süreci kapatıldı: {n}", flush=True)


if __name__ == "__main__":
    main()
