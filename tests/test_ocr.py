from app.ocr import OcrResult, _parse, normalize_tag


def test_parse_well_formed():
    r = _parse('{"tag": "042", "confidence": 0.91}')
    assert r.tag == "042"
    assert r.confidence == 0.91


def test_parse_fenced_json():
    r = _parse('```json\n{"tag": "7", "confidence": 0.5}\n```')
    assert r.tag == "7"
    assert r.confidence == 0.5


def test_parse_null_tag():
    r = _parse('{"tag": null, "confidence": 1.0}')
    assert r.tag is None
    assert r.confidence == 1.0


def test_parse_garbage():
    r = _parse("I cannot tell")
    assert r.tag is None
    assert r.confidence is None
    assert r.raw == "I cannot tell"


def test_normalize_tag():
    assert normalize_tag("042") == "042"
    assert normalize_tag(" #042 ") == "042"
    assert normalize_tag("tag-12a3") == "123"
    assert normalize_tag("") == ""
