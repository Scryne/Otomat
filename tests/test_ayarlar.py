from otomat.ayarlar import modeller


def test_model_kimlikleri_configte():
    m = modeller()
    assert m["llm"]["model"].startswith("qwen3:")
    assert len(m["tts"]["model_sha256"]) == 64
    assert len(m["tts"]["sesler_sha256"]) == 64
