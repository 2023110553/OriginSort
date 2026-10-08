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

## 폴더 분석

```powershell
py -m originsort.cli scan "C:\Users\사용자\Desktop\전공"
```

현재 개발 단계에서는 한글이 포함된 Windows 경로에서 editable 설치가 실패하는 Python 인코딩 문제를 피하기 위해 `PYTHONPATH` 방식을 사용합니다.

결과에는 출처 키, 발견된 파일 수, 목적지 후보와 상태가 표시됩니다. 하나의 출처가 여러 폴더에서 발견되면 `충돌`로 표시하며 자동으로 목적지를 결정하지 않습니다.

