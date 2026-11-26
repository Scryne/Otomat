@echo off
rem Trend kanalı günlük koşusu (Faz 20): günün konusu -> video + kesitler -> yükleme.
rem Windows Görev Zamanlayıcı'dan çağrılır (Otomat-Trend-gunluk); GPU (Ming TTS, ACE-Step) ve ağ ister.
cd /d C:\Users\scryn\Documents\Projeler\Otomat
if not exist calisma\trend mkdir calisma\trend
echo ==== %date% %time% basladi >> calisma\trend\gunluk.log
uv run --extra ses python -m otomat.trend.uretim >> calisma\trend\gunluk.log 2>&1
if errorlevel 1 (
  echo ==== uretim DUSTU %date% %time% >> calisma\trend\gunluk.log
  exit /b 1
)
uv run --extra ses python -m otomat.trend.yukle son >> calisma\trend\gunluk.log 2>&1
echo ==== %date% %time% bitti (cikis %errorlevel%) >> calisma\trend\gunluk.log
