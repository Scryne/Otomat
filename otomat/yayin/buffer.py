"""Buffer üzerinden yükleme: audit beklemeden public yayın yolu (docs/arastirma/06).

Kilit yalnız bizim doğrulanmamış Google projemizin videos.insert'ünde. Buffer'ın denetimden geçmiş YouTube bağlantısı
videoyu private yükler; planlı yayın, etiket, yerelleştirme ve altyazı sonra kendi API'mizle (youtube.duzenle).
Buffer dosya kabul etmez, herkese açık kalıcı bir URL ister: video, gönderim süresince public site reposunda
(otomat-site, GitHub Pages) durur, Buffer aldıktan sonra silinir.

Ortam:
- BUFFER_API_KEY: Actions secret; yerelde `.env` satırı.
- OTOMAT_SITE_ANAHTAR: otomat-site deploy key'inin özel anahtarı (Actions). Yoksa yerel git kimliği (https).
"""

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from otomat.ayarlar import KOK

API = "https://api.buffer.com"
SITE_REPO = "Scryne/otomat-site"
SITE_URL = "https://scryne.github.io/otomat-site"
KANAL = "Earth in Numbers"
# public repo: kişisel e-posta girmez (gunluk.yml'deki bot kimliği)
KIMLIK = ["-c", "user.name=otomat-bot", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"]
DENEME = 4


class BufferHatasi(RuntimeError):
    pass


def anahtar() -> str:
    if k := os.environ.get("BUFFER_API_KEY"):
        return k
    env = KOK / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8").splitlines():
            if satir.startswith("BUFFER_API_KEY="):
                return satir.split("=", 1)[1].strip()
    raise BufferHatasi("BUFFER_API_KEY yok (Actions secret ya da yerel .env)")


def sorgu(metin: str, degiskenler: dict | None = None, tekrar: bool = True) -> dict:
    """GraphQL çağrısı. Okumalar 5xx/429/bağlantı hatasında yeniden denenir; mutasyon (tekrar=False) çift gönderi
    açmasın diye denenmez."""
    istek = urllib.request.Request(
        API,
        data=json.dumps({"query": metin, "variables": degiskenler or {}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {anahtar()}", "User-Agent": "otomat"},
    )
    for i in range(DENEME if tekrar else 1):
        try:
            with urllib.request.urlopen(istek, timeout=120) as y:
                yanit = json.load(y)
            break
        except (urllib.error.URLError, TimeoutError) as e:
            gecici = not isinstance(e, urllib.error.HTTPError) or e.code == 429 or e.code >= 500
            if not tekrar or not gecici or i == DENEME - 1:
                raise BufferHatasi(f"Buffer API: {e}") from e
            time.sleep(5 * 2**i)
    if yanit.get("errors"):
        raise BufferHatasi(f"Buffer API: {yanit['errors']}"[:500])
    return yanit["data"]


def kanal_id() -> str:
    orglar = sorgu("query { account { organizations { id } } }")["account"]["organizations"]
    for org in orglar:
        q = "query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id name service } }"
        for k in sorgu(q, {"o": org["id"]})["channels"]:
            if k["service"] == "youtube" and k["name"] == KANAL:
                return k["id"]
    raise BufferHatasi(f"Buffer'da '{KANAL}' YouTube kanalı bağlı değil")


GONDER = """mutation($i: CreatePostInput!) { createPost(input: $i) {
  ... on PostActionSuccess { post { id } } ... on MutationError { message } } }"""
DURUM = "query($p: PostId!) { post(input: {id: $p}) { status externalLink error { message } } }"


def gonder(video_url: str, baslik: str, aciklama: str, bekle_sn: int = 900) -> str:
    """Videoyu Buffer'dan private yükletir, YouTube video id'sini döner. Planlama sonra youtube.duzenle ile."""
    girdi = {
        "channelId": kanal_id(),
        "schedulingType": "automatic",
        "mode": "shareNow",
        "needsApproval": False,
        "text": aciklama,
        "assets": [{"video": {"url": video_url}}],
        "metadata": {
            "youtube": {
                "title": baslik[:100],
                "privacy": "private",
                "categoryId": "28",
                "madeForKids": False,
                "isAiGenerated": False,  # youtube.py: containsSyntheticMedia False (gerçekçi değil)
                "notifySubscribers": True,
            }
        },
    }
    sonuc = sorgu(GONDER, {"i": girdi}, tekrar=False)["createPost"]
    if "post" not in sonuc:
        raise BufferHatasi(f"createPost: {sonuc.get('message')}")
    post_id = sonuc["post"]["id"]
    son = time.monotonic() + bekle_sn
    while True:
        p = sorgu(DURUM, {"p": post_id})["post"]
        if p["status"] == "sent" and p.get("externalLink"):
            if m := re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", p["externalLink"]):
                return m[1]
            raise BufferHatasi(f"video id okunamadı: {p['externalLink']}")
        if p["status"] == "error":
            raise BufferHatasi(f"Buffer yayını düştü: {(p.get('error') or {}).get('message')}")
        if time.monotonic() > son:
            raise BufferHatasi(f"Buffer gönderisi {bekle_sn} sn'de gitmedi (durum: {p['status']})")
        time.sleep(15)


def _git(*arg: str, cwd: Path | None = None, env: dict | None = None) -> None:
    subprocess.run(["git", *KIMLIK, *arg], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def _site(islem) -> None:
    """otomat-site'ın sığ kopyasında işlem(kopya) yapar, değişikliği commit'leyip push'lar."""
    with tempfile.TemporaryDirectory() as gecici:
        env = dict(os.environ)
        uzak = f"https://github.com/{SITE_REPO}.git"
        if ozel := os.environ.get("OTOMAT_SITE_ANAHTAR"):
            dosya = Path(gecici) / "anahtar"
            dosya.write_text(ozel.strip() + "\n", encoding="utf-8")
            dosya.chmod(0o600)
            env["GIT_SSH_COMMAND"] = f"ssh -i {dosya} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            uzak = f"git@github.com:{SITE_REPO}.git"
        kopya = Path(gecici) / "site"
        _git("clone", "--depth", "1", uzak, str(kopya), env=env)
        mesaj = islem(kopya)
        _git("add", "-A", cwd=kopya, env=env)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=kopya).returncode:
            _git("commit", "-m", mesaj, cwd=kopya, env=env)
            _git("push", cwd=kopya, env=env)


def medya_koy(video: Path, ad: str, bekle_sn: int = 600) -> str:
    """Videoyu site reposuna koyar, Pages yayınlayana kadar bekler, herkese açık URL'yi döner."""

    def koy(kopya: Path) -> str:
        (kopya / "media").mkdir(exist_ok=True)
        (kopya / "media" / ad).write_bytes(video.read_bytes())
        return f"Medya: {ad}"

    _site(koy)
    url = f"{SITE_URL}/media/{ad}"
    boyut = video.stat().st_size
    son = time.monotonic() + bekle_sn
    while True:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as y:
                if int(y.headers.get("Content-Length", -1)) == boyut:
                    return url
        except (urllib.error.URLError, TimeoutError):
            pass
        if time.monotonic() > son:
            raise BufferHatasi(f"Pages {bekle_sn} sn'de yayınlamadı: {url}")
        time.sleep(15)


def medya_kaldir(ad: str) -> None:
    """Buffer videoyu aldıktan sonra: site reposu her gün büyümesin."""

    def kaldir(kopya: Path) -> str:
        (kopya / "media" / ad).unlink(missing_ok=True)
        return f"Medya kaldırıldı: {ad}"

    _site(kaldir)
