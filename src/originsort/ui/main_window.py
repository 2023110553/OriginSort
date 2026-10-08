from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from originsort.monitor import DownloadMonitor
from originsort.mover import MoveResult, undo_move
from originsort.parsers import parse_eclass_source
from originsort.scanner import inspect_file, scan_folder
from originsort.storage import Storage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.storage = Storage()
        self.storage.initialize()
        self.monitor: DownloadMonitor | None = None
        self.setWindowTitle("OriginSort")
        self.resize(820, 560)
        self._build_ui()
        self._build_tray()
        self._load_settings()
        self._refresh_tables()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._monitor_tick)
        self.timer.start()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("OriginSort")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("동국대학교 eClass 다운로드를 과목 폴더로 정리합니다.")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        status_row = QHBoxLayout()
        self.status_label = QLabel("자동 정리 꺼짐")
        self.auto_checkbox = QCheckBox("자동 정리")
        self.auto_checkbox.toggled.connect(self._set_auto_enabled)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.auto_checkbox)
        layout.addLayout(status_row)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel()
        choose_downloads = QPushButton("감시 폴더 선택")
        choose_downloads.clicked.connect(self._choose_watch_folder)
        analyze = QPushButton("기존 정리 폴더 분석")
        analyze.clicked.connect(self._analyze_folder)
        folder_row.addWidget(QLabel("감시 폴더:"))
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(choose_downloads)
        folder_row.addWidget(analyze)
        layout.addLayout(folder_row)

        self.tabs = QTabWidget()
        self.rules_table = self._table(["출처", "목적지", "근거", "상태"])
        self.history_table = self._table(["ID", "파일", "원래 위치", "상태"])
        self.activity_table = self._table(["결과", "파일", "목적지"])
        self.tabs.addTab(self.activity_table, "최근 활동")
        rules_page = QWidget()
        rules_layout = QVBoxLayout(rules_page)
        rules_layout.addWidget(self.rules_table)
        rules_buttons = QHBoxLayout()
        add_url = QPushButton("URL로 추가")
        add_url.clicked.connect(self._add_rule_from_url)
        add_file = QPushButton("파일로 추가")
        add_file.clicked.connect(self._add_rule_from_file)
        toggle_rule = QPushButton("선택 규칙 켜기/끄기")
        toggle_rule.clicked.connect(self._toggle_selected_rule)
        delete_rule = QPushButton("선택 규칙 삭제")
        delete_rule.clicked.connect(self._delete_selected_rule)
        for button in (add_url, add_file, toggle_rule, delete_rule):
            rules_buttons.addWidget(button)
        rules_layout.addLayout(rules_buttons)
        self.tabs.addTab(rules_page, "분류 규칙")
        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_layout.addWidget(self.history_table)
        undo_button = QPushButton("선택한 이동 되돌리기")
        undo_button.clicked.connect(self._undo_selected)
        history_layout.addWidget(undo_button)
        self.tabs.addTab(history_page, "이동 기록")
        layout.addWidget(self.tabs)
        self.setCentralWidget(root)

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        menu = QMenu()
        show_action = QAction("OriginSort 열기", self)
        show_action.triggered.connect(self._show_window)
        self.pause_action = QAction("자동 정리 시작", self)
        self.pause_action.triggered.connect(
            lambda: self.auto_checkbox.setChecked(not self.auto_checkbox.isChecked())
        )
        quit_action = QAction("종료", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_window()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.tray.show()

    def _load_settings(self) -> None:
        folder = self.storage.get_setting("watch_folder", str(Path.home() / "Downloads"))
        self._set_watch_folder(Path(folder))
        enabled = self.storage.get_setting("auto_enabled", "0") == "1"
        self.auto_checkbox.setChecked(enabled)

    def _set_watch_folder(self, folder: Path) -> None:
        resolved = folder.expanduser().resolve()
        self.folder_label.setText(str(resolved))
        self.storage.set_setting("watch_folder", str(resolved))
        self.monitor = None
        if resolved.is_dir():
            self.monitor = DownloadMonitor(
                resolved, self.storage, execute=True, on_result=self._on_move_result
            )
            self.monitor.remember_existing_files()

    def _set_auto_enabled(self, enabled: bool) -> None:
        self.storage.set_setting("auto_enabled", "1" if enabled else "0")
        self.status_label.setText("자동 정리 켜짐" if enabled else "자동 정리 꺼짐")
        self.pause_action.setText("자동 정리 일시정지" if enabled else "자동 정리 시작")

    def _choose_watch_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "다운로드 감시 폴더 선택",
                                                   self.folder_label.text())
        if folder:
            self._set_watch_folder(Path(folder))

    def _analyze_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "기존 정리 폴더 선택")
        if not folder:
            return
        candidates, inspected = scan_folder(Path(folder))
        valid = [item for item in candidates if len(item.destinations) == 1]
        conflicts = len(candidates) - len(valid)
        answer = QMessageBox.question(
            self,
            "분석 결과",
            f"파일 {inspected}개에서 규칙 {len(valid)}개를 찾았습니다.\n"
            f"충돌 {conflicts}개는 저장하지 않습니다.\n\n규칙을 저장할까요?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for candidate in valid:
            self.storage.save_rule(
                candidate.source_key,
                next(iter(candidate.destinations)),
                evidence_count=candidate.evidence_count,
                creation_method="folder_scan",
            )
        self._refresh_tables()

    def _choose_destination(self) -> Path | None:
        folder = QFileDialog.getExistingDirectory(self, "저장할 과목 폴더 선택")
        return Path(folder) if folder else None

    def _add_rule_from_url(self) -> None:
        url, accepted = QInputDialog.getText(self, "URL로 규칙 추가",
                                             "eClass 자료실 URL")
        if not accepted:
            return
        source = parse_eclass_source(url.strip())
        if source is None:
            QMessageBox.warning(self, "등록 실패", "지원되는 eClass 자료실 URL이 아닙니다.")
            return
        destination = self._choose_destination()
        if destination is None:
            return
        self.storage.save_rule(source.key, destination, evidence_count=0,
                               creation_method="url_input")
        self._refresh_tables()

    def _add_rule_from_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "기존 eClass 파일 선택")
        if not file_name:
            return
        evidence = inspect_file(Path(file_name))
        if evidence is None:
            QMessageBox.warning(self, "등록 실패", "파일에서 eClass 출처를 찾지 못했습니다.")
            return
        destination = self._choose_destination()
        if destination is None:
            return
        self.storage.save_rule(evidence.source.key, destination, evidence_count=1,
                               creation_method="sample_file")
        self._refresh_tables()

    def _selected_rule_key(self) -> str | None:
        row = self.rules_table.currentRow()
        return self.rules_table.item(row, 0).text() if row >= 0 else None

    def _toggle_selected_rule(self) -> None:
        key = self._selected_rule_key()
        if key is None:
            QMessageBox.information(self, "규칙 관리", "규칙을 선택하세요.")
            return
        rule = self.storage.get_rule(key)
        if rule:
            self.storage.set_rule_enabled(key, not rule.enabled)
            self._refresh_tables()

    def _delete_selected_rule(self) -> None:
        key = self._selected_rule_key()
        if key is None:
            QMessageBox.information(self, "규칙 관리", "규칙을 선택하세요.")
            return
        answer = QMessageBox.question(self, "규칙 삭제", f"{key}\n\n삭제할까요?")
        if answer == QMessageBox.StandardButton.Yes:
            self.storage.delete_rule(key)
            self._refresh_tables()

    def _monitor_tick(self) -> None:
        if self.auto_checkbox.isChecked() and self.monitor:
            self.monitor.scan_once()

    def _on_move_result(self, result: MoveResult) -> None:
        row = self.activity_table.rowCount()
        self.activity_table.insertRow(row)
        values = [result.reason, result.source.name,
                  str(result.destination) if result.destination else "-"]
        for column, value in enumerate(values):
            self.activity_table.setItem(row, column, QTableWidgetItem(value))
        self._refresh_history()

    def _refresh_tables(self) -> None:
        self.rules_table.setRowCount(0)
        for rule in self.storage.list_rules():
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            values = [rule.source_key, str(rule.destination),
                      str(rule.evidence_count), "사용" if rule.enabled else "중지"]
            for column, value in enumerate(values):
                self.rules_table.setItem(row, column, QTableWidgetItem(value))
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.history_table.setRowCount(0)
        for record in self.storage.list_moves():
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            values = [str(record.id), record.destination_path.name,
                      str(record.source_path), "되돌림" if record.undone_at else "이동됨"]
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(value))

    def _undo_selected(self) -> None:
        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "되돌리기", "이동 기록을 선택하세요.")
            return
        move_id = int(self.history_table.item(row, 0).text())
        preview = undo_move(move_id, self.storage)
        if not preview.success:
            QMessageBox.warning(self, "되돌리기 불가", preview.reason)
            return
        answer = QMessageBox.question(
            self, "되돌리기 확인",
            f"{preview.source}\n→ {preview.destination}\n\n되돌릴까요?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            result = undo_move(move_id, self.storage, execute=True)
            if not result.success:
                QMessageBox.warning(self, "되돌리기 실패", result.reason)
            self._refresh_history()

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage("OriginSort", "백그라운드에서 계속 실행 중입니다.",
                              QSystemTrayIcon.MessageIcon.Information, 2000)
