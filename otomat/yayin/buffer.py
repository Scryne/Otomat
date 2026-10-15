"""Buffer üzerinden yükleme: audit beklemeden public yayın yolu (docs/arastirma/06).

Kilit yalnız bizim doğrulanmamış Google projemizin videos.insert'ünde. Buffer'ın denetimden geçmiş YouTube bağlantısı
videoyu private yükler; planlı yayın, etiket, yerelleştirme ve altyazı sonra kendi API'mizle (youtube.duzenle).
Buffer dosya kabul etmez, herkese açık kalıcı bir URL ister: video, gönderim süresince public site reposunda
(otomat-site, GitHub Pages) durur, Buffer aldıktan sonra silinir.

Ortam:
- BUFFER_API_KEY: Actions secret; yerelde `.env` satırı.
- OTOMAT_SITE_ANAHTAR: otomat-site deploy key'inin özel anahtarı (Actions). Yoksa yerel git kimliği (https).
"""

import http.client
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from otomat import kanal
from otomat.ayarlar import KOK

API = "https://api.buffer.com"
SITE_REPO = "Scryne/otomat-site"
SITE_URL = "https://scryne.github.io/otomat-site"
SITE_GIT = ""  # boşsa GitHub (testte yerel çıplak repo)
KANAL = kanal.aktif().ad
YOKLAMA_SN = 45  # ücretsiz API 30 günde 3.000 istek (anahtar başına, tüm kanallar): gönderi başı en çok ~20 yoklama
YOKLAMA_HATA = 3  # gönderi durumu üst üste bu kadar okunamazsa sonuç belirsiz sayılır
# public repo: kişisel e-posta girmez (gunluk.yml'deki bot kimliği)
KIMLIK = ["-c", "user.name=otomat-bot", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"]
DENEME = 4
ISTEK = {"sayi": 0}  # bu süreçte Buffer'a giden istek (günlük rapor; 30 günde 3.000 sınırının takibi)


class BufferHatasi(RuntimeError):
    pass


class GonderiBelirsiz(BufferHatasi):
    """Gönderi açıldı (ya da açılıp açılmadığı bilinmiyor) ama sonucu okunamadı: Buffer videoyu yine de yükleyebilir.
    Hikâye harcanmış sayılır; aynı video sonraki koşuda yeniden gönderilirse kanalda iki kopyası olurdu."""


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
        ISTEK["sayi"] += 1
        try:
            with urllib.request.urlopen(istek, timeout=120) as y:
                yanit = json.load(y)
            if not isinstance(yanit, dict):
                raise ValueError(f"beklenmeyen yanıt: {str(yanit)[:100]}")
            break
        # okurken kopan bağlantı (RemoteDisconnected, IncompleteRead) ve yarım JSON da ağ hatasıdır: eskiden
        # BufferHatasi'na çevrilmeden kaçıyor, gönderiden sonra "gönderi açılmadı" sanılıp video ikinci kez gidiyordu
        except (OSError, http.client.HTTPException, ValueError) as e:
            gecici = not isinstance(e, urllib.error.HTTPError) or e.code == 429 or e.code >= 500
            if not tekrar or not gecici or i == DENEME - 1:
                raise BufferHatasi(f"Buffer API: {type(e).__name__}: {e}") from e
            time.sleep(5 * 2**i)
    if yanit.get("errors"):
        raise BufferHatasi(f"Buffer API: {yanit['errors']}"[:500])
    if not isinstance(yanit.get("data"), dict):
        raise BufferHatasi(f"Buffer API: veri yok: {str(yanit)[:200]}")
    return yanit["data"]


def kanal_id() -> str:
    if kid := kanal.aktif().buffer_kanal_id:  # profildeyse iki sorgu tasarrufu
        return kid
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
        "text": aciklama.replace("<", "‹").replace(">", "›"),  # YouTube < > reddeder (youtube.temiz)
        "assets": [{"video": {"url": video_url}}],
        "metadata": {
            "youtube": {
                "title": baslik.replace("<", "‹").replace(">", "›")[:100],
                "privacy": "private",
                "categoryId": kanal.aktif().kategori,
                # kanalın MFK ayarı (K-24'ten beri iki kanal da genel kitle): yükleme anından itibaren doğru kitle
                "madeForKids": kanal.aktif().mfk,
                "isAiGenerated": False,  # youtube.py: containsSyntheticMedia False (gerçekçi değil)
                "notifySubscribers": True,
            }
        },
    }
    try:
        sonuc = sorgu(GONDER, {"i": girdi}, tekrar=False)["createPost"]
    except BufferHatasi as e:
        neden = e.__cause__
        if isinstance(neden, urllib.error.HTTPError) and neden.code < 500 or neden is None:
            raise  # Buffer isteği reddetti (4xx ya da GraphQL hatası): gönderi açılmadı
        raise GonderiBelirsiz(f"createPost yanıtı alınamadı (gönderi açılmış olabilir): {e}") from e
    if not isinstance(sonuc, dict):
        raise GonderiBelirsiz(f"createPost yanıtı okunamadı (gönderi açılmış olabilir): {sonuc!r}"[:300])
    if "post" not in sonuc:
        raise BufferHatasi(f"createPost: {sonuc.get('message')}")
    try:
        post_id = sonuc["post"]["id"]
    except (KeyError, TypeError) as e:
        raise GonderiBelirsiz(f"createPost gönderi kimliği okunamadı: {sonuc!r}"[:300]) from e
    son = time.monotonic() + bekle_sn
    okunamayan = 0
    while True:
        # gönderi açıldı: bundan sonra her hata (ağ, bozuk yanıt, `post: null`) belirsizdir, kesin red değil. Tek bir
        # GraphQL hıçkırığı (HTTP 200 + errors) iyi giden gönderiyi "belirsiz" yapıp hikâyeyi harcıyor, planlamayı da
        # sonraki koşuya (çoğu zaman slottan sonraya) bırakıyordu: üst üste YOKLAMA_HATA okuma hatası gerekir
        try:
            p = sorgu(DURUM, {"p": post_id})["post"]
            durum_ = p["status"]
        except Exception as e:  # noqa: BLE001
            okunamayan += 1
            if okunamayan >= YOKLAMA_HATA or time.monotonic() > son:
                raise GonderiBelirsiz(f"gönderi {post_id} durumu okunamadı: {type(e).__name__}: {e}") from e
            time.sleep(YOKLAMA_SN)
            continue
        okunamayan = 0
        if durum_ == "sent" and p.get("externalLink"):
            if m := re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", p["externalLink"]):
                return m[1]
            raise GonderiBelirsiz(f"gönderi {post_id} gitti ama video id okunamadı: {p['externalLink']}")
        if durum_ == "error":
            raise BufferHatasi(f"Buffer yayını düştü: {(p.get('error') or {}).get('message')}")
        if time.monotonic() > son:
            raise GonderiBelirsiz(f"Buffer gönderisi {post_id} {bekle_sn} sn'de gitmedi (durum: {durum_})")
        time.sleep(YOKLAMA_SN)


