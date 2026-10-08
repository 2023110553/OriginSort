from pathlib import Path

import originsort.mover as mover_module
from originsort.classifier import Classification
from originsort.storage import Rule, Storage


def _classification(source: Path, destination: Path) -> Classification:
    rule = Rule("eclass.dongguk.edu:ubboard:150765", destination,
                3, "folder_scan", True)
    return Classification(source, rule.source_key, rule, "분류 가능")


def test_move_defaults_to_preview(tmp_path, monkeypatch) -> None:
    source = tmp_path / "Downloads" / "lecture.pdf"
    source.parent.mkdir()
    source.write_bytes(b"lecture")
    destination = tmp_path / "시소프"
    destination.mkdir()
    monkeypatch.setattr(mover_module, "classify_file",
                        lambda path, storage: _classification(source, destination))
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    result = mover_module.move_classified_file(source, storage)
    assert result.reason == "이동 미리보기"
    assert source.exists()
    assert not (destination / source.name).exists()


def test_moves_records_and_undoes_file(tmp_path, monkeypatch) -> None:
    source = tmp_path / "Downloads" / "lecture.pdf"
    source.parent.mkdir()
    source.write_bytes(b"lecture")
    destination = tmp_path / "시소프"
    destination.mkdir()
    monkeypatch.setattr(mover_module, "classify_file",
                        lambda path, storage: _classification(source, destination))
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    moved = mover_module.move_classified_file(source, storage, execute=True)
    assert moved.success
    assert moved.move_id is not None
    assert not source.exists()
    assert moved.destination is not None and moved.destination.exists()
    preview = mover_module.undo_move(moved.move_id, storage)
    assert preview.reason == "되돌리기 미리보기"
    assert not source.exists()
    undone = mover_module.undo_move(moved.move_id, storage, execute=True)
    assert undone.success
    assert source.read_bytes() == b"lecture"


def test_undo_refuses_modified_file(tmp_path, monkeypatch) -> None:
    source = tmp_path / "Downloads" / "lecture.pdf"
    source.parent.mkdir()
    source.write_bytes(b"original")
    destination = tmp_path / "시소프"
    destination.mkdir()
    monkeypatch.setattr(mover_module, "classify_file",
                        lambda path, storage: _classification(source, destination))
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    moved = mover_module.move_classified_file(source, storage, execute=True)
    assert moved.destination is not None and moved.move_id is not None
    moved.destination.write_bytes(b"modified")
    result = mover_module.undo_move(moved.move_id, storage, execute=True)
    assert not result.success
    assert "변경" in result.reason


def test_duplicate_name_gets_numbered_suffix(tmp_path) -> None:
    original = tmp_path / "lecture.pdf"
    original.write_bytes(b"existing")
    assert mover_module.available_destination(original).name == "lecture (1).pdf"
