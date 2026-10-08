from originsort.parsers.dongguk_eclass import parse_eclass_source


def test_parses_ubboard_article_id() -> None:
    source = parse_eclass_source(
        "https://eclass.dongguk.edu/mod/ubboard/article.php?id=150765&bwid=196561"
    )

    assert source is not None
    assert source.key == "eclass.dongguk.edu:ubboard:150765"


def test_does_not_confuse_course_id_with_ubboard_id() -> None:
    source = parse_eclass_source(
        "https://eclass.dongguk.edu/course/view.php?id=56902"
    )

    assert source is None


def test_rejects_other_domains() -> None:
    source = parse_eclass_source(
        "https://example.com/mod/ubboard/article.php?id=150765"
    )

    assert source is None

