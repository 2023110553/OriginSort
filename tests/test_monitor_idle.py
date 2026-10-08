from originsort.monitor import DownloadMonitor
from originsort.storage import Storage


def test_idle_scan_does_not_enumerate_unchanged_folder(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "existing.pdf").write_bytes(b"old")
    storage = Storage(tmp_path / "rules.db")
    storage.initialize()
    monitor = DownloadMonitor(downloads, storage)
    monitor.remember_existing_files()

    monkeypatch.setattr(
        monitor,
        "_eligible",
        lambda path: (_ for _ in ()).throw(AssertionError("folder was enumerated")),
    )

    assert monitor.scan_once() == []
