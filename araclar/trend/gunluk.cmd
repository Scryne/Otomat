@echo off
rem Trend kanalı koşusu (Faz 20, K-49): Pazartesi/Çarşamba/Cumartesi 09:00 (Görev Zamanlayıcı: Otomat-Trend-gunluk).
rem Günün konusu -> video + kesitler -> yükleme (kapak yüklenmeden hiçbir şey zamanlanmaz; video sıradaki boş
rem yayın gününe 21:50 UTC). GPU (Ming TTS, ACE-Step) ve ağ ister. Üretim düşse de kapak bekleyen işler denenir.
cd /d C:\Users\scryn\Documents\Projeler\Otomat
set PYTHONIOENCODING=utf-8
if not exist calisma\trend mkdir calisma\trend
echo ==== %date% %time% basladi >> calisma\trend\gunluk.log
set URETIM=0
uv run --extra ses python -m otomat.trend.uretim >> calisma\trend\gunluk.log 2>&1
if errorlevel 1 (
  set URETIM=1
  echo ==== uretim DUSTU %date% %time% >> calisma\trend\gunluk.log
)
uv run --extra ses python -m otomat.trend.yukle son >> calisma\trend\gunluk.log 2>&1
set YUKLE=%errorlevel%
echo ==== %date% %time% bitti (uretim %URETIM%, yukle %YUKLE%) >> calisma\trend\gunluk.log
if not "%URETIM%"=="0" exit /b 1
exit /b %YUKLE%
