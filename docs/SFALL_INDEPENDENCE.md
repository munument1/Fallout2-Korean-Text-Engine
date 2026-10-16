# sfall과 한국어 출력 엔진의 분리 — ExtraCRC 정책 (v1.1.0-beta.2)

## 공식 sfall의 기존 CJK 규칙을 따른다

sfall의 CJK 수정 EXE도 `[Debugging] ExtraCRC`를 사용한다. 공식 sfall 팀에서 이를 설명했으므로 한국어 EXE의 기본 CRC 화이트리스트 등록 요청보다 이 방식을 우선한다.

- 한국어 글자 출력: 한국어 호환 EXE, `fallout2font.dll` 브리지, 사용자가 별도 확보한 CJK 기존 DLL, Galmuri 폰트.
- sfall: 공식/기존 `ddraw.dll`을 **교체·재빌드하지 않는다**.
- `ExtraCRC`: 기존 `ddraw.ini`의 `[Debugging]` 항목에 **검증된 한국어 EXE CRC만 추가**한다.
- 번역 데이터: 별도 한국어 패치에 포함한다. `TranslationsINI`는 건드리지 않으며 모드별 경로를 보존한다.

참고: [sfall 개발자 답변](https://github.com/munument1/Fallout2-Korean-Text-Engine/pull/6#issuecomment-6210816149).

## 기본 동작

1. 설치 대상 EXE 및 원본 CJK 파일의 SHA-256을 검사해 지원 프로필을 검증한다.
2. 게임에 sfall이 없다면 기존과 같이 `ddraw.dll`, `ddraw.ini`를 새로 생성하지 않는다. sfall 없이 실행되는지는 실제 게임에서 별도 검증해야 한다.
3. 기존 sfall이 있으면 DLL을 그대로 두고 `ddraw.ini`에 필요한 `ExtraCRC`가 있는지 확인한다.
4. 값이 없으면 **기존 CRC 목록 끝에 새로운 한국어 CRC 하나만 덧붙인다.** 기존 줄바꿈, 인코딩, 주석, 다른 옵션, `TranslationsINI`는 그대로 유지한다.
5. GUI는 설치 전에 `ddraw.ini` 수정 여부를 보여 주고, 사용자가 설치를 승인하면 수정 파일을 백업한 뒤 적용한다.
6. 이미 CRC가 존재하면 `ddraw.ini`를 수정하지 않는다. 애매한 중복 `[Debugging]` 또는 잘못된 CRC 목록은 자동 수정을 거부한다.
7. 복구할 때 해당 INI의 원본 바이트를 복구한다. 설치 후 사용자가 파일을 추가 수정했으면 자동 덮어쓰기를 거절한다.

이 작업은 **공식 sfall이 한국어 EXE를 자동 인식한다는 뜻이 아니다.** 프로그램이 `ExtraCRC`를 관리하므로 사용자가 수동 편집하지 않아도 된다는 뜻이다.

## 모드 고유 설정

- 일부 프로필(외부 HRP 중복 등)에 필요한 `HiResMode` 변경은 **별도 고급 옵션**에서만 적용한다. 이는 `ExtraCRC` 자동 등록과 분리한다.
- 모드가 사용하는 sfall 버전을 바꾸지 않는다. 검증된 공식 4.5.1 외의 x86 sfall형 DLL도 기존 파일을 유지하지만 실제 게임 호환 여부는 미확인으로 경고한다.
- 알 수 없는/비정상 `ddraw.dll`, 필수 INI 누락, 미지원 게임 EXE가 감지되면 강제로 설치하지 않는다.
- 설치기에서 번역 패키지의 `.msg`나 화면 자산까지 자동 구성하는 작업은 아직 별도이다.

## 빌드별 CRC32C

| 프로필 | CRC |
| --- | --- |
| Fallout 2 원본, RPU, Et Tu, Resurrection | `0xFCDC75E0` |
| Sonora | `0xFF51969F` |
| Nevada Extended | `0xE5BF456F` |
| Olympus 2207 | `0xE81550F3` |
| Sonora 개발판 | `0xFC345277` |

이 값은 고정된 검증 대상 파일에만 적용된다. 원본 모드 업데이트가 새로운 EXE를 공급하면 해시·CRC를 다시 검증해야 한다.

## 테스트 및 남은 검증

`tests/test_sfall_ini.py`는 게임 바이너리 없이 CP949/UTF-8 BOM, CRLF, 기존 CJK CRC, 주석 보존, 중복 입력과 복구 관련 정책을 확인한다. 원본 게임 EXE, CJK DLL, 모드 바이너리를 이용한 설치·복구 통합 검사는 `KOREAN_ENGINE_TEST_INPUTS`를 지정한 개인 PC에서 수행해야 한다.

**GitHub Actions 성공은 실제 게임 플레이를 검증한 것이 아니다.** 순정 Fallout 2 + 공식 sfall → RPU → Et Tu → 기타 모드 순서로 메뉴, 대화, 인벤토리, 전투 메시지, 저장/불러오기, 게임 종료·재실행, 원상 복구를 확인해야 한다.
