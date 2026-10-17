# Fallout 2 독립형 한국어 엔진: 게임 종류 없는 구조 검사 설치기

2026-10-17 | 개발 브랜치 feature/native-structural-autodetect

## 정식판 지원 범위 변경 (2026-10-18)

**Fallout 1.5 Resurrection은 범용 독립형 설치기 지원 대상에서 제외한다.**
Resurrection 1.5는 구형 sfall과 독자적인 고해상도 패치를 사용하므로, 자체 EXE 섹션을
추가하는 설치기는 구형 sfall의 크기 검사와 충돌한다. 최신 공식 sfall로 바꾸더라도
고해상도 설정 수정 및 장시간 호환성 재검증이 필요하다. 원본 모드의 장기 업데이트가
종료된 상황에서는 기존 배포를 유지하는 편이 안전하다.

사용자는 [Resurrection KR1.1 기존 정식 한글 패치](https://github.com/munument1/Fallout-1.5-Resurrection-KR/releases/tag/Resurrection-V1.5-KR1.1)를 이용한다.
이후 독립형 설치기는 Resurrection 고유의 `fores.exe`, `fores.cfg`, 확장자 없는
`FALLOUT2`가 함께 있으면 **아무 파일도 변경하기 전에 명시적으로 거부**한다.
기존 beta.2 실험 기록은 역사적 검증 결과로 보존하고, 아래 표의 호환성 검증은
향후 정식판의 지원 약속으로 해석하지 않는다. 과거 독립형 엔진 설치를 한 경우
기존 설치기의 복구 기능은 계속 이용할 수 있다.

## 목표

게임 이름·모드 버전·EXE 전체 SHA-256 목록을 수동으로 갱신하지 않고
현재 실행 파일의 내부 구조를 검사해 독립형 한글 엔진을 적용한다.
사용자는 **게임 폴더 한 개만 선택**하면 된다.

## 적용 원리

1. 게임 폴더의 .exe 또는 확장자 없는 PE 파일 중 Watcom 기반 Fallout 2 실행 파일을 탐색한다. Resurrection은 `fores.exe` 런처를 보존하고 실제 엔진 파일 `FALLOUT2`만 검사한다.
2. Win32 PE 핵심 섹션 매핑, 원래 후킹 명령어, Windows DLL import,
   폰트 콜백 관리자, 줄바꿈 및 호출 ABI의 여섯 부분 SHA-256 지문을 검사한다.
3. 이 지문이 호환되면 **EXE 전체 SHA-256이 바뀌어도** 설치 가능하다.
   번역 데이터, 리소스, 후킹 ABI와 관계없는 코드 수정은 허용된다.
4. Nevada처럼 기존 리소스 섹션이 커진 EXE의 경우 자체 .krinit 섹션을
   기존 섹션 뒤쪽으로 옮기고 로더 주소도 자동 계산한다.
5. 호환되는 EXE가 여러 개 발견되면 모두 개별 백업·패치한다.
   기존 HRP 및 sfall DLL과 게임 설정은 불필요하게 교체하지 않는다.
   한국어 MSG 번역 데이터가 설치되지 않았다면 게임 설정을 억지로
   language=korean으로 바꾸지 않는다.
6. 어느 EXE에서든 핵심 ABI가 바뀌었다면 전체 설치를 거부한다.

이 방법은 **아무런 제약 없이 모든 업데이트에 대응한다는 뜻은 아니다.**
Fallout 2의 폰트 ABI와 메모리 매핑을 유지하는 업데이트에 대응하는
방식이며, 해당 엔진 자체가 바뀌면 별도의 분석·구현이 필요하다.

## 사용자 보유 파일 대상 시험

| 폴더 | 자동 검사·복사본 설치·원복 | 실게임 결과 |
| --- | --- | --- |
| RPU | 두 EXE 성공 | 고해상도 한국어 메인 메뉴 정상 확인 |
| Et Tu | 두 EXE 성공 | 원본에서도 HRP와 sfall 고해상도 설정 충돌 발생 |
| Sonora | 한 EXE 성공 | 번역 미설치 시 기존 언어 설정 유지, 게임 창 확인 |
| Nevada | 두 EXE 성공 | 기존 4.3.0.2 Extended sfall 보존, 도입 화면 진입 |
| Resurrection 1.5 실제 설치본 | 확장자 없는 `FALLOUT2` 한 개 호환 | `fores.exe` 보존; 구형 sfall 3.7.4에서 EXE 크기 거부, 4.5.1 + `HiResMode=0`에서 게임 창 진입 |
| Olympus 2207 | 세 EXE 성공 | 4.2.6 Extended sfall 유지, `olympus.cfg` 자동 선택, 특수 ExtraCRC 보존·도입 화면 진입 |

2026-10-17 추가 실증: 사용자가 업데이트 완료를 확인하고 직접 수정을 허용한
`D:\Fallout 2\olrmpus`, `Nevada`, `Resurrection`, `Sonora` 네 설치본에
독립형 엔진을 적용했다. 먼저 별도 **전체 게임 복사본**에서 설치·약 12초 기동·해시
원상복구 시험을 각각 통과했고, 사용자 설치본에도 다시 적용한 뒤 별도로
약 8초간 게임 창·도입 화면을 확인했다. 원본 파일 사전 SHA와 별도 안전 백업은
작업 디렉터리 `build/owner-original-safety-20261017` 아래 `safety_manifest.json`과
개별 폴더에 보관했다. 설치기 내 복구용 `korean_engine_backup_v2`도 각 게임 폴더에 있다.
사용자의 Et Tu·RPU 설치본은 수정하지 않았으며 설치 전·후 대표 EXE/DLL
SHA-256 동일성을 확인했다.

이 기동 시험은 **한국어 전체 대화·전투·저장·로드·모드 전용 스크립트의
장시간 검증이 아니다**. Nevada와 Sonora는 기존 한국어 MSG 텍스트가 없어
별도 번역 파일을 마련하기 전에는 영어 언어 설정을 유지한다.

추가 수정: 위의 `D:\Fallout 2\Resurrection` 상위 폴더는 실제 Resurrection
게임 폴더가 아니라 원본 Fallout 2 자료가 있는 폴더였음을 후속 조사로 확인했다.
해당 상위 폴더에 적용한 한국어 엔진 및 교체 sfall은 SHA-256을 대조해 원상복구했다.
**실제 Resurrection 1.5 게임은 `D:\Fallout 2\Resurrection\Resurrection`에 있다.**
별도 `fores.exe` 런처, 원본 확장자 없는 `FALLOUT2` 1.02d PE,
`fores.cfg`, 모드 전용 `fores.dat`가 존재한다.
beta.2는 .exe 확장자 여부가 아니라 Watcom PE 구조를 기준으로 엔진 파일을
검사하므로 `FALLOUT2`만 패치하고 `fores.exe`는 보존한다.
검증한 복사본에서 번역 629개와 엔진 설치 후 기존 sfall 3.7.4는
`Expected 0x122800 but got 0x123800` 오류를 표시했다.
공식 sfall 4.5.1로만 바꾸면 중복 고해상도 패치 충돌 경고가 발생했으나,
`ddraw.ini`의 `[Main] HiResMode=0`까지 설정하자 16초 이상 게임 창이 유지됐다.
실제 게임 폴더에도 동일한 구성으로 적용하고 번역/엔진 해시를 확인했다.
전체화면 캡처는 검은 화면이므로 **한국어 메뉴까지 확인됐다고 주장하지 않는다.**
별도 복구용 기존 sfall DLL·INI는 작업 폴더에 보관했다.

## 후속 주의

- Fallout 2 CE처럼 Watcom 엔진 자체가 다른 실행 파일은 별도 지원이 필요하다.
- 게임 시작·메뉴 확인은 긴 대화·스크롤·전체 전투 회귀 검증과 같지 않다.
- 기존 Olympus·Nevada의 Extended sfall DLL을 공식 4.5.1로 단순 교체하면
  `sfall: Conflict of High Resolution patches` 경고가 재현된다. 따라서 유지한다.
- Resurrection에 포함된 sfall 3.2a는 새 .krinit 삽입으로 EXE 파일 크기가
  `0x122800`에서 `0x123800`으로 증가하면 시작 단계에서 오류를 출력한다.
  단순 ExtraCRC 등록과 SkipSizeCheck=1 추가만으로는 통과하지 않았다.
  **설치기 자체는 구형 DLL을 임의 교체하지 않고 안전하게 거절한다.** 이번 사용자
  설치본은 명시적 수정 허용에 따라 기존 `ddraw.dll`을 안전 백업에 보존한 뒤
  별도로 확인한 공식 sfall 4.5.1로 교체했다. 이 교체는 **설치기 `--restore`로
  자동 복구되지 않으므로**, 완전 원복 시 안전 백업의 원래 `ddraw.dll`도 복사해야 한다.
- Olympus는 `fallout2.cfg`와 `olympus.cfg`가 공존한다. 기존 sfall의 활성
  `[Misc] ConfigFile=olympus.cfg`를 안전하게 확인해 올바른 CFG만 수정한다.
  `ExtraCRC`에 기록된 기존 원본 EXE 크기 숫자도 제거/재해석하지 않는다.
- 반복 설치/복구 시 이전 복구 기록을 지우지 않고
  `korean_engine_backup_v2_restored_2`, `_3`과 같은 고유 이름으로 보존한다.
- 게임 실행 후 설정 파일이 자체적으로 달라지면 설치기 복구 해시 검사에서
  오류가 발생할 수 있으며, 이때는 강제 덮어쓰지 않고 확인이 필요하다.
- 기존 정식판 및 알파5·알파6·알파7·알파8을 보존한다. 알파8은 Olympus
  확장 sfall 특수 설정 대응과 다중 CFG 자동 선택, 알파9는 구형 순정 전용
  설치기 도움말을 실제 범용 설치·복구 동작에 맞춘 후속 시험판이다.
