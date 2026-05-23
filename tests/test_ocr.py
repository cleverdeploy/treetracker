from app.ocr import normalize_tag


def test_normalize_tag():
    assert normalize_tag("042") == "042"
    assert normalize_tag(" #042 ") == "042"
    assert normalize_tag("tag-12a3") == "123"
    assert normalize_tag("") == ""
