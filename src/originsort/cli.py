from __future__ import annotations

import argparse
from pathlib import Path

from .classifier import classify_file
from .mover import move_classified_file, undo_move
from .monitor import DownloadMonitor
from .parsers import parse_eclass_source
from .scanner import inspect_file
from .scanner import RuleCandidate, scan_folder
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="originsort",
        description="동국대학교 eClass 다운로드 출처 분석기",
    )
    parser.add_argument("--db", type=Path, help="SQLite 데이터베이스 경로")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="기존 정리 폴더를 분석합니다")
    scan.add_argument("folder", type=Path, help="분석할 폴더")

    rules = commands.add_parser("rules", help="분류 규칙을 관리합니다")
    rule_commands = rules.add_subparsers(dest="rules_command", required=True)
    discover = rule_commands.add_parser("discover", help="기존 폴더에서 규칙 후보를 찾습니다")
    discover.add_argument("folder", type=Path)
    discover.add_argument("--save", action="store_true",
                          help="충돌 없는 후보를 데이터베이스에 저장합니다")
    rule_commands.add_parser("list", help="저장된 규칙을 표시합니다")
    add_url = rule_commands.add_parser("add-url", help="eClass URL로 규칙을 추가합니다")
    add_url.add_argument("url")
    add_url.add_argument("destination", type=Path)
    add_file = rule_commands.add_parser("add-file", help="기존 파일의 출처로 규칙을 추가합니다")
    add_file.add_argument("file", type=Path)
    add_file.add_argument("destination", type=Path)
    for action in ("enable", "disable", "delete"):
        command = rule_commands.add_parser(action, help=f"규칙을 {action} 처리합니다")
        command.add_argument("source_key")

    classify = commands.add_parser("classify",
                                   help="파일을 이동하지 않고 예상 목적지를 표시합니다")
    classify.add_argument("file", type=Path)

    move = commands.add_parser("move", help="분류된 파일의 이동을 미리보거나 실행합니다")
    move.add_argument("file", type=Path)
    move.add_argument("--execute", action="store_true",
                      help="미리보기 대신 실제로 이동합니다")

    history = commands.add_parser("history", help="최근 이동 기록을 표시합니다")
    history.add_argument("--limit", type=int, default=20)

    undo = commands.add_parser("undo", help="기록된 이동을 되돌립니다")
    undo.add_argument("move_id", type=int)
    undo.add_argument("--execute", action="store_true",
                      help="미리보기 대신 실제로 되돌립니다")

    watch = commands.add_parser("watch", help="새 다운로드를 감시합니다")
    watch.add_argument("folder", type=Path)
    watch.add_argument("--execute", action="store_true",
                       help="판별된 파일을 실제로 이동합니다")
    watch.add_argument("--interval", type=float, default=1.0,
                       help="폴더 확인 주기(초)")
    return parser


def _resolve_directory(folder: Path) -> Path | None:
    resolved = folder.expanduser().resolve()
    return resolved if resolved.is_dir() else None


def _print_candidates(candidates: list[RuleCandidate], inspected: int) -> None:
    print(f"분석한 파일: {inspected}개")
    print(f"발견한 출처: {len(candidates)}개")
    for candidate in candidates:
        print(f"\n[{candidate.status}] {candidate.source_key}")
        print(f"근거 파일: {candidate.evidence_count}개")
        for destination, count in sorted(
            candidate.destinations.items(), key=lambda item: str(item[0])
        ):
            print(f"  {destination} ({count}개)")


def run_scan(folder: Path) -> int:
    resolved = _resolve_directory(folder)
    if resolved is None:
        print(f"폴더를 찾을 수 없습니다: {folder.expanduser().resolve()}")
        return 2
    candidates, inspected = scan_folder(resolved)
    _print_candidates(candidates, inspected)
    return 0


def run_discover(folder: Path, storage: Storage, save: bool) -> int:
    resolved = _resolve_directory(folder)
    if resolved is None:
        print(f"폴더를 찾을 수 없습니다: {folder.expanduser().resolve()}")
        return 2
    candidates, inspected = scan_folder(resolved)
    _print_candidates(candidates, inspected)
    if not save:
        print("\n미리보기만 수행했습니다. 저장하려면 --save를 추가하세요.")
        return 0
    saved = 0
    for candidate in candidates:
        if len(candidate.destinations) != 1:
            continue
        destination = next(iter(candidate.destinations))
        storage.save_rule(candidate.source_key, destination,
                          evidence_count=candidate.evidence_count,
                          creation_method="folder_scan")
        saved += 1
    print(f"\n충돌 없는 규칙 {saved}개를 저장했습니다.")
    return 0


