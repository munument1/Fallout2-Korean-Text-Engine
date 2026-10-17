# 한국어 캐릭터 설명 카드 실자료 비교 및 무손실 줄바꿈 검사

작성일: 2026-10-17

## 목적

이전 실험 alpha.3의 캐릭터 설명 12줄 강제 제한은 텍스트 손실을 일으킬 수 있습니다.
기존 한글 번역이 스크롤 없이 표시되던 동작을 되찾는 것이 목표이므로, 시험용
반복 문구가 아닌 실제 소유자가 보유한 번역 데이터를 사용해 비교했습니다.

## 시험 환경

- 기준: CJK_451_LAB/Q_MINIMAL_VANILLA의 기존 CJK 기반 게임 복사본
- 실험: 자체 독립형 EXE + fix/preserve-full-card-description 브랜치에서
  별도로 빌드한 자체 x86 한글 DLL
- 게임: Fallout 2 US 1.02d, sfall 4.5.1, 640×480 DX9
- 양쪽의 영어 메시지 경로에 동일한 실제 CP949 한국어 메시지 파일을
  복사한 후 게임 설정을 language=english로 통일했습니다.
- 원본: CJK_451_LAB/sources/rpu-v28-kor-reference/Data/text/korean/game/
  에 보관된 stat.msg, skill.msg, pro_item.msg, editor.msg, misc.msg
- 원본 메시지 파일 내용은 저장소에 재배포하지 않고 개인 로컬 실험 복사본에만 적용했습니다.

파일 SHA-256:

| 파일 | SHA-256 |
| --- | --- |
| stat.msg | 7fdd82b5fda0… |
| skill.msg | 9c21a86e1d7f69cfec2db0537188c28a1575ded5cd1da13b57b0b28301037bca |
| pro_item.msg | 14070c9fdee7… |
| editor.msg | 5f01f30b2868… |
| misc.msg | 2f87071442bd… |

## 실험에서 확인된 오류 원인

- 예전 캐릭터 생성 화면을 가득 채운 문장은 실제 번역 내용이 아니었습니다.
- 테스트용 skill.msg의 200번 문장만도 약 696바이트로, 같은 번호의 실제
  RPU 한국어 번역 문장은 87바이트입니다.
- 기술 목록만 실제 번역으로 교체했을 때도 화면에는 같은 시험 문구가 남았습니다.
  남아 있던 stat.msg 및 pro_item.msg에도 반복 문구가 들어 있었기 때문입니다.
- 그 후 두 게임 복사본에서 다섯 종류의 메시지 파일을 동일한 실제 번역으로
  교체하고 다시 스크린샷을 촬영했습니다.

## 결과

1. CJK 기반 구형 한글판과 수정된 독립형 엔진 모두 **동일한 Strength(힘)
   설명을 정상 출력**했습니다. 12줄 제한이나 스크롤이 필요한 화면이 아니었습니다.
2. 시험의 두 실행 파일 모두 게임 캐릭터 생성 화면에 정상 진입했습니다.
3. x86 호출 기반 검사 real_translation_wrap_probe.cpp로 skill.msg와 stat.msg에서
   ID 200~239의 **실제 한국어 설명문 55개**를 조사했습니다.
4. 모든 설명문에서 **문자 경계 무결성, 마지막 바이트 보존, 카드 전용 호출과
   일반 줄바꿈의 결과 일치**를 확인했습니다. 오류 0건입니다.
5. 이 55개 설명의 최대 줄 수는 **6줄**, 12줄 초과는 **0건**이었습니다.

두 화면의 개인 로컬 증빙 파일:

- build/reversion/real-comparison/cjk_old-authentic-card.png
- build/reversion/real-comparison/native_full-authentic-card.png

게임 저작물의 스크린샷 및 테스트용 CJK 실행 파일은 소스 저장소에 올리지 않습니다.

## 재현

Windows x86 개발 환경에서 독립형 DLL을 컴파일한 후:

    cl /std:c++17 /EHsc /O2 /MT /utf-8 tests\real_translation_wrap_probe.cpp /Fe:real_translation_wrap_probe.exe
    real_translation_wrap_probe.exe <standalone-font.dll> <owned-RPU-skill.msg> <owned-RPU-stat.msg>

소유자가 합법적으로 보유한 파일 경로를 지정해야 합니다. 이 검사기는 파일 내용
전체를 복사하거나 수정하지 않으며 byte-offset, CP949 유효성만 조사합니다.

## 판단 및 남은 범위

- **12줄로 자르는 코드는 사용하면 안 됩니다.** 실제 번역 파일에서는 제거한
  상태로도 글자 손실이 없었고, 비교한 게임 화면의 표시도 정상입니다.
- 화면 길이를 무조건 늘리거나 별도 F10 팝업·스크롤창을 강제하는 대신,
  기존 카드의 폰트/문장 폭을 유지하는 것이 현 단계의 올바른 기준입니다.
- 이 실험에서 모든 게임 대화·아이템·퀘스트 설명을 검사한 것은 아닙니다.
  실제 화면을 벗어나는 장문은 별도로 조사해야 하며, 설명을 일방적으로
  삭제하는 조치로 해결했다고 주장하면 안 됩니다.
- 아직 실험 브랜치 상태이며, 기존 v1.2.0-alpha.3 릴리즈는 **여전히 12줄
  제한이 있는 구버전**입니다. 검증 후 차기 릴리즈에 이 수정을 반영해야 합니다.
