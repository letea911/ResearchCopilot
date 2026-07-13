from ingestion.bibtex import BibTeXParser


SAMPLE = '''
@article{smith2024,
  title = {A Study of High Entropy LDH},
  author = {Smith, John A and Wang, Li},
  year = {2024},
  journal = {Nature Materials},
  doi = {10.1038/s41563-024-01234},
  abstract = {We study high entropy layered double hydroxides.}
}

@article{chen2023,
  title = "Anion Intercalation Engineering",
  author = "Chen, Qiang",
  year = "2023",
  journal = "Advanced Materials"
}
'''


def test_parse_two_entries():
    p = BibTeXParser()
    entries = p.parse_text(SAMPLE)
    assert len(entries) == 2


def test_title_and_journal():
    entries = BibTeXParser().parse_text(SAMPLE)
    assert entries[0].title == "A Study of High Entropy LDH"
    assert entries[0].journal == "Nature Materials"
    assert entries[0].year == 2024
    assert entries[0].doi == "10.1038/s41563-024-01234"


def test_author_formatting():
    entries = BibTeXParser().parse_text(SAMPLE)
    # "Smith, John A and Wang, Li" -> "Smith JA, Wang L"
    assert entries[0].authors == "Smith JA, Wang L"
    assert entries[1].authors == "Chen Q"


def test_quoted_values():
    entries = BibTeXParser().parse_text(SAMPLE)
    assert entries[1].title == "Anion Intercalation Engineering"
    assert entries[1].journal == "Advanced Materials"


def test_missing_fields_ok():
    entries = BibTeXParser().parse_text(SAMPLE)
    assert entries[1].doi is None
    assert entries[1].abstract is None
