from ingestion.normalizer import TextNormalizer


def test_normalize_crlf_to_lf():
    n = TextNormalizer()
    assert n.normalize("hello\r\nworld") == "hello\nworld"


def test_normalize_extra_spaces():
    n = TextNormalizer()
    result = n.normalize("hello    world")
    assert result == "hello world"


def test_normalize_collapse_multiple_blank_lines():
    n = TextNormalizer()
    result = n.normalize("line1\n\n\n\nline2")
    assert result == "line1\n\nline2"


def test_normalize_fix_hyphenated_break():
    n = TextNormalizer()
    result = n.normalize("experi-\nment")
    assert result == "experiment"


def test_normalize_strip_trailing_whitespace():
    n = TextNormalizer()
    result = n.normalize("  hello  \n  world  ")
    assert result == "hello\nworld"


def test_normalize_idempotent():
    n = TextNormalizer()
    text = "The band gap of TiO2 is 3.2 eV.\n\nThis makes it suitable for photocatalysis."
    result1 = n.normalize(text)
    result2 = n.normalize(result1)
    assert result1 == result2


def test_normalize_empty_string():
    n = TextNormalizer()
    assert n.normalize("") == ""
    assert n.normalize("   ") == ""
