# Fallout 2 한국어 출력 엔진

## 독립형 한국어 엔진 — 새 설치 방식 (v1.2.0-beta.2)

**[중국어 실행 파일이 필요 없는 Windows 설치기 다운로드](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/tag/v1.2.0-beta.2)**

사용자가 게임 폴더를 하나 선택하면 호환되는 Fallout 2 계열 실행 파일의 **Watcom ABI·PE 구조를 자동 검사**해 한국어 출력 기능을 설치합니다. 게임 종류·중국어 CJK EXE·글꼴 DLL 입력을 요구하지 않으며, EXE 전체 해시만 다른 호환 업데이트도 처리할 수 있습니다. ABI 자체가 바뀐 실행 파일은 안전하게 거부합니다.

설치 순서는 **게임 버전과 일치하는 한국어 번역 ZIP을 먼저 적용 → 독립형 설치기 실행 → 기존 게임 런처 실행**입니다. 수정 대상 원본 파일만 복구용으로 보관하고 게임 전체 복사본을 강제로 생성하지 않습니다.

현재 번역 ZIP: [Nevada](https://github.com/munument1/Fallout2-Nevada-KR/releases/tag/v2026.10.17-native-beta.1) ·
[Olympus 2207](https://github.com/munument1/Fallout2-Olympus2207-KR/releases/tag/v2026.10.17-native-beta.1) ·
[Resurrection 1.5](https://github.com/munument1/Fallout-1.5-Resurrection-KR/releases/tag/v2026.10.17-native-beta.2) ·
[Sonora 1.16.4/DLC 공통 번역](https://github.com/munument1/Fallout2-Sonora-KR/releases/tag/v1.16.4-native-beta.2).
[Et Tu 2.0.3911](https://github.com/munument1/Fallout2-EtTu-KR/releases/tag/v2.0.3911-native-beta.2) ?
[RPU 2.4.34](https://github.com/munument1/Fallout2-RPU-KR/releases/tag/v2.4.34-native-beta.2).
Sonora `eng_repack` 개발본은 [별도 자료](https://github.com/munument1/Fallout2-Sonora-KR/releases/tag/v2026.10.17-native-beta.1)입니다. Et Tu와 RPU의 원본 업데이트는 아직 진행 중입니다.

**아직 공개 베타입니다.** 한국어 메뉴·짧은 기동과 파일 해시 검증은 진행했지만 모든 모드의 장시간 대화·전투·저장/불러오기를 전수 검증하지 않았습니다. 기존 모드 전용 sfall(특히 Nevada/Olympus Extended)을 일반판으로 무조건 교체하지 마세요. Resurrection은 확장자 없는 `FALLOUT2`가 실제 엔진이고 `fores.exe`는 별도 런처이며, 기존 구형 sfall과 고해상도 패치의 호환 설정이 필요합니다.

---

## 기존 CJK 기반 v1.0.0 (이전 설치 방식)

아래 v1.0.0은 GitHub에서 프리릴리즈로 표시된 **중국어판 파일을 사용자가 준비해야 하는 이전 설치 방식**입니다. 위의 독립형 베타 2와 설치 방법이 다르며, 독립형 엔진을 사용하려면 이 이전 설치기를 내려받지 마세요.

클래식 **Fallout 2와 호환 모드에서 한글을 표시해 주는 프로그램**입니다. 한국어 글꼴과 줄바꿈을 지원하며, 기존 파일은 설치할 때 백업합니다.

### 이전 방식 다운로드

**[이전 방식 Windows 설치기 다운로드 (.exe)](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/download/v1.0.0/Fallout2-Korean-Text-Engine-Setup.exe)**

Python이나 명령어 입력 없이 실행할 수 있습니다.

### 이전 CJK 방식 설치 방법

1. **게임 준비:** Fallout 2 또는 지원 모드를 별도 폴더에 준비하고 [공식 sfall 4.5.1](https://github.com/sfall-team/sfall/releases/tag/v4.5.1)을 적용합니다.
2. **설치기 실행:** 게임 폴더와 직접 확보한 **FO2_UPU_CHT_v34의 CJK 파일 폴더**를 선택합니다.
3. **「설치하기」 클릭:** 파일을 자동 검사하고 설치합니다. 설치 후 **게임별 한국어 번역 패치**를 별도로 적용하면 됩니다.

CJK 원본 폴더에는 해당 패키지의 \`Fallout2.exe\`와 \`fallout2font.dll\`이 함께 있어야 합니다. Sonora·Nevada·Olympus 같은 모드에서는 원본 Fallout 2 US 1.02d 실행 파일을 추가로 선택하라는 안내가 나타날 수 있습니다.

**설치 전 상태로 되돌리기:** 설치기에서 같은 게임 폴더를 선택한 후 **「설치 전 상태로 복구」**를 누르세요. 게임별 번역 패치로 별도 설치한 파일은 복구 대상이 아닙니다.

## 지원 게임

Fallout 2 원본 / Restoration Project Updated / Fallout Et Tu / Fallout Sonora / Fallout Nevada Extended / Olympus 2207 / Fallout 1.5 Resurrection

지원은 **검증된 게임·모드 버전**에 한합니다. 다른 버전의 실행 파일은 안전을 위해 패치를 거부합니다. 자세한 버전별 정보는 [기술 문서](docs/TECHNICAL.md)를 확인하세요.

## 알아두기

- 이 프로그램은 **한국어 출력 엔진**입니다. 대사·책·인터페이스의 번역 데이터는 각 모드의 한국어 패치에서 별도로 제공합니다.
- 게임 EXE, 공식 sfall DLL 및 외부 CJK 원본 파일은 배포하지 않습니다. 이용자가 직접 확보한 파일을 사용합니다.
- 원본 Steam 설치 경로는 보호 대상이므로 **게임 복사본**에 설치하세요.
- 오류가 나면 [Issues](https://github.com/munument1/Fallout2-Korean-Text-Engine/issues)에 게임 버전과 오류 메시지를 남겨 주세요.

## 개발자용 자료

[고급 설치·구조 설명](docs/TECHNICAL.md) · [게임별 검증 기록](docs/validation.json) · [테스트 안내](docs/TESTING.md) · [이전 CJK 방식 개발자용 ZIP](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases/download/v1.0.0/korean-text-engine.zip)

새 출력 어댑터 및 설치 도구는 MIT, Galmuri 글꼴은 OFL 라이선스를 따릅니다.
