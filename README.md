# OriginSort

OriginSort는 Windows가 다운로드 파일에 기록한 출처 정보를 이용해 동국대학교 eClass 자료를 알맞은 폴더로 정리하는 프로그램입니다.

현재 단계는 핵심 기술 검증용 CLI입니다. 폴더 안의 파일을 변경하거나 이동하지 않고 다음 정보만 분석합니다.

- NTFS `Zone.Identifier`의 `ReferrerUrl`, `HostUrl`
- 동국대학교 eClass `ubboard` 자료실 ID
- 자료실 ID와 기존 폴더 사이의 관계

출처 정보가 없거나 지원하지 않는 URL은 그대로 건너뜁니다.

## 개발 환경

Python 3.11 이상이 필요합니다.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install pytest
$env:PYTHONPATH = (Resolve-Path src)
pytest
```

GUI 개발 실행:

```powershell
pip install "PySide6>=6.8"
py -m originsort.ui.app
```

Windows 실행 파일 빌드:

```powershell
pip install "PyInstaller>=6.0"
.\scripts\build.cmd
```

완성된 파일은 `dist\OriginSort.exe`에 생성됩니다.

## 폴더 분석

```powershell
py -m originsort.cli scan "C:\Users\사용자\Desktop\전공"
```

현재 개발 단계에서는 한글이 포함된 Windows 경로에서 editable 설치가 실패하는 Python 인코딩 문제를 피하기 위해 `PYTHONPATH` 방식을 사용합니다.

결과에는 출처 키, 발견된 파일 수, 목적지 후보와 상태가 표시됩니다. 하나의 출처가 여러 폴더에서 발견되면 `충돌`로 표시하며 자동으로 목적지를 결정하지 않습니다.

## 규칙 저장과 파일 판별

폴더 분석은 기본적으로 미리보기입니다. 충돌 없는 후보를 저장하려면 `--save`를 명시합니다.

```powershell
py -m originsort.cli rules discover "C:\Users\사용자\Desktop\대학" --save
py -m originsort.cli rules list
py -m originsort.cli classify "C:\Users\사용자\Downloads\lecture.pdf"
```

URL이나 이미 받은 파일 하나로도 규칙을 등록할 수 있습니다.

```powershell
py -m originsort.cli rules add-url "https://eclass.dongguk.edu/mod/ubboard/article.php?id=150765" "C:\과목\시소프"
py -m originsort.cli rules add-file "C:\Downloads\lecture.pdf" "C:\과목\시소프"
```

규칙은 `%LOCALAPPDATA%\OriginSort\originsort.db`에 저장됩니다. `classify`는 파일을 이동하지 않고 예상 목적지만 출력합니다.

전체 개발 순서는 [개발 계획](docs/ROADMAP.md)에서 관리합니다.

## 이동과 되돌리기

`move`와 `undo`는 기본적으로 미리보기만 합니다. 실제 변경에는 `--execute`가 필요합니다.

```powershell
py -m originsort.cli move "C:\Users\사용자\Downloads\lecture.pdf"
py -m originsort.cli move "C:\Users\사용자\Downloads\lecture.pdf" --execute
py -m originsort.cli history
py -m originsort.cli undo 1
py -m originsort.cli undo 1 --execute
```

## 다운로드 감시

감시는 시작 시 이미 존재하던 파일을 건너뛰고 이후 추가되어 크기가 안정된 파일만 처리합니다. Chrome의 `.crdownload` 같은 임시 파일은 무시합니다.

```powershell
py -m originsort.cli watch "C:\Users\사용자\Downloads"
py -m originsort.cli watch "C:\Users\사용자\Downloads" --execute
```

첫 번째 명령은 분류 결과만 출력합니다. 두 번째 명령만 실제 파일을 이동합니다. `Ctrl+C`로 종료할 수 있습니다.

이동 기록에는 원래 경로와 SHA-256 해시가 저장됩니다. 이동된 파일이 수정됐거나 원래 위치에 같은 이름의 파일이 생기면 되돌리기를 실행하지 않습니다.

