"""Yer adlarının anlatıda, altyazıda ve grafikte görünen biçimi; üç kaynakta tek biçim.

World Bank resmî kısaltmalar kullanır ("Korea, Rep.", "Lao PDR"), TTS bunları bozuk okur ve cümle sonunda "Rep.." çıkar.
USGS yer metni adlandırılmış depremler ("2025 Hubbard Glacier Earthquake"), eyalet kısaltmaları ("CA") ve küçük harfle
başlayan yönler ("southern Mid-Atlantic Ridge") taşır. Aynı ülke kaynaklar arasında farklı yazılır
(Turkey/Turkiye/Türkiye).
"""

import re

ESANLAM = {
    # World Bank
    "Bahamas, The": "The Bahamas",
    "Gambia, The": "The Gambia",
    "Congo, Dem. Rep.": "DR Congo",
    "Congo, Rep.": "Republic of the Congo",
    "Egypt, Arab Rep.": "Egypt",
    "Hong Kong SAR, China": "Hong Kong",
    "Macao SAR, China": "Macao",
    "Iran, Islamic Rep.": "Iran",
    "Korea, Rep.": "South Korea",
    "Korea, Dem. People's Rep.": "North Korea",
    "Lao PDR": "Laos",
    "Micronesia, Fed. Sts.": "Micronesia",
    "Somalia, Fed. Rep.": "Somalia",
    "Venezuela, RB": "Venezuela",
    "Yemen, Rep.": "Yemen",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Slovak Republic": "Slovakia",
    "Russian Federation": "Russia",
    "Syrian Arab Republic": "Syria",
    "Brunei Darussalam": "Brunei",
    "Viet Nam": "Vietnam",
    "Naoero": "Nauru",
    "Turkiye": "Türkiye",
    "Virgin Islands (U.S.)": "U.S. Virgin Islands",
    # USGS
    "Turkey": "Türkiye",
    "Democratic Republic of the Congo": "DR Congo",
    "Federated States of Micronesia": "Micronesia",
    "Fiji Islands": "Fiji",
    "Timor Leste": "Timor-Leste",
    "Burma (Myanmar)": "Myanmar",
    "Mauritius - Reunion": "Mauritius and Reunion",
    "CA": "California",
    "MX": "Mexico",
}


def goster(ad: str) -> str:
    ad = ad.strip()
    if ad in ESANLAM:
        return ESANLAM[ad]
    ad = re.sub(r"^\d{4}\s+|\s+Earthquake$", "", ad)  # "2025 Hubbard Glacier Earthquake" → "Hubbard Glacier"
    ad = re.sub(r"^off the \w+ coast of (the )?", "", ad)  # "off the west coast of northern Sumatra"
    ad = re.sub(r"\s*\((?:US|U\.S\.|UK|Dutch part|French part)\)$", "", ad)  # "Puerto Rico (US)"
    ad = re.sub(r"^St\. ", "Saint ", ad)
    if m := re.fullmatch(r"(.+), The", ad):
        ad = f"The {m[1]}"
    ad = ESANLAM.get(ad, ad)
    return ad[:1].upper() + ad[1:]
