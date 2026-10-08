"""Hikâye motoru (K-15…K-19, docs/arastirma/08): kaynaktan seçilen tek hikâye → senaryo (LLM) → hakem ve onarım →
sahne başına illüstrasyon → anlatıcı sesi + müzik + kelime vurgulu altyazı → mp4 + metadata.

Kanal profilinde `tur = "hikaye"` olan kanallar bu motoru kullanır (gunluk.py); veri kanallarının motoru değişmez.
Hikâye bir `OlguPaketi` olarak taşınır (kol = kaynak bölümü, anahtar = kaynak kimliği): tekrar engeli, haydut,
analitik ve yayın katmanı olduğu gibi çalışır.
"""
