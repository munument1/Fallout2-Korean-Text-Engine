# 순정 EXE 직접 패치 방식 — 자체 한국어 엔진 v1.2 실험

**상태:** 중국어 CJK EXE·중국어 폰트 DLL·외부 다운로드가 필요 없는 **순정 US 1.02d 전용 연구 구현**. 전체 게임·모드 검증 전이므로 일반 사용자 대상 정식 배포가 아닙니다.

## 이전 버전과 달라진 구조

| 구성 | 기존 v1.2.0-alpha.1 | 이번 native 실험 |
| --- | --- | --- |
| 글꼴 DLL | 자체 구현 | 자체 구현 + 게임 호출 규약 훅 |
| 게임 EXE 코드 | 중국어 수정 EXE의 패치를 활용 | **순정 Fallout 2 EXE에서 독자적으로 생성** |
| 중국어 원본 폴더 | 수동 선택 또는 자동 다운로드 | **필요 없음** |
| 외부 EXE 다운로드 | 기본값으로 진행 | **진행하지 않음** |
| sfall | 있으면 설정에 CRC 자동 추가 | 동일, 공식 DLL 교체 없음 |
| 지원 대상 | 기존 지정 프로필(완전한 실게임 검증 전) | **현재는 순정 US 1.02d만 허용** |

## 새로 만든 코드

- tools/native_pe.py: 원본 SHA-256이 일치하는 순정 US 1.02d에 새로운 PE 섹션 .krinit을 만들고, 게임 실행 중 한 번 기존 Windows API 호출 지점에서 자체 한글 DLL을 로드합니다.
- src/native_font_hooks.cpp: 기존 Watcom 컴파일러의 EAX/EDX/EBX/ECX 기반 호출 규약을 자체 x86 어셈블리 중계 함수로 연결하고, 폰트 100~110 관리자의 출력·높이·너비·선택 함수와 런타임 등록 복사본을 교체합니다.
- src/font_standalone.cpp: 이미 자체 구현된 CP949 글리프, GDI 출력, 텍스트 폭·높이·색 처리 활용.
- tools/install_engine.py: --native-exe와 --standalone-font를 함께 사용하면 donor 없이 자체 PE 수정·DLL 설치·sfall ExtraCRC 추가·원상 복구까지 수행.
- tools/gui_installer.py: InitKoreanEngine export가 포함된 자체 DLL을 번들로 제공하는 경우 순정판만 선택할 수 있고 외부 CJK 다운로드 화면 자체를 표시하지 않습니다.

게임 EXE에 복사되는 코드는 자체 작성한 초기화 바이트 코드이며 기존 CJK 실행 파일의 추가 섹션을 복사하지 않습니다. sfall의 versionCHI 판별을 위한 호환 점프 변위는 유지하지만, 대상 코드는 완전히 다릅니다.

## 실제 확인

1. 32비트 DLL 컴파일 및 글꼴 2종, 한글 11,172자 처리 자동 프로브 성공.
2. 순정 US 1.02d EXE에서 직접 생성한 새 게임 EXE PE 구조·자체 초기화 코드 검사 성공.
3. 공식 sfall 4.5.1과 함께 게임 창, Fallout 2 메인 메뉴, **캐릭터 선택 및 캐릭터 생성 화면** 실행 성공.
4. 실제 게임 프로세스 메모리에서 gModernFontManager와 등록 복사본의 함수 포인터들이 우리 자체 DLL 함수 주소로 변경된 것 확인.
5. 캐릭터 선택 화면에서 CP949 한글 설명 출력 확인. 캐릭터 생성의 긴 한국어 문자열에서 **줄 겹침·영역 침범 증상**을 발견했으며 해결 전.
6. 자체 설치 CLI로 중국어 파일이 없는 게임 복사본에 설치하고, 기존 sfall DLL 보존과 ExtraCRC 등록(이번 native 빌드: 0xEAC9737C), 백업 및 복구 확인. 복구 뒤 원본 SHA-256 일치.
7. 기존 영어/한글 번역 내용은 사용자 게임 자료에 의존. 레이아웃이나 번역의 완전성을 증명하지는 않음.

## 아직 검증되지 않은 핵심 사항

- 인게임 대화·핍보이·인벤토리·전투 메시지·저장·불러오기 정상 작동 여부.
- 게임 전체의 멀티바이트 문자 경계 처리, 긴 대사 자동 줄바꿈과 다양한 글꼴/폰트 크기의 출력 영역.
- 외부 sfall이 없는 환경 및 구버전 sfall에서의 게임 실행 여부. 이 시험 PC에서는 **수정하지 않은 순정 EXE 자체도 sfall 없이 코드 1로 종료**하므로, 이 환경에서 sfall 없는 독립 엔진 실행은 검증하지 못했습니다.
- RPU/Et Tu/Resurrection/Sonora/Nevada/Olympus: 별도 EXE를 수정하거나 모드 파일을 해치지 않는 훅을 만들고 검증하기 전 **절대 자동 적용하지 않음**.
- 검증되지 않은 게임/모드 버전, 이미 수정된 EXE, 다른 게임 배포판의 EXE는 SHA 검사를 통해 거부.

## 시험 설치

원본 게임 폴더는 수정하지 않고 복사본에만 적용하세요.

    python tools/install_engine.py "D:\Games\Fallout2-Test" --profile stock --native-exe --standalone-font path\to\fallout2font.dll

완전 복구:

    python tools/install_engine.py "D:\Games\Fallout2-Test" --restore

독립형 DLL은 src/font_standalone.cpp + src/native_font_hooks.cpp를 함께 x86으로 컴파일해야 합니다. 공식 sfall은 게임 폴더에 있을 때만 CRC를 등록하고 DLL 파일 자체는 교체하지 않습니다.
