# 폴아웃 2 완전 독립형 한글 엔진 — 개발 현황

이 연구 브랜치는 기존 v1.1.0-beta.2 릴리즈를 변경하지 않습니다.

## 목표

게임 폴더와 한국어 번역 자료만 선택하면 설치되도록 중국어 CJK 원본 폴더와 레거시 폰트 DLL 의존성을 제거합니다. 기존 모드의 공식 sfall 설정은 보존합니다.

## 이번 구현

- src/font_standalone.cpp: 중국어 DLL을 로드하지 않는 새 x86 한국어 렌더러입니다.
- InitFont, ClearFont, SelectFont, GetTextWidth, GetTextHeight, TextOutput, TextOutputL, TextOutputX, SplitText 등 기존 9개 ABI 함수를 자체 구현했습니다.
- CP949→Unicode, 갈무리 글리프 너비 측정, GDI 래스터화, 팔레트 색 매핑, 여러 행 줄바꿈, 실측 글자 높이 기반 줄 간격을 처리합니다.
- 기존 중국어 DLL 로드나 함수 포인터 참조가 없습니다.
- tests/font_standalone_probe.cpp: 레거시 DLL 없이 모든 현대 한글 11,172자, 두 글꼴, 줄바꿈, 픽셀 출력, 원문 보존, 버퍼 가드 및 API를 검사합니다.
- Windows x86 빌드와 독립 프로브를 통과했습니다. 기존 CJK 기반 시험 EXE + 공식 sfall 4.5.1의 별도 게임 복사본에서 레거시 DLL 없이 게임 초기화·메인 창 생성을 확인했습니다. 모든 화면/플레이 검증은 미완료입니다.

## 아직 해결되지 않은 핵심 의존성

중국어 수정 EXE가 여전히 필요합니다. 원본 Fallout 2 US 1.02d EXE 대비 CJK EXE에는 새 코드 섹션과 약 37군데의 기존 코드 변경이 있으며, 이 코드가 폰트 DLL 로딩과 여러 게임 출력 경로를 연결합니다.

현재 설치기의 tools/runtime.py는 사용자가 제공한 CJK EXE를 검증해 이를 기반으로 한국어 EXE를 생성합니다. 새로운 폰트 DLL만으로 순정 EXE가 자동으로 한글을 지원하지는 않습니다.

## 설치 편의성 시험 기능

- 실험용 설치기는 게임 폴더 하나를 선택한 뒤, 명시적으로 동의하면 NovaRain의 공개 GitHub 저장소에서 CJK EXE 한 파일만 임시 다운로드합니다.
- SHA-256을 기존 검증된 원본 CJK EXE 값에 고정하여, 원본이 바뀌거나 비정상 파일이 수신되면 게임 폴더를 수정하기 전에 거부합니다.
- 자체 제작 한글 DLL은 패키지에 포함되므로 기존 중국어 폰트 DLL 파일 및 CJK 원본 폴더를 별도로 선택할 필요가 없습니다.
- 다운로드한 EXE는 임시 폴더에서 파생 EXE를 생성하는 데 사용하고 삭제합니다. 중국어 게임 EXE 자체를 배포 패키지에 넣지는 않습니다.
- **최종 설치된 게임 EXE에는 아직 CJK 패치 코드가 포함되어 있습니다.** 따라서 사용자 인터페이스에서 폴더 선택이 사라진 것과 엔진이 CJK 코드로부터 독립한 것은 다릅니다.
- 외부 다운로드가 불편하다면 직접 보유한 검증된 원본 CJK EXE 폴더를 선택할 수 있습니다.
- 이 경로는 기능 검증용입니다. 외부 EXE의 라이선스와 최종 패포 적합성을 별도 검토해야 합니다.

### 시험 설치기 검증 결과

- Windows 단일 GUI 설치기(PyInstaller) 빌드 및 내장 --self-test 통과.
- 정확한 순정 EXE, 공식 sfall, 테스트 모드 설정이 들어 있는 **별도 시험 폴더**를 대상으로 임시 CJK EXE 자동 다운로드 → SHA-256 확인 → 새 독립형 DLL 설치 → 복구까지 성공.
- 설치 폴더에서 fallout2font_legacy.dll을 만들지 않았으며, 복구 후 순정 게임 EXE의 원래 SHA-256과 일치함을 확인.
- sfall 설정의 기존 BOM 없는 파일에 잘못된 UTF-8 BOM을 추가하지 않도록 INI 디코딩을 수정하고, 보존 테스트 추가.
- 제공된 기존 통합 테스트 경로 중 Sonora/Nevada/Olympus/Resurrection 등 일부 모드 경로가 현재 로컬 설치와 일치하지 않아 전체 모드 통합 테스트는 미완료. 순정 관련 CRC·sfall 없는 설치 테스트는 통과.

따라서 현재 달성 단계는 **중국어 폰트 DLL 의존 제거 + 원본 CJK 폴더를 수동 선택하지 않는 시험용 설치 흐름**입니다. 중국어 수정 EXE의 추가 코드를 직접 구현하는 최종 단계는 아직 미완료입니다.

## 다음 단계

1. 순정 EXE용 자체 부트스트랩과 출력 함수 훅을 독립적으로 구현합니다.
2. 검증된 실행 파일의 변경만 허용하고 원상 복구 가능한 패치 도구를 구현합니다.
3. 순정·공식 sfall·RPU·Et Tu에서 실제 메뉴/대화/인벤토리/저장 및 불러오기를 확인합니다.
4. 그다음 설치기의 CJK 원본 폴더 선택을 제거합니다. 검증되지 않은 제3자 CJK 코드를 설치 패키지에 복사·배포하지 않습니다.

## 빌드

Windows x86 Visual Studio 개발자 명령 프롬프트에서 다음 명령을 실행합니다. 사전에 build/standalone 폴더를 만듭니다.

    cl /nologo /std:c++17 /EHsc /O2 /MT /LD /utf-8 src\font_standalone.cpp /link /Brepro /DEF:src\font_bridge.def /OUT:build\standalone\fallout2font.dll gdi32.lib user32.lib
    cl /nologo /std:c++17 /EHsc /O2 /MT /utf-8 tests\font_standalone_probe.cpp /Febuild\standalone\font_standalone_probe.exe user32.lib
    build\standalone\font_standalone_probe.exe build\standalone\fallout2font.dll

DLL 옆에 fallout2font.ini와 fonts/Galmuri9.ttf, fonts/Galmuri11.ttf가 필요합니다. 기존 정식 게임 폴더가 아닌 별도 복사본에서만 실험하세요.
