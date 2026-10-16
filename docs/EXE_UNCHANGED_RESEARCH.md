# 원본 EXE 무변경 한국어 출력 엔진 연구

## 목표

한국어 번역을 **sfall과 별개의 런타임 기능**으로 제공하면서 아래 세 파일을 수정하지 않는 방식이다.

- 게임 실행 파일: `fallout2.exe` 및 각 모드 전용 EXE
- 기존 sfall: `ddraw.dll`
- 기존 sfall 설정: `ddraw.ini`

게임 자체가 사용하는 `fallout2.cfg` (또는 모드별 `*.cfg`)의 `[system] language=korean` 선택은 언어팩의 일반적인 작동 방식으로 남긴다. 번역 데이터 역시 별도로 설치한다.

## 현재 코드가 왜 이 조건을 충족하지 못하나?

기존 엔진은 중국어판의 수정 EXE에서 한국어용 실행 코드를 생성한다. 결과적으로 게임 파일이 바뀌고, sfall에선 변경된 EXE를 별도 CRC로 인식할 수 있다. `ExtraCRC`를 수동으로 제거해도 **수정 EXE와 기존 sfall의 호환성이 자동으로 보장되지 않는다.**

기존 한국어 sfall 포크 `Fallout2-sfall-KR`는 디스크 EXE를 바꾸지 않고 **메모리 패치**를 수행한다. 그러나 이 방식은 `ddraw.dll` 자체를 교체하므로 목표와 다르다. 그 폰트 관련 구현은 훅 지점 조사 자료로만 참고한다.

## 가능한 경로와 판단

| 방식 | EXE 변경 | sfall DLL 변경 | 현 시점 판단 |
| --- | --- | --- | --- |
| 기존 CJK 실행 파일 치환 | 예 | 아니요 | 현재 정식 구현, CRC 호환성 문제 |
| 한국어 sfall 포크 설치 | 아니요 | 예 | 기존 기술 참고, 목표 불충족 |
| 별도 런타임 로더 + 메모리 훅 | 아니요 | 아니요 | **연구 대상**. 훅·주입 시점 미확인 |
| 게임 원본 엔진의 번역 파일만 교체 | 아니요 | 아니요 | 글꼴·문자폭·인코딩 문제 미해결 |

추가 DLL을 복사하는 것만으로 게임이 해당 DLL을 로드하는 건 아니다. 원본 EXE가 어떤 DLL을 **정적으로 import**하는지 조사하고, 로더 초기화 시점·훅 충돌·문자폭 계산을 검증해야 한다.

## 역사적 한국어 폰트 훅 6곳

기존 `Fallout2-sfall-KR`의 `KoreanText.cpp`는 `MakeJump`로 게임 내부의 여섯 함수 진입점을 가로챈다. 이에 대응하는 함수 주소는 `FunctionOffsets_def.h`에서 확인했다.

| 원본 함수 이름 | VA (US 1.02d 기준) | 역할 |
| --- | --- | --- |
| `FMtext_height_` | `0x442168` | 폰트 높이 |
| `FMtext_width_` | `0x442188` | 문자열 폭 |
| `FMtext_to_buf_` | `0x4422B4` | 글자 출력 |
| `GNW_text_height_` | `0x4D5B54` | GUI 폰트 높이 |
| `GNW_text_width_` | `0x4D5B60` | GUI 문자열 폭 |
| `GNW_text_to_buf_` | `0x4D59B0` | GUI 글자 출력 |

새 검사 도구는 이 여섯 주소가 **원본 EXE에서 실행 가능한 섹션에 들어가는지** 보고한다. 그러나 이것만으로 실제 바이너리 훅이 안전하다고 볼 수 없다. **프로로그·명령어 경계·호출 규약·sfall 훅 충돌 검증**을 별도로 해야 한다.

기존 sfall 구현에는 Watcom 게임 엔진 호출 규약을 맞추기 위한 MSVC x86 어셈블리 어댑터가 포함돼 있다. 로더를 독립 구현할 경우 이 호출 규약을 만족하는 별도 연결 코드가 필요하며, 원본 sfall 소스를 MIT 프로젝트에 단순 복사하지 않는다.
## 이번 브랜치에 추가한 검사 도구

`tools/probe_runtime_loading.py`는 사용자가 별도로 보유한 EXE를 **읽기 전용**으로 조사한다. 원본 게임 파일이나 DLL을 수정하지 않고, 게임을 실행하지도 않는다.

필요한 입력:

- 미국판 Fallout 2 1.02d `fallout2.exe`
- 검증된 `FO2_UPU_CHT_v34`의 CJK `Fallout2.exe`
- (선택) 해당 모드의 원본 EXE

두 필수 EXE의 SHA-256을 저장소 manifest와 비교한다. 결과는 import DLL/함수 이름, PE 섹션 매핑, 변경 바이트의 위치와 개수만 표시하며 **저작권 있는 실행 코드 내용은 출력하지 않는다**.

실행 예시:

```powershell
python tools/probe_runtime_loading.py --original "D:\\Original\\fallout2.exe" --cjk "D:\\CJK\\Fallout2.exe"
```

추가 모드 EXE를 보려면 `--mod "D:\\Games\\Nevada\\Nevada.exe"`를 지정한다. JSON 보관은 `--output`으로 지정할 수 있지만 분석 결과는 원본 EXE 폴더 외부에 둔다.

## 필수 검증 순서

1. 실제 원본/CJK EXE로 import 및 PE 차이를 조사한다. **현재 자료만으로 특정 우회 로딩 DLL의 호환성을 단정하지 않는다.**
2. 메모리 훅 진입점과 CP949 처리 경로를 매핑한다. 게임 버전·모드별로 바뀌는 주소에 대한 안전 검증이 필요하다.
3. 독립 로더 프로토타입은 먼저 **게임 파일 및 sfall 미변경**을 해시로 증명한 뒤 비번역 상태의 시작 화면을 검사한다.
4. 한국어 글꼴의 출력뿐 아니라 문자열 폭, CR/LF, 버튼 크기, UI 잔상, 로그 및 메뉴 레이아웃을 검사한다.
5. sfall 있는 모드에서 충돌 여부를 검사한다. sfall의 로더와 메모리 패치 순서가 특히 중요하다.
6. 복구·실패 처리·원래 게임 실행 경로·멀티 모드 호환성을 실게임에서 검증한다.

**연구 브랜치와 PR은 배포판이 아니다.** 현재 정식 v1.0.0은 종전 CJK 수정 EXE 기반이며, 원본 EXE 무변경 구현이 되었다고 표기하면 안 된다.

## 참고 코드

- [현재 엔진의 CJK 실행 파일 패처](../tools/runtime.py)
- [기존 sfall 독립화 PR](https://github.com/munument1/Fallout2-Korean-Text-Engine/pull/4)
- [한국어 sfall 포크 (이전 기술)](https://github.com/munument1/Fallout2-sfall-KR)
- [원작 sfall](https://github.com/sfall-team/sfall)
