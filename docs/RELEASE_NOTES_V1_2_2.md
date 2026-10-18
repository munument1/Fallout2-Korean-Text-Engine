# Fallout 2 Korean Text Engine v1.2.2 — 독립형 정식 설치기

중국어 CJK 수정 EXE 및 중국어 글꼴 DLL 없이 Fallout 2 계열 게임의 한국어 출력 기능을 설치하는 Windows 버전입니다.

## v1.2.2 변경 사항

- 설치 화면·확인창·사용법에서 DLL, CJK, Watcom, CRC 등 내부 구현 설명을 덜어냈습니다.
- 게임 폴더 선택, 번역 ZIP 적용, 설치 및 복구에 필요한 안내로 정리했습니다.
- 호환성 검사의 실행 파일·설정 파일 정보는 작업 기록에서 확인할 수 있습니다.
- 설치·호환성 검사·백업·복구 동작은 v1.2.1과 같습니다. Steam을 포함한 기존 설치 폴더를 사용할 수 있으며 시험용 복사본 준비는 선택 사항입니다.

## 다운로드

- `Fallout2-Korean-Native-Setup.exe`: 일반 사용자용 독립형 설치기 (필수)
- `Independent-Korean-Native-Font.zip`: 자체 구현한 x86 DLL과 Galmuri 글꼴을 담은 개발자·수동 적용용 자료
- `SHA256SUMS.txt`: 릴리즈 파일의 SHA-256 검증값

게임 원본 EXE, `ddraw.dll`(sfall), 유료 게임 데이터 및 한국어 번역문은 배포하지 않습니다.

## 설치 방법

1. 게임을 종료합니다. **Steam을 포함한 기존 게임·모드 설치 폴더에 바로 설치할 수 있습니다.** 시험용 전체 복사본 준비는 선택 사항입니다.
2. 게임·모드 버전에 맞는 **한국어 번역 ZIP을 먼저 적용**합니다.
3. `Fallout2-Korean-Native-Setup.exe`를 실행해 게임 폴더만 지정하고 호환성 검사를 거쳐 설치합니다.
4. 기존 게임 실행기 또는 모드 런처로 실행하여 한글 메뉴와 대화가 표시되는지 확인합니다.

설치기는 Watcom x86 PE의 코드·폰트 관리자·임포트·호출 규약 지문을 검사하고, 호환되는 실행 파일을 개별적으로 백업·패치합니다. 전체 EXE 해시가 다르더라도 주요 ABI가 같으면 허용하지만, **모든 미래 업데이트를 지원하는 것은 아닙니다**. 기존 sfall DLL을 덮어쓰지 않으며, 확인된 `ExtraCRC` 설정만 추가합니다. 기존 한국어 MSG 데이터가 없으면 언어 설정을 유지합니다.

## 대상 및 예외

Fallout 2, Restoration Project Updated(RPU), Fallout Et Tu, Sonora, Nevada, Olympus 2207의 확인된 Watcom 기반 실행 파일을 대상으로 합니다. 모드에 따라 기존 Extended sfall과 고해상도 패치 설정을 유지해야 합니다.

**Fallout 1.5 Resurrection은 이 버전의 설치 대상이 아닙니다.** 원본과 함께 제공된 구형 sfall/고해상도 패치 구성과 독립형 EXE 확장 방식이 충돌합니다. [기존 KR1.1 정식 한국어 패치](https://github.com/munument1/Fallout-1.5-Resurrection-KR/releases/tag/Resurrection-V1.5-KR1.1)를 사용하세요. 설치기는 Resurrection 런처·CFG·엔진 조합을 발견하면 파일 변경 전에 중단합니다.

Fallout 2 Community Edition처럼 Watcom ABI를 사용하지 않는 엔진은 지원 범위에서 제외됩니다.

## 백업과 복구

설치 도중 변경되는 원본 파일은 게임 폴더의 `korean_engine_backup_v2`에 보관됩니다. 설치기에서 같은 폴더를 선택하고 **설치 전 상태로 복구**를 누르세요. 파일 교체 실패 시 롤백하고, 임시 파일 및 불완전한 백업 생성을 방지하는 처리를 강화했습니다. 게임별 번역 ZIP으로 추가한 파일은 복구 대상이 아닙니다.

## 검증 범위

Steam 형태 경로에서 설치·백업·복구 및 기존 저장 파일 보존 회귀 검사를 추가했습니다. 이 검사는 합성 실행 파일과 임시 경로로 수행하며 실제 Steam 설치본을 수정하지 않습니다. Windows 빌드에서 자동 단위 테스트, 32비트 독립형 DLL 컴파일 및 export 검사, 한글 11,172자와 대화 줄바꿈 프로브, 실행 파일 번들 자체 검사, SHA-256 생성이 수행됩니다. 앞선 사용자 보유 설치본에서 메뉴 또는 도입 화면 진입, 대상별 구조 확인과 설치·복구 검증을 진행했습니다. **모든 모드의 긴 대화, 전투, 저장·불러오기, 장시간 플레이를 전수 검증한 것은 아닙니다.** 문제가 있으면 [GitHub Issues](https://github.com/munument1/Fallout2-Korean-Text-Engine/issues)에 게임·모드 버전과 오류 메시지를 남겨 주세요.

v1.0.0 CJK 기반 이전 설치기와 기존 베타 릴리즈는 기록용으로 그대로 보존합니다.
