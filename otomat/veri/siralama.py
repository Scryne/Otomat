"""Ülke → değer tablosundan sıralama paketleri (World Bank ve Eurostat ortak kullanır)."""

from statistics import median

from otomat.veri import Kaynak, Olgu, OlguPaketi


def _yuvarla(x: float, ondalik: int) -> int | float:
    return int(round(x)) if ondalik == 0 else round(x, ondalik)


def ayrisan_ondalik(degerler: list[float], ondalik: int, en_fazla: int = 2) -> int | None:
    """Değerlerin gösterimde birbirinden ayrıştığı en az ondalık: `ondalik` ya da bir fazlası (`en_fazla`yı aşmadan).

    Eşit görünen değerlerde "X birinci" iddiası yanlıştır: onlarca ülke %100'deyken alfabede önce gelen "en yüksek"
    olur. Ayrışmıyorsa None.
    """
    for o in range(ondalik, max(ondalik, min(ondalik + 1, en_fazla)) + 1):
        yuvarlanmis = [_yuvarla(d, o) for d in degerler]
        if len(set(yuvarlanmis)) == len(yuvarlanmis):
            return o
    return None


def siralama_paketleri(
    kol: str,
    kod: str,
    ad: str,
    birim: str,
    ondalik: int,
    yil: int,
    degerler: dict[str, float],  # ISO3 -> değer
    isimler: dict[str, str],  # ISO3 -> ülke adı
    kaynak: Kaynak,
    kapsam: str,  # "the world" | "Europe"
    eski: dict[str, float] | None = None,
    eski_yil: int | None = None,
) -> list[OlguPaketi]:
    if len(degerler) < 15:
        return []
    sonuc = []
    koroplet = {k: _yuvarla(v, ondalik) for k, v in degerler.items()}
    ortanca = _yuvarla(median(degerler.values()), ondalik)
    for tur, ters in (("en_yuksek_10", True), ("en_dusuk_10", False)):
        sirali = sorted(degerler.items(), key=lambda x: x[1], reverse=ters)[:10]
        yon = "highest" if ters else "lowest"
        hassas = ayrisan_ondalik([d for _, d in sirali[:4]], ondalik)  # 4.: "üçüncü" de tek olmalı
        if hassas is None:
            continue
        olgular = {
            "indicator": Olgu(ad, "what is being compared"),
            "year": Olgu(yil, "year of the data"),
            "countries_compared": Olgu(len(degerler), f"number of countries compared in {kapsam}"),
            "median_value": Olgu(ortanca, f"median {ad} across the countries compared", birim),
            "scope": Olgu(kapsam, "geographic scope of the comparison"),
        }
        for i, (iso, deger) in enumerate(sirali[:3], 1):
            olgular[f"rank{i}_country"] = Olgu(isimler.get(iso, iso), f"country with the number {i} {yon} {ad}")
            olgular[f"rank{i}_value"] = Olgu(_yuvarla(deger, hassas), f"{ad} of rank{i}_country", birim)
        sonuc.append(
            OlguPaketi(
                kol=kol,
                tur=tur,
                anahtar=f"{kol}:{tur}:{kod}:{yil}",
                konu=f"countries in {kapsam} with the {yon} {ad}",
                olgular=olgular,
                gorsel={
                    "sablon": "sirali_cubuk",
                    "ogeler": [
                        {"etiket": isimler.get(i, i), "deger": _yuvarla(v, hassas), "iso3": i} for i, v in sirali
                    ],
                    "birim": birim,
                    "ondalik": hassas,
                    "koroplet": koroplet,
                    "kapsam": kapsam,
                },
                kaynak=kaynak,
                etiketler=["rankings", "world" if kapsam == "the world" else kapsam],
            )
        )

    if eski and eski_yil:
        degisim = {k: degerler[k] - eski[k] for k in degerler.keys() & eski.keys()}
        # yalnız gerçekten (yuvarlanmış değerde de) artanlar: hepsi düştüyse "en az düşen" artış diye anlatılmasın
        sirali = [
            (iso, d)
            for iso, d in sorted(degisim.items(), key=lambda x: x[1], reverse=True)
            if _yuvarla(degerler[iso], ondalik) > _yuvarla(eski[iso], ondalik)
        ][:10]
        if len(degisim) >= 15 and len(sirali) >= 3:
            olgular = {
                "indicator": Olgu(ad, "what is being compared"),
                "from_year": Olgu(eski_yil, "start year"),
                "to_year": Olgu(yil, "end year"),
                "scope": Olgu(kapsam, "geographic scope of the comparison"),
            }
            for i, (iso, _) in enumerate(sirali[:3], 1):
                ulke = isimler.get(iso, iso)
                olgular[f"rank{i}_country"] = Olgu(ulke, f"country with the number {i} biggest rise in {ad}")
                olgular[f"rank{i}_from"] = Olgu(
                    _yuvarla(eski[iso], ondalik), f"{ad} of rank{i}_country in from_year", birim
                )
                olgular[f"rank{i}_to"] = Olgu(
                    _yuvarla(degerler[iso], ondalik), f"{ad} of rank{i}_country in to_year", birim
                )
            sonuc.append(
                OlguPaketi(
                    kol=kol,
                    tur="en_cok_artan_10",
                    anahtar=f"{kol}:en_cok_artan_10:{kod}:{eski_yil}-{yil}",
                    konu=f"countries in {kapsam} where {ad} rose the most since {eski_yil}",
                    olgular=olgular,
                    gorsel={
                        "sablon": "sirali_cubuk",
                        "ogeler": [
                            {
                                "etiket": isimler.get(i, i),
                                "deger": _yuvarla(degerler[i], ondalik),
                                "onceki": _yuvarla(eski[i], ondalik),
                                "iso3": i,
                            }
                            for i, _ in sirali
                        ],
                        "birim": birim,
                        "ondalik": ondalik,
                        "kapsam": kapsam,
                    },
                    kaynak=kaynak,
                    etiketler=["trends", "world" if kapsam == "the world" else kapsam],
                )
            )
    return sonuc


def referans_yili(yil_ulke: dict[int, dict[str, float]], oran: float = 0.8) -> int | None:
    """Kapsamı en geniş yılın %80'ine ulaşan en yeni yıl (yeni yıllar genelde eksik dolu)."""
    if not yil_ulke:
        return None
    en_genis = max(len(v) for v in yil_ulke.values())
    for yil in sorted(yil_ulke, reverse=True):
        if len(yil_ulke[yil]) >= oran * en_genis:
            return yil
    return None
