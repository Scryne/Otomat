---
proje: Otomat
created: 2026-10-02
type: dokunus-noktalari
---
# Scryne'ın dokunuş noktaları

K-2 gereği Scryne'ın elini sürmesi gereken her an burada listelenir. Yeni bir dokunuş eklemek bir tasarım
kusurudur; önce otomatikleştirmeyi dene, olmazsa buraya gerekçesiyle yaz.

## Bir kerelik (kurulum)
| # | Ne | Neden otomatik olamaz | Süre |
|---|---|---|---|
| D1 ✅ 2026-10-03 (marka hesabı) | YouTube kanalı (marka hesabı) açmak | Hesap kişiye ait | 5 dk |
| D2 ✅ 2026-10-03 (kendi hesabında) | Google Cloud projesinde YouTube Data API'yi açıp OAuth onayını vermek | Kimlik doğrulama sahibin elinde | 10 dk (adım adım rehberle) |
| D3 ✅ 2026-10-03 | API denetim (audit) formunu göndermek | Başvuru sahibi beyanı | 5 dk (metni ben hazırlarım) |
| D5 ✅ 2026-10-05 | Buffer ücretsiz hesap + kanalı bağlama + API anahtarı (`.env`) | Hesap ve OAuth onayı sahibin elinde | 5 dk |
| D4 | Para kazanma eşiği aşılınca: AdSense, kimlik/PIN, 20/B istisna belgesi | Yasal kimlik, posta, vergi dairesi | eşik anında, ~1 gün |

## Süren
| # | Ne | Sıklık | Süre |
|---|---|---|---|
| R1 | (isteğe bağlı) Haftalık raporu okumak (vault + Kokpit); Scryne 10-05: "hiçbir şeye dokunmayayım" | haftalık | 2 dk |
| ~~R2~~ | ~~Studio'da toplu "herkese açık"~~ — 2026-10-05'ten beri yok: `OTOMAT_YAYIN=buffer` yayını kendisi yapar | — | — |
| A1 | (yalnız alarm issue'su token düştü derse) yerelde yeniden yetki: tarayıcıda izin, sonra secret güncelleme | olay | 2 dk |
