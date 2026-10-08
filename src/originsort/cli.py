from __future__ import annotations

import argparse
from pathlib import Path

from .scanner import scan_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="originsort",
        description="동국대학교 eClass 다운로드 출처 분석기",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="기존 정리 폴더를 분석합니다")
    scan.add_argument("folder", type=Path, help="분석할 폴더")
    return parser


def run_scan(folder: Path) -> int:
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        print(f"폴더를 찾을 수 없습니다: {folder}")
        return 2

    candidates, inspected = scan_folder(folder)
    print(f"분석한 파일: {inspected}개")
    print(f"발견한 출처: {len(candidates)}개")

    for candidate in candidates:
        print(f"\n[{candidate.status}] {candidate.source_key}")
        print(f"근거 파일: {candidate.evidence_count}개")
        for destination, count in sorted(
            candidate.destinations.items(), key=lambda item: str(item[0])
        ):
            print(f"  {destination} ({count}개)")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        return run_scan(args.folder)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