def _git(*arg: str, cwd: Path | None = None, env: dict | None = None) -> None:
    try:
        subprocess.run(["git", *KIMLIK, *arg], cwd=cwd, env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:  # capture_output yüzünden hata yalnız "exit status 1" görünüyordu
        raise BufferHatasi(f"git {arg[0]}: {(e.stderr or e.stdout or '').strip()[-300:]}") from e


PUSH_DENEME = 4


def _site(islem, sikistir: bool = False) -> None:
    """otomat-site'ın sığ kopyasında işlem(kopya) yapar, değişikliği commit'leyip push'lar. `sikistir`: medya klasörü
    boşaldıysa dal tek commit'e indirilir (bkz. medya_kaldir)."""
    with tempfile.TemporaryDirectory() as gecici:
        env = dict(os.environ)
        uzak = SITE_GIT or f"https://github.com/{SITE_REPO}.git"
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
        if sikistir and not any((kopya / "media").glob("*")) and _sikistir(kopya, mesaj, env):
            return
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=kopya).returncode:
            _git("commit", "-m", mesaj, cwd=kopya, env=env)
            # iki kanal işi aynı anda aynı repoya yazıyor: ikinci push non-fast-forward'la reddediliyordu (Plan B'ye
            # düşüyordu); dosyalar kanal önekli olduğu için rebase çakışmaz
            for i in range(PUSH_DENEME):
                try:
                    _git("push", cwd=kopya, env=env)
                    break
                except BufferHatasi:
                    if i == PUSH_DENEME - 1:
                        raise
                    _git("pull", "--rebase", cwd=kopya, env=env)
                    time.sleep(3 * (i + 1))


def _sikistir(kopya: Path, mesaj: str, env: dict) -> bool:
    """Dalı tek commit'e indirip zorla push'lar: silinen her video public repo tarihçesinde kalıyordu (10 günde 294 MB,
    Pages repo sınırı 1 GB; geri çekilen videolar da tarihçeden açılabiliyordu). Kira (`--force-with-lease`) klonlanan
    uca bağlı: arada öbür kanal medya koyduysa push reddedilir, olağan silme commit'ine dönülür (False)."""
    uc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kopya, capture_output=True, text=True, check=True).stdout
    try:
        _git("checkout", "--orphan", "sikistirilmis", cwd=kopya, env=env)
        _git("commit", "-m", f"{mesaj} (medya tarihçesi sıkıştırıldı)", cwd=kopya, env=env)
        _git("push", f"--force-with-lease=main:{uc.strip()}", "origin", "sikistirilmis:main", cwd=kopya, env=env)
    except BufferHatasi:
        _git("checkout", "main", cwd=kopya, env=env)
        return False
    return True


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
        except (OSError, http.client.HTTPException, ValueError):  # kopan bağlantı da "henüz yok" demek
            pass
        if time.monotonic() > son:
            raise BufferHatasi(f"Pages {bekle_sn} sn'de yayınlamadı: {url}")
        time.sleep(15)


def medya_kaldir(ad: str) -> None:
    """Buffer videoyu aldıktan sonra: site reposu her gün büyümesin. Medya klasörü boşaldıysa tarihçe sıkıştırılır."""

    def kaldir(kopya: Path) -> str:
        (kopya / "media" / ad).unlink(missing_ok=True)
        return f"Medya kaldırıldı: {ad}"

    _site(kaldir, sikistir=True)
