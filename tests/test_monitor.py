from originsort.monitor import DownloadMonitor
from originsort.mover import MoveResult
from originsort.storage import Storage


def test_ignores_existing_and_processes_stable_new_file(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    existing = downloads / "existing.pdf"
    existing.write_bytes(b"old")
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    moved = []

    def fake_move(path, storage, *, execute=False):
        moved.append(path)
        return MoveResult(True, "이동 미리보기", path, tmp_path / "target" / path.name)

    monkeypatch.setattr("originsort.monitor.move_classified_file", fake_move)
    monitor = DownloadMonitor(downloads, storage, stable_checks=1)
    monitor.remember_existing_files()
    new_file = downloads / "new.pdf"
    new_file.write_bytes(b"new")
    assert monitor.scan_once() == []
    assert len(monitor.scan_once()) == 1
    assert moved == [new_file]
    assert existing not in moved


def test_ignores_partial_downloads(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "lecture.pdf.crdownload").write_bytes(b"partial")
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    monkeypatch.setattr(
        "originsort.monitor.move_classified_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )
    monitor = DownloadMonitor(downloads, storage, stable_checks=1)
    assert monitor.scan_once() == []
    assert monitor.scan_once() == []


def test_waits_until_file_stops_changing(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    calls = []
    monkeypatch.setattr(
        "originsort.monitor.move_classified_file",
        lambda path, storage, execute=False: calls.append(path)
        or MoveResult(True, "이동 미리보기", path, tmp_path / "target" / path.name),
    )
    monitor = DownloadMonitor(downloads, storage, stable_checks=2)
    new_file = downloads / "lecture.pdf"
    new_file.write_bytes(b"a")
    monitor.scan_once()
    new_file.write_bytes(b"still downloading")
    monitor.scan_once()
    monitor.scan_once()
    assert calls == []
    monitor.scan_once()
    assert calls == [new_file]
