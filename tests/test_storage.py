from originsort.storage import Storage


def test_saves_and_updates_rule(tmp_path) -> None:
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    first_destination = tmp_path / "first"
    second_destination = tmp_path / "second"
    storage.save_rule("eclass.dongguk.edu:ubboard:150765", first_destination,
                      evidence_count=2, creation_method="folder_scan")
    storage.save_rule("eclass.dongguk.edu:ubboard:150765", second_destination,
                      evidence_count=4, creation_method="folder_scan")
    rules = storage.list_rules()
    assert len(rules) == 1
    assert rules[0].destination == second_destination.resolve()
    assert rules[0].evidence_count == 4


def test_unknown_rule_returns_none(tmp_path) -> None:
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    assert storage.get_rule("missing") is None

