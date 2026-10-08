import originsort.classifier as classifier_module
from originsort.models import Evidence, SourceIdentity
from originsort.storage import Storage


def test_classifies_file_with_enabled_rule(tmp_path, monkeypatch) -> None:
    downloaded = tmp_path / "Downloads" / "lecture.pdf"
    downloaded.parent.mkdir()
    downloaded.write_bytes(b"pdf")
    destination = tmp_path / "시소프"
    destination.mkdir()
    source = SourceIdentity("dongguk_eclass", "ubboard", "150765",
                            "eclass.dongguk.edu")
    monkeypatch.setattr(classifier_module, "inspect_file",
                        lambda path: Evidence(path, path.parent, source))
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    storage.save_rule(source.key, destination, evidence_count=3,
                      creation_method="folder_scan")
    result = classifier_module.classify_file(downloaded, storage)
    assert result.reason == "분류 가능"
    assert result.destination == destination / "lecture.pdf"


def test_leaves_file_when_source_is_unknown(tmp_path, monkeypatch) -> None:
    downloaded = tmp_path / "local.pdf"
    downloaded.write_bytes(b"pdf")
    monkeypatch.setattr(classifier_module, "inspect_file", lambda path: None)
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    result = classifier_module.classify_file(downloaded, storage)
    assert result.destination is None
    assert result.reason == "지원되는 eClass 출처 정보 없음"

