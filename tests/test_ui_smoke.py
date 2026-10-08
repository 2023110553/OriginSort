import pytest


PySide6 = pytest.importorskip("PySide6")


def test_main_window_starts_offscreen(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("ORIGINSORT_DATA_DIR", str(tmp_path / "data"))
    from PySide6.QtWidgets import QApplication

    from originsort.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "OriginSort"
    assert window.rules_table.columnCount() == 4
    window.timer.stop()
    window.tray.hide()
    window.deleteLater()
    app.processEvents()
