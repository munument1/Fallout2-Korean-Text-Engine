# Fallout 2 한국어 출력 엔진 v1.1.0-beta.2 — sfall ExtraCRC 자동 호환 시험판

> **게임 테스트용 프리릴리즈.** 공식 sfall의 한국어 EXE CRC 등록이나 모든 모드의 실제 플레이 호환을 보증하지 않습니다. 원본 게임 폴더를 복사한 테스트용 설치본에서만 사용하세요. 기존 `v1.0.0` 정식판 및 `v1.1.0-beta.1`은 변경하지 않았습니다.

## 변경점

- **개발자 권고에 맞춰 `ExtraCRC`를 기본 호환 경로로 채택.** 설치기가 검증된 한국어 EXE CRC를 기존 `ddraw.ini`의 `[Debugging] ExtraCRC`에 자동 등록합니다.
- 구형 중국어·일본어 CRC와 기존 모드의 CRC 목록, `TranslationsINI`, 주석, 공백, CRLF·인코딩 등 **다른 설정을 보존**하도록 별도 INI 편집 로직을 도입했습니다.
- 같은 CRC가 이미 존재하면 INI는 수정하지 않고, 중복된 `[Debugging]` 또는 잘못된 `ExtraCRC` 입력이 있으면 강제 수정을 거절합니다.
- 설치 전에 기존 `ddraw.ini` 수정 여부를 명시하고 사용자 확인을 받습니다. 설치한 파일은 자동 백업하며, 복구 시 원본 내용으로 되돌립니다.
- `HiResMode` 수정이 필요한 일부 모드만 고급 옵션에서 따로 허용해야 합니다.
- sfall `ddraw.dll` 자체는 업데이트·교체하지 않습니다. sfall 없는 순정 게임 복사본도 설치 도구 대상으로 지원하지만 실제 게임 실행 검증이 남아 있습니다.
- 별도 게임 바이너리 없이 동작하는 CRC/INI 경계조건 회귀 테스트를 추가했습니다.

## 설치·테스트 방법

1. 원본 Fallout 2 또는 지원 모드 폴더를 **안전한 별도 경로에 복사**하세요.
2. 베타 설치기 `Fallout2-Korean-Text-Engine-Setup.exe`를 실행하세요.
3. 게임 폴더와 직접 보유한 **FO2_UPU_CHT_v34의 검증된 CJK EXE 및 기존 폰트 DLL**이 있는 폴더를 지정하세요.
4. 기존 공식 sfall이 있으면 **`ExtraCRC`는 자동 등록**됩니다. 설치 확인 창에 `ddraw.ini` 변경 여부가 표시됩니다. 수동으로 `ExtraCRC`를 입력할 필요는 없습니다.
5. Sonora 개발판·Resurrection처럼 별도 외부 HRP 충돌 방지가 필요한 프로필에서만 **고급 설정 → 모드 전용 HiResMode 추가 호환 설정**을 선택하세요.
6. 해당 게임·모드의 **한국어 번역 데이터는 별도로 적용**하세요.
7. 게임 실행 후 메뉴, 대화, 아이템 설명, 핍보이, 전투 메시지, 저장·불러오기, 설치 전 상태로 복구를 검사하세요.

## 확인할 사항

- 공식 sfall 4.5.1은 기존 CJK 수정 EXE에도 `ExtraCRC`를 사용하는 방식입니다. 새 설치기는 그 관례를 따릅니다. [sfall 개발자 설명](https://github.com/munument1/Fallout2-Korean-Text-Engine/pull/6#issuecomment-6210816149).
- `0xFCDC75E0`은 원본 Fallout 2/RPU/Et Tu/Resurrection의 현재 고정 한국어 EXE 프로필에 해당합니다. Sonora/Nevada/Olympus는 각각 다른 검증 대상 CRC를 사용합니다.
- 확인되지 않은 게임/모드 빌드에는 설치를 강행하지 않습니다. 다른 버전 sfall은 바이너리·설정이 다를 수 있으며 실제 호환을 보장하지 않습니다.
- **GitHub Actions 빌드 및 단위 테스트 성공은 게임 실행 검증이 아닙니다.** 사용자 게임 파일 기반의 통합 테스트는 별도로 수행해야 합니다.

## 첨부

- `Fallout2-Korean-Text-Engine-Setup.exe`: Windows 설치기
- `korean-text-engine.zip`: 개발자용 패키지
- `SHA256SUMS.txt`: 파일 무결성 확인용

문제 재현은 [이슈](https://github.com/munument1/Fallout2-Korean-Text-Engine/issues)에 게임·모드 버전, sfall 버전, 표시 증상, 재현 단계와 오류 화면을 남겨 주세요. 상용 EXE와 제3자 CJK DLL은 첨부하지 마세요.
