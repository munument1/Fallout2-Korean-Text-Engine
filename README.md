# Fallout 2 한국어 출력 엔진

> **개발 중인 독립형 실험판:** 중국어 CJK EXE·폰트 DLL 없이 한글 엔진을 설치합니다. 새 실험 브랜치는 **게임 종류를 선택하지 않고 폴더 안의 실제 게임 실행 파일 구조를 검증**합니다. 폰트 ABI가 유지되는 모드 업데이트라면 전체 EXE 해시가 바뀌어도 적용할 수 있습니다. 핵심 엔진이 바뀌면 안전하게 거부합니다. [구조 검사 설치기 및 모드 실증](docs/UNIVERSAL_STRUCTURAL_INSTALLER_KO.md) · [독립형 엔진 진행 상황](docs/NATIVE_EXECUTABLE_PROGRESS_KO.md). 아래 기존 정식 설치 방식과는 별개입니다.

클래식 **Fallout 2와 호환 모드에서 한글을 표시해 주는 프로그램**입니다. 한국어 글꼴과 줄바꿈을 지원하며, 기존 파일은 설치할 때 백업합니다.

## 독립형 범용 공개 베타 (v1.2.0-beta.1)

**[독립형 Windows 설치기 다운로드 (공개 베타)](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/tag/v1.2.0-beta.1)**

중국어 수정 EXE·DLL이나 게임 종류 선택이 필요 없습니다. 위 시험판 설치기를 실행하고 **게임/모드 복사본 폴더만 지정**하면, 기존 Fallout 2 실행 파일들의 내부 엔진 구조를 검사해 호환되는 파일을 함께 백업·패치합니다. 글꼴 엔진만으로 게임의 영문 MSG가 자동 번역되는 것은 아닙니다.

모드 업데이트로 EXE 전체 해시가 바뀌더라도 핵심 Watcom ABI가 같으면 적용할 수 있지만, **모든 업데이트를 보장하지는 않습니다.** RPU·Et Tu·Sonora·Nevada·Olympus 2207 복사본의 구조 호환성을 확인했습니다. alpha.8부터 Olympus의 다중 CFG 파일 및 Extended sfall 특수 CRC 형식을 보존하며, alpha.9는 오래된 순정 전용 안내문을 범용 설치 방식에 맞게 수정했습니다. Resurrection은 구형 sfall 3.2a의 크기 검사 때문에 **별도 최신 sfall 호환성 검토가 필요**합니다. 오래된 DLL을 설치기가 멋대로 교체하지 않습니다. 같은 복사본에서 설치·복구를 반복해도 과거 백업 기록을 보존합니다. 자세한 적용 범위는 [범용 설치기 검증 기록](docs/UNIVERSAL_STRUCTURAL_INSTALLER_KO.md)을 확인하세요.

베타에서는 복잡한 게임 종류 선택과 사용하지 않는 네이티브 모드 고급 설정을 숨겼습니다. **전체 게임 복사본을 자동 생성하지 않고** 수정되는 파일 원본만 `korean_engine_backup_v2`에 보관해 되돌릴 수 있습니다. EXE 자체를 패치하므로 최소한의 복구 사본은 안전을 위해 유지합니다. 메뉴·기동을 검증했지만 긴 대화·전투·저장/불러오기 전수 검증을 끝낸 **정식판은 아닙니다.**

## 기존 CJK 기반 안정판 다운로드

**[Windows 설치기 다운로드 (.exe)](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/latest/download/Fallout2-Korean-Text-Engine-Setup.exe)**

Python이나 명령어 입력 없이 실행할 수 있습니다.

## 기존 CJK 기반 설치 방법

1. **게임 준비:** Fallout 2 또는 지원 모드를 별도 폴더에 준비합니다. **순정 Fallout 2에서 sfall 없이 설치하는 구성은 지원 대상으로 추가했으며 실제 실행 검증은 아직 필요합니다.** 모드에 sfall이 포함되어 있다면 기존 파일을 그대로 둡니다.
2. **설치기 실행:** 게임 폴더와 직접 확보한 **FO2_UPU_CHT_v34의 CJK 파일 폴더**를 선택합니다.
3. **「설치하기」 클릭:** 파일을 자동 검사하고 설치합니다. 기존 sfall을 유지하고, 필요한 경우 `ExtraCRC` 값만 자동 추가합니다(설치 전 확인·백업). 모드별 별도 HRP 수정이 필요한 경우에는 고급 설정을 요청합니다. 설치 후 **게임별 한국어 번역 패치**를 별도로 적용하면 됩니다.

CJK 원본 폴더에는 해당 패키지의 `Fallout2.exe`와 `fallout2font.dll`이 함께 있어야 합니다. Sonora·Nevada·Olympus 같은 모드에서는 원본 Fallout 2 US 1.02d 실행 파일을 추가로 선택하라는 안내가 나타날 수 있습니다.

**설치 전 상태로 되돌리기:** 설치기에서 같은 게임 폴더를 선택한 후 **「설치 전 상태로 복구」**를 누르세요. 게임별 번역 패치로 별도 설치한 파일은 복구 대상이 아닙니다.

## 기존 CJK 방식 지원 게임

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
