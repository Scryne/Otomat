"""Hikâye kanallarının (2026-10-08, Faz 15) kanal ayarları API ile: banner, filigran, açıklama (EN + ES/PT/DE/FR),
anahtar kelimeler, varsayılan dil, çocuk kanalında kanal düzeyinde "made for kids".

Kanal adı, tanıtıcı (@handle) ve profil resmi API ile değiştirilemez: Scryne Studio'dan yapar, ardından `kanal.toml`'daki
`ad` YouTube'daki adla aynı yapılır (youtube.kanal_dogrula). Bu betik adı değiştirilmiş kanalda çalışır.

    OTOMAT_KANAL=earth uv run python docs/marka/hikaye_kanallari.py
    OTOMAT_KANAL=uzay  uv run python docs/marka/hikaye_kanallari.py
"""

from pathlib import Path

from googleapiclient.http import MediaFileUpload

from otomat import kanal
from otomat.yayin import youtube

KOK = Path(__file__).parent
YEREL = {"es": "es_ES", "pt": "pt_BR", "de": "de_DE", "fr": "fr_FR"}  # önceki kanallardaki biçim

KANALLAR = {
    "earth": {
        "ad": "Inkwell Oddities",
        "dizin": KOK / "inkwell",
        "mfk": False,
        "anahtar": '"true stories" "weird history" "strange history" "history shorts" "unusual facts" '
        '"illustrated stories" storytime "bizarre history"',
        "aciklama": {
            "en": (
                "True stories so strange they sound made up. Every day, one real event, person or animal from history "
                "(a beer flood in London, a town that could not stop dancing, a cat that survived three shipwrecks) "
                "told in under a minute with storybook illustrations.\n\n"
                "Every story comes from Wikipedia's list of unusual articles and is checked line by line against the "
                "source, which is linked in each video. Illustrations are AI-generated; narration is computer-generated. "
                "New Short every day.\n"
            ),
            "es": (
                "Historias reales tan extrañas que parecen inventadas. Cada día, un hecho, una persona o un animal real "
                "de la historia (una inundación de cerveza en Londres, un pueblo que no podía dejar de bailar, un gato "
                "que sobrevivió a tres naufragios) contado en menos de un minuto con ilustraciones de cuento.\n\n"
                "Cada historia proviene de la lista de artículos inusuales de Wikipedia y se verifica línea por línea "
                "con la fuente, enlazada en cada video. Las ilustraciones están generadas con IA y la narración por "
                "computadora. Un Short nuevo cada día.\n"
            ),
            "pt": (
                "Histórias reais tão estranhas que parecem inventadas. Todos os dias, um fato, uma pessoa ou um animal "
                "real da história (uma enchente de cerveja em Londres, uma cidade que não conseguia parar de dançar, um "
                "gato que sobreviveu a três naufrágios) contado em menos de um minuto com ilustrações de livro de "
                "histórias.\n\n"
                "Cada história vem da lista de artigos incomuns da Wikipédia e é conferida linha por linha com a fonte, "
                "indicada em cada vídeo. As ilustrações são geradas por IA e a narração por computador. Um Short novo "
                "todos os dias.\n"
            ),
            "de": (
                "Wahre Geschichten, so seltsam, dass sie erfunden klingen. Jeden Tag ein echtes Ereignis, ein Mensch "
                "oder ein Tier aus der Geschichte (eine Bierflut in London, eine Stadt, die nicht aufhören konnte zu "
                "tanzen, eine Katze, die drei Schiffsuntergänge überlebte), in unter einer Minute erzählt, mit "
                "Bilderbuch-Illustrationen.\n\n"
                "Jede Geschichte stammt aus der Wikipedia-Liste ungewöhnlicher Artikel und wird Zeile für Zeile mit der "
                "Quelle abgeglichen, die in jedem Video verlinkt ist. Die Illustrationen sind KI-generiert, die "
                "Sprecherstimme computergeneriert. Jeden Tag ein neuer Short.\n"
            ),
            "fr": (
                "Des histoires vraies si étranges qu'elles semblent inventées. Chaque jour, un fait, une personne ou un "
                "animal réel de l'histoire (une inondation de bière à Londres, une ville qui ne pouvait plus s'arrêter "
                "de danser, un chat qui a survécu à trois naufrages) raconté en moins d'une minute avec des "
                "illustrations de livre de contes.\n\n"
                "Chaque histoire vient de la liste des articles insolites de Wikipédia et est vérifiée ligne par ligne "
                "avec la source, citée dans chaque vidéo. Les illustrations sont générées par IA et la narration par "
                "ordinateur. Un nouveau Short chaque jour.\n"
            ),
        },
    },
    "uzay": {
        "ad": "Lanternbug Tales",
        "dizin": KOK / "lanternbug",
        "mfk": True,
        "anahtar": '"kids stories" "bedtime stories" "fables for kids" "Aesop\'s fables" "moral stories" '
        '"animal stories" "stories for toddlers" storytime',
        "aciklama": {
            "en": (
                "Gentle animal fables for little ones, one every day. A classic Aesop fable (the Lion and the Mouse, "
                "the Fox and the Grapes, the North Wind and the Sun) retold in simple words with soft picture-book "
                "illustrations and a kind lesson at the end. For children aged 3 to 7.\n\n"
                "Stories are retold from Aesop's public-domain fables and checked to be gentle and child-friendly. "
                "Illustrations are AI-generated; narration is computer-generated.\n"
            ),
            "es": (
                "Fábulas de animales tranquilas para los más pequeños, una cada día. Una fábula clásica de Esopo (el "
                "león y el ratón, la zorra y las uvas, el viento del norte y el sol) contada con palabras sencillas, "
                "ilustraciones suaves de libro infantil y una enseñanza amable al final. Para niños de 3 a 7 años.\n\n"
                "Las historias se basan en las fábulas de Esopo, de dominio público, y se revisan para que sean suaves "
                "y aptas para niños. Las ilustraciones están generadas con IA y la narración por computadora.\n"
            ),
            "pt": (
                "Fábulas de animais tranquilas para os pequenos, uma por dia. Uma fábula clássica de Esopo (o leão e o "
                "rato, a raposa e as uvas, o vento norte e o sol) recontada com palavras simples, ilustrações suaves "
                "de livro infantil e uma lição gentil no final. Para crianças de 3 a 7 anos.\n\n"
                "As histórias são recontadas a partir das fábulas de Esopo, em domínio público, e revisadas para serem "
                "suaves e adequadas às crianças. As ilustrações são geradas por IA e a narração por computador.\n"
            ),
            "de": (
                "Sanfte Tierfabeln für die Kleinen, jeden Tag eine. Eine klassische Fabel von Äsop (der Löwe und die "
                "Maus, der Fuchs und die Trauben, der Nordwind und die Sonne), in einfachen Worten neu erzählt, mit "
                "weichen Bilderbuch-Illustrationen und einer freundlichen Lehre am Ende. Für Kinder von 3 bis 7 "
                "Jahren.\n\n"
                "Die Geschichten beruhen auf Äsops gemeinfreien Fabeln und werden darauf geprüft, dass sie sanft und "
                "kindgerecht sind. Die Illustrationen sind KI-generiert, die Sprecherstimme computergeneriert.\n"
            ),
            "fr": (
                "De douces fables d'animaux pour les petits, une chaque jour. Une fable classique d'Ésope (le lion et "
                "le rat, le renard et les raisins, le vent du nord et le soleil) racontée avec des mots simples, de "
                "douces illustrations d'album et une gentille leçon à la fin. Pour les enfants de 3 à 7 ans.\n\n"
                "Les histoires reprennent les fables d'Ésope, du domaine public, et sont vérifiées pour rester douces "
                "et adaptées aux enfants. Les illustrations sont générées par IA et la narration par ordinateur.\n"
            ),
        },
    },
}


