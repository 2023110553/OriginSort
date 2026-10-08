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


def test_persists_app_setting(tmp_path) -> None:
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    assert storage.get_setting("auto_enabled", "0") == "0"
    storage.set_setting("auto_enabled", "1")
    assert storage.get_setting("auto_enabled") == "1"


def test_disables_and_deletes_rule(tmp_path) -> None:
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    key = "eclass.dongguk.edu:ubboard:150765"
    storage.save_rule(key, tmp_path, evidence_count=1,
                      creation_method="sample_file")
    assert storage.set_rule_enabled(key, False)
    assert storage.get_rule(key) is not None
    assert storage.get_rule(key).enabled is False
    assert storage.delete_rule(key)
    assert storage.get_rule(key) is None

