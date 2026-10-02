---
proje: Otomat
created: 2026-10-02
type: rehber
---
# YouTube API Services — Audit and Quota Extension Form: hazır metin

Form: https://support.google.com/youtube/contact/yt_api_form. Köşeli parantezli yerleri D1/D2'den sonra doldururum.
Ret sebeplerinden kaçınmak için (docs/arastirma/03): proje numarası doğru olmalı, YouTube logosu/markası uygulama
sayfasında kullanılmamalı, gizlilik politikası YouTube bölümünü içermeli.

**Organization / developer type:** Independent Developer / Sole Proprietor

**API client name:** Otomat

**Google Cloud project number(s):** 93875631034 (project ID: otomat-510419)

**Website / homepage:** https://scryne.github.io/otomat-site/

**Privacy policy URL:** https://scryne.github.io/otomat-site/privacy.html — **Terms of service URL:** https://scryne.github.io/otomat-site/terms.html

**Which API services do you use?** YouTube Data API v3 (videos.insert, videos.update, captions.insert, channels.list),
YouTube Analytics API (reports.query).

**Use case (describe how your client uses the API):**

> Otomat is a private, single-user publishing tool that uploads short educational data-visualization videos to one
> YouTube channel that I own and operate. Each video is generated from open public datasets (U.S. Geological Survey
> earthquake catalog, World Bank World Development Indicators, Eurostat), with the data source and license credited on
> screen and in the description. The tool runs once per day on my own GitHub Actions workflow: it renders one video,
> uploads it to my channel with `videos.insert` as a scheduled upload (`publishAt`), sets localized titles and
> descriptions, and adds caption tracks with `captions.insert`. It reads my own channel's YouTube Analytics reports
> (views, average view percentage) to decide which topics to make next. The tool has no other users, does not access
> any other channel, does not download or scrape YouTube content, and does not display YouTube data to anyone.
> Credentials are stored as encrypted GitHub Actions secrets and are only used for my channel.

**How many users / channels?** One (my own channel, Earth in Numbers: https://www.youtube.com/channel/UC6vokENR8hP2Yo1UdZSqdiQ).

**Expected daily quota usage:** ~1 upload (videos.insert, upload bucket), ~5 captions.insert (2,000 units),
~1 videos.update (50 units), ~5 Analytics queries. Well within the default quota; no quota increase requested.

**Do you store YouTube API data?** Only my own channel's video IDs and aggregated analytics numbers (views, average view
percentage) for my own videos, kept in a private repository to choose future topics. Deleted on request.

**Screencast / screenshots (if asked):** ilk API yüklemesi 2026-10-02: video `DBVL_Cakzbw` (private, 5 yerelleştirme, 5 altyazı izi); kayıt: `spikes/s9_test_yukleme.py` çıktısı. Gerekirse Studio ekran görüntüsü.
