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

따라서 현재 달성 단계는 **기존 중국어 폰트 DLL 제거 시험판**이며 **CJK 원본 폴더 없이 설치하는 최종 목표는 아직 미완료**입니다.

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
