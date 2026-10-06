"""Olgu paketinden görsel şablona köprü. Sıralama paketleri hem çubuk hem koroplet olarak çizilebilir."""

from pathlib import Path

from otomat.gorsel import koroplet, nokta_harita, olcek, sirali_cubuk, yakin_gecis
from otomat.veri import OlguPaketi

KAPSAM_HARITA = {"the world": "dunya", "Europe": "avrupa"}


def secenekler(paket: OlguPaketi) -> list[str]:
    g = paket.gorsel
    sonuc = [g["sablon"]]
    if "koroplet" in g and g.get("kapsam") in KAPSAM_HARITA:
        sonuc.append("koroplet")
    return sonuc


def _gezegen_karti(paket: OlguPaketi) -> list[tuple[str, str]]:
    """Ölçek şablonunun gezegen kartı: olgulardan, birimleriyle (sayılar yalnız paketten)."""
    from otomat.anlati.kapilar import deger_yazisi

    o = paket.olgular
    satirlar = [("distance", "distance_ly"), ("one year", "year_days"), ("temperature", "temperature_c"),
                ("width", "radius_earths")]  # fmt: skip

    def yaz(k: str) -> str:  # deger_yazisi "days" birimini yazmaz (Earth anlatısı); kartta birim şart
        return deger_yazisi(o[k].deger, o[k].birim) + (" days" if o[k].birim == "days" else "")

    return [(etiket, yaz(k)) for etiket, k in satirlar if k in o]


def ciz(
    paket: OlguPaketi,
    cikti: Path,
    baslik: str,
    kanca: str | None = None,
    sablon: str | None = None,
    saniye: float = 30,
    **kw,
) -> Path:
    g = paket.gorsel
    sablon = sablon or g["sablon"]
    if sablon not in secenekler(paket):
        raise ValueError(f"{paket.anahtar} '{sablon}' ile çizilemez")
    kaynak = paket.kaynak.ad
    if sablon == "yakin_gecis":
        return yakin_gecis.ciz(g["gecisler"], baslik, kaynak, cikti, kanca=kanca, vurgu=g.get("vurgu", 0),
                               saniye=saniye, **kw)  # fmt: skip
    if sablon == "olcek":
        return olcek.ciz(g, baslik, kaynak, cikti, kanca=kanca, kart=_gezegen_karti(paket), saniye=saniye, **kw)
    if sablon == "nokta_harita":
        return nokta_harita.ciz(
            g["olaylar"],
            baslik,
            kaynak,
            cikti,
            kutu=g.get("kutu"),
            kanca=kanca,
            bolge_adi=paket.olgular["region"].deger if "region" in paket.olgular and g.get("kutu") else None,
            saniye=saniye,
            **kw,
        )
    ortanca = paket.olgular.get("median_value")
    if sablon == "sirali_cubuk":
        return sirali_cubuk.ciz(
            g["ogeler"],
            baslik,
            kaynak,
            cikti,
            birim=g.get("birim", ""),
            ortanca=ortanca.deger if ortanca else None,
            ondalik=g.get("ondalik"),
            kanca=kanca,
            degisim=paket.tur == "en_cok_artan_10",
            saniye=saniye,
            **kw,
        )
    return koroplet.ciz(
        g["koroplet"],
        baslik,
        kaynak,
        cikti,
        kapsam=KAPSAM_HARITA[g["kapsam"]],
        birim=g.get("birim", ""),
        ondalik=g.get("ondalik"),
        kanca=kanca,
        saniye=saniye,
        **kw,
    )