def run_list_rules(storage: Storage) -> int:
    rules = storage.list_rules()
    if not rules:
        print("저장된 규칙이 없습니다.")
        return 0
    for rule in rules:
        state = "사용" if rule.enabled else "중지"
        print(f"[{state}] {rule.source_key}")
        print(f"  → {rule.destination} (근거 {rule.evidence_count}개)")
    return 0


def _valid_destination(path: Path) -> Path | None:
    resolved = path.expanduser().resolve()
    return resolved if resolved.is_dir() else None


def run_add_url(url: str, destination: Path, storage: Storage) -> int:
    source = parse_eclass_source(url)
    target = _valid_destination(destination)
    if source is None:
        print("지원되는 eClass 자료실 URL이 아닙니다.")
        return 2
    if target is None:
        print(f"대상 폴더를 찾을 수 없습니다: {destination.expanduser().resolve()}")
        return 2
    storage.save_rule(source.key, target, evidence_count=0,
                      creation_method="url_input")
    print(f"규칙 저장: {source.key} → {target}")
    return 0


def run_add_file(file_path: Path, destination: Path, storage: Storage) -> int:
    resolved = file_path.expanduser().resolve()
    target = _valid_destination(destination)
    evidence = inspect_file(resolved) if resolved.is_file() else None
    if evidence is None:
        print("파일에서 지원되는 eClass 출처를 찾지 못했습니다.")
        return 2
    if target is None:
        print(f"대상 폴더를 찾을 수 없습니다: {destination.expanduser().resolve()}")
        return 2
    storage.save_rule(evidence.source.key, target, evidence_count=1,
                      creation_method="sample_file")
    print(f"규칙 저장: {evidence.source.key} → {target}")
    return 0


def run_classify(path: Path, storage: Storage) -> int:
    classification = classify_file(path, storage)
    print(f"파일: {classification.file_path}")
    if classification.source_key:
        print(f"출처: {classification.source_key}")
    print(f"결과: {classification.reason}")
    if classification.destination:
        print(f"예상 목적지: {classification.destination}")
        return 0
    return 3


def _print_move_result(result) -> int:
    print(f"결과: {result.reason}")
    print(f"원본: {result.source}")
    if result.destination:
        print(f"대상: {result.destination}")
    if result.move_id is not None:
        print(f"이동 기록 ID: {result.move_id}")
    return 0 if result.success else 3


def run_history(storage: Storage, limit: int) -> int:
    records = storage.list_moves(max(1, limit))
    if not records:
        print("이동 기록이 없습니다.")
        return 0
    for record in records:
        state = "되돌림" if record.undone_at else "이동됨"
        print(f"[{record.id}] {state} {record.destination_path}")
        print(f"  원래 위치: {record.source_path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    storage = Storage(args.db)
    storage.initialize()
    if args.command == "scan":
        return run_scan(args.folder)
    if args.command == "rules" and args.rules_command == "discover":
        return run_discover(args.folder, storage, args.save)
    if args.command == "rules" and args.rules_command == "list":
        return run_list_rules(storage)
    if args.command == "rules" and args.rules_command == "add-url":
        return run_add_url(args.url, args.destination, storage)
    if args.command == "rules" and args.rules_command == "add-file":
        return run_add_file(args.file, args.destination, storage)
    if args.command == "rules" and args.rules_command in {"enable", "disable"}:
        enabled = args.rules_command == "enable"
        if not storage.set_rule_enabled(args.source_key, enabled):
            print("규칙을 찾을 수 없습니다.")
            return 2
        print("규칙 상태를 변경했습니다.")
        return 0
    if args.command == "rules" and args.rules_command == "delete":
        if not storage.delete_rule(args.source_key):
            print("규칙을 찾을 수 없습니다.")
            return 2
        print("규칙을 삭제했습니다.")
        return 0
    if args.command == "classify":
        return run_classify(args.file, storage)
    if args.command == "move":
        return _print_move_result(
            move_classified_file(args.file, storage, execute=args.execute)
        )
    if args.command == "history":
        return run_history(storage, args.limit)
    if args.command == "undo":
        return _print_move_result(
            undo_move(args.move_id, storage, execute=args.execute)
        )
    if args.command == "watch":
        folder = _resolve_directory(args.folder)
        if folder is None:
            print(f"폴더를 찾을 수 없습니다: {args.folder.expanduser().resolve()}")
            return 2
        mode = "자동 이동" if args.execute else "미리보기"
        print(f"감시 시작: {folder} ({mode})")
        monitor = DownloadMonitor(folder, storage, execute=args.execute,
                                  on_result=_print_move_result)
        try:
            monitor.run(max(0.2, args.interval))
        except KeyboardInterrupt:
            print("감시를 종료했습니다.")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
