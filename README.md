# Fallout 2 한국어 출력 엔진

> **개발 중인 독립형 실험판:** 중국어 CJK EXE·폰트 DLL 없이 한글 엔진을 설치합니다. 현재 개발판은 **순정 Fallout 2 US 1.02d와 실제 검증된 RPU 고해상도 패치 실행 파일**을 폴더에서 자동 판별해 설치하며, 게임 종류를 직접 선택할 필요가 없습니다. 다른 RPU/HRP 버전이나 Et Tu 등의 지원은 별도 검증이 필요합니다. [RPU 자동 판별 검증 보고서](docs/NATIVE_RPU_AUTO_DETECTION_KO.md) · [독립형 엔진 진행 상황](docs/NATIVE_EXECUTABLE_PROGRESS_KO.md). 아래 기존 정식 설치 방식과는 별개입니다.

클래식 **Fallout 2와 호환 모드에서 한글을 표시해 주는 프로그램**입니다. 한국어 글꼴과 줄바꿈을 지원하며, 기존 파일은 설치할 때 백업합니다.

## 다운로드

**[Windows 설치기 다운로드 (.exe)](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/latest/download/Fallout2-Korean-Text-Engine-Setup.exe)**

Python이나 명령어 입력 없이 실행할 수 있습니다.

## 설치 방법

1. **게임 준비:** Fallout 2 또는 지원 모드를 별도 폴더에 준비합니다. **순정 Fallout 2에서 sfall 없이 설치하는 구성은 지원 대상으로 추가했으며 실제 실행 검증은 아직 필요합니다.** 모드에 sfall이 포함되어 있다면 기존 파일을 그대로 둡니다.
2. **설치기 실행:** 게임 폴더와 직접 확보한 **FO2_UPU_CHT_v34의 CJK 파일 폴더**를 선택합니다.
3. **「설치하기」 클릭:** 파일을 자동 검사하고 설치합니다. 기존 sfall을 유지하고, 필요한 경우 `ExtraCRC` 값만 자동 추가합니다(설치 전 확인·백업). 모드별 별도 HRP 수정이 필요한 경우에는 고급 설정을 요청합니다. 설치 후 **게임별 한국어 번역 패치**를 별도로 적용하면 됩니다.

CJK 원본 폴더에는 해당 패키지의 `Fallout2.exe`와 `fallout2font.dll`이 함께 있어야 합니다. Sonora·Nevada·Olympus 같은 모드에서는 원본 Fallout 2 US 1.02d 실행 파일을 추가로 선택하라는 안내가 나타날 수 있습니다.

**설치 전 상태로 되돌리기:** 설치기에서 같은 게임 폴더를 선택한 후 **「설치 전 상태로 복구」**를 누르세요. 게임별 번역 패치로 별도 설치한 파일은 복구 대상이 아닙니다.

## 지원 게임

Fallout 2 원본 / Restoration Project Updated / Fallout Et Tu / Fallout Sonora / Fallout Nevada Extended / Olympus 2207 / Fallout 1.5 Resurrection

지원은 **검증된 게임·모드 버전**에 한합니다. 일부 모드는 게임 자체의 기능을 위해 sfall이 필요할 수 있으며, 이 출력 엔진이 그 의존성을 대신하지는 않습니다. 다른 버전의 실행 파일은 안전을 위해 패치를 거부합니다. 자세한 버전별 정보는 [기술 문서](docs/TECHNICAL.md)를 확인하세요.

## 알아두기

- 이 프로그램은 **한국어 출력 엔진**입니다. 대사·책·인터페이스의 번역 데이터는 각 모드의 한국어 패치에서 별도로 제공합니다.
- 게임 EXE, 공식 sfall DLL 및 외부 CJK 원본 파일은 배포하지 않습니다. 이용자가 직접 확보한 파일을 사용합니다.
- 원본 Steam 설치 경로는 보호 대상이므로 **게임 복사본**에 설치하세요.
- 공식 sfall은 중국어·일본어 수정 EXE에서도 `[Debugging] ExtraCRC`를 사용합니다. 한국어판 역시 **필요한 CRC만 자동 추가**하며 기존 항목·주석·줄바꿈·모드 설정을 보존하고 수정되는 파일을 백업합니다. 설치 전에 변경 여부를 보여 주고 확인받습니다. 이미 등록된 경우에는 `ddraw.ini`를 변경하지 않습니다. **HiResMode 변경이 필요한 일부 프로필**은 고급 설정에서 별도 허용해야 합니다. sfall이 없는 순정판은 `ddraw.ini`를 생성하지 않습니다.
- **주의:** sfall 없는 실제 게임 구동은 별도로 확인해야 합니다. 정식 v1.0.0과 베타 v1.1.0-beta.1에는 자동 CRC 등록 개선이 아직 포함되지 않습니다. 새 동작은 v1.1.0-beta.2 개발 브랜치에서 검증 중입니다.
- 오류가 나면 [Issues](https://github.com/munument1/Fallout2-Korean-Text-Engine/issues)에 게임 버전과 오류 메시지를 남겨 주세요.

## 개발자용 자료

[sfall 분리 구조](docs/SFALL_INDEPENDENCE.md) · [고급 설치·구조 설명](docs/TECHNICAL.md) · [게임별 검증 기록](docs/validation.json) · [테스트 안내](docs/TESTING.md) · [개발자용 ZIP](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/latest)

새 출력 어댑터 및 설치 도구는 MIT, Galmuri 글꼴은 OFL 라이선스를 따릅니다.
