"""Orbit Ruler kanal ayarları API ile: banner, açıklama (EN + ES/PT/DE/FR), anahtar kelimeler, varsayılan dil.

Profil resmi API ile değiştirilemez (Studio'dan). Earth'teki yapıyla aynı alanlar (Scryne'ın 10-06 elle kurulumu).
Kullanım: OTOMAT_KANAL=uzay uv run python docs/marka/uzay/master/kanal_ayarla.py
"""

from pathlib import Path

from googleapiclient.http import MediaFileUpload

from otomat import kanal
from otomat.yayin import youtube

BANNER = Path(__file__).parents[1] / "youtube" / "banner-2560x1440.png"

ACIKLAMA = {
    "en": (
        "Orbit Ruler shows space by scale: the asteroids that pass Earth, drawn at their real distance against the "
        "Moon's orbit, and planets around other stars, set next to Earth and Jupiter.\n\n"
        "Data comes from NASA/JPL close-approach data and the NASA Exoplanet Archive, cited in every video. Asteroid "
        "sizes are estimated from brightness and always shown as a range. Narration is computer-generated. "
        "New Short every day.\n"
    ),
    "es": (
        "Orbit Ruler muestra el espacio a escala: los asteroides que pasan cerca de la Tierra, dibujados a su "
        "distancia real frente a la órbita de la Luna, y planetas de otras estrellas junto a la Tierra y Júpiter.\n\n"
        "Los datos provienen de NASA/JPL y del NASA Exoplanet Archive, citados en cada video. El tamaño de los "
        "asteroides se estima por su brillo y siempre se muestra como un rango. La narración es generada por "
        "computadora. Un Short nuevo cada día.\n"
    ),
    "pt": (
        "Orbit Ruler mostra o espaço em escala: os asteroides que passam perto da Terra, desenhados na distância real "
        "em relação à órbita da Lua, e planetas de outras estrelas ao lado da Terra e de Júpiter.\n\n"
        "Os dados vêm da NASA/JPL e do NASA Exoplanet Archive, citados em cada vídeo. O tamanho dos asteroides é "
        "estimado pelo brilho e sempre mostrado como um intervalo. A narração é gerada por computador. "
        "Um Short novo todos os dias.\n"
    ),
    "de": (
        "Orbit Ruler zeigt den Weltraum im Maßstab: Asteroiden, die an der Erde vorbeiziehen, in ihrer echten "
        "Entfernung zur Mondbahn, und Planeten anderer Sterne neben Erde und Jupiter.\n\n"
        "Die Daten stammen von NASA/JPL und dem NASA Exoplanet Archive und werden in jedem Video genannt. "
        "Asteroidengrößen werden aus der Helligkeit geschätzt und immer als Spanne gezeigt. Die Sprecherstimme ist "
        "computergeneriert. Jeden Tag ein neuer Short.\n"
    ),
    "fr": (
        "Orbit Ruler montre l'espace à l'échelle : les astéroïdes qui frôlent la Terre, dessinés à leur vraie "
        "distance par rapport à l'orbite de la Lune, et des planètes d'autres étoiles à côté de la Terre et de "
        "Jupiter.\n\n"
        "Les données viennent de la NASA/JPL et du NASA Exoplanet Archive, citées dans chaque vidéo. La taille des "
        "astéroïdes est estimée d'après leur luminosité et toujours donnée sous forme de fourchette. La narration est "
        "générée par ordinateur. Un nouveau Short chaque jour.\n"
    ),
}
YEREL = {"es": "es_ES", "pt": "pt_BR", "de": "de_DE", "fr": "fr_FR"}  # Earth'teki biçim
ANAHTAR = '"space by scale" asteroids "near earth objects" exoplanets astronomy "nasa data" "solar system" planets'


def main() -> None:
    assert kanal.aktif().id == "uzay", "OTOMAT_KANAL=uzay ile çalıştır"
    yt = youtube.servis()  # kanal_dogrula: token Orbit Ruler'a ait değilse burada durur
    k = yt.channels().list(part="id,brandingSettings,localizations", mine=True).execute()["items"][0]
    yanit = yt.channelBanners().insert(media_body=MediaFileUpload(str(BANNER), mimetype="image/png")).execute()
    marka = k["brandingSettings"]
    marka.setdefault("channel", {}).update(
        {"description": ACIKLAMA["en"], "keywords": ANAHTAR, "defaultLanguage": "en"}
    )
    marka.setdefault("image", {})["bannerExternalUrl"] = yanit["url"]
    yt.channels().update(part="brandingSettings", body={"id": k["id"], "brandingSettings": marka}).execute()
    yerel = {"en_US": {"title": "Orbit Ruler", "description": ACIKLAMA["en"]}}
    yerel |= {YEREL[d]: {"title": "Orbit Ruler", "description": ACIKLAMA[d]} for d in YEREL}
    yt.channels().update(part="localizations", body={"id": k["id"], "localizations": yerel}).execute()
    son = yt.channels().list(part="brandingSettings,localizations", mine=True).execute()["items"][0]
    print("açıklama:", son["brandingSettings"]["channel"]["description"][:60], "…")
    print("anahtar:", son["brandingSettings"]["channel"].get("keywords"))
    print("diller:", sorted(son.get("localizations", {})))
    print("banner:", "var" if son["brandingSettings"].get("image", {}).get("bannerExternalUrl") else "yok")


if __name__ == "__main__":
    main()