def main() -> None:
    k = kanal.aktif()
    ayar = KANALLAR[k.id]
    assert k.ad == ayar["ad"], f"önce kanalı Studio'da '{ayar['ad']}' yap ve kanal.toml'daki ad'ı güncelle"
    yt = youtube.servis()  # kanal_dogrula: token bu kanala ait değilse burada durur
    c = yt.channels().list(part="id,brandingSettings,localizations,status", mine=True).execute()["items"][0]
    banner = yt.channelBanners().insert(
        media_body=MediaFileUpload(str(ayar["dizin"] / "banner-2560x1440.png"), mimetype="image/png")
    ).execute()
    marka = c["brandingSettings"]
    marka.setdefault("channel", {}).update(
        {"description": ayar["aciklama"]["en"], "keywords": ayar["anahtar"], "defaultLanguage": "en"}
    )
    marka.setdefault("image", {})["bannerExternalUrl"] = banner["url"]
    yt.channels().update(part="brandingSettings", body={"id": c["id"], "brandingSettings": marka}).execute()
    yerel = {"en_US": {"title": ayar["ad"], "description": ayar["aciklama"]["en"]}}
    yerel |= {YEREL[d]: {"title": ayar["ad"], "description": ayar["aciklama"][d]} for d in YEREL}
    yt.channels().update(part="localizations", body={"id": c["id"], "localizations": yerel}).execute()
    yt.channels().update(
        part="status", body={"id": c["id"], "status": {"selfDeclaredMadeForKids": ayar["mfk"]}}
    ).execute()
    filigran = ayar["dizin"] / "filigran-150.png"
    try:
        yt.watermarks().set(
            channelId=c["id"],
            body={"timing": {"type": "offsetFromStart", "offsetMs": 0}, "position": {"type": "corner",
                  "cornerPosition": "topRight"}},  # fmt: skip
            media_body=MediaFileUpload(str(filigran), mimetype="image/png"),
        ).execute()
    except Exception as e:  # noqa: BLE001 — 10-06'da yanıt kütüphane hatasıyla okunamadı ama ayar uygulanmıştı
        print("filigran: yanıt okunamadı, Studio'da kontrol et:", type(e).__name__)
    son = yt.channels().list(part="snippet,brandingSettings,localizations,status", mine=True).execute()["items"][0]
    print("ad:", son["snippet"]["title"])
    print("açıklama:", son["brandingSettings"]["channel"]["description"][:70], "…")
    print("anahtar:", son["brandingSettings"]["channel"].get("keywords"))
    print("diller:", sorted(son.get("localizations", {})))
    print("banner:", "var" if son["brandingSettings"].get("image", {}).get("bannerExternalUrl") else "yok")
    print("mfk:", son["status"].get("selfDeclaredMadeForKids"), "/", son["status"].get("madeForKids"))


if __name__ == "__main__":
    main()
