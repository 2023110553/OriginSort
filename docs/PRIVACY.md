# 개인정보와 로컬 데이터

OriginSort는 모든 분석과 파일 이동을 사용자 PC에서 수행합니다. 네트워크 요청, 원격 분석 서비스, 텔레메트리를 사용하지 않습니다.

## 읽는 정보

- 사용자가 선택한 폴더의 파일 경로
- Windows `Zone.Identifier`에 기록된 `ReferrerUrl`, `HostUrl`
- 파일 이동 검증을 위한 파일 크기와 SHA-256 해시

## 저장하는 정보

`%LOCALAPPDATA%\OriginSort\originsort.db`에 다음 정보가 저장됩니다.

- 정규화된 eClass 출처 키
- 사용자가 승인한 목적지 폴더
- 이동 전후 경로와 검증용 해시
- 감시 폴더와 자동 정리 설정

원본 URL 전체와 파일 내용은 데이터베이스에 저장하지 않습니다. eClass 로그인 쿠키나 계정 정보에도 접근하지 않습니다.

