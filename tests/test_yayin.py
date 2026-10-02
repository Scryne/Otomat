from otomat.ses import Parca
from otomat.yayin.ceviri import rakamlar
from otomat.yayin.srt import srt


def test_rakamlar_ayractan_bagimsiz():
    assert rakamlar("1,047 quakes, magnitude 7.8") == rakamlar("1.047 sismos, magnitud 7,8")
    assert rakamlar("1 047 séismes") == ["1047"]
    assert rakamlar("on August 14, 2026") == rakamlar("el 14 de agosto de 2026") == ["14", "2026"]
    assert rakamlar("2026-10-02") == ["02", "10", "2026"]
    assert rakamlar("1,047") != rakamlar("1,074")


def test_srt():
    metin = srt([Parca(0.0, 1.5, "Hello world"), Parca(1.5, 61.25, "Second")])
    assert metin.startswith("1\n00:00:00,000 --> 00:00:01,500\nHello world\n")
    assert "2\n00:00:01,500 --> 00:01:01,250\nSecond" in metin
    assert "Hola" in srt([Parca(0, 1, "Hello")], ["Hola"])
