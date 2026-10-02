import imageio_ffmpeg

from otomat.kosu import duman


def test_duman_videosu_uretilir(tmp_path):
    yol = duman(tmp_path / "d.mp4", saniye=1)
    assert yol.stat().st_size > 1000
    kareler, _ = imageio_ffmpeg.count_frames_and_secs(str(yol))
    assert kareler == 30
