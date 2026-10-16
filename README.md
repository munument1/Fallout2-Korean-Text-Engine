# Fallout 2 한국어 출력 엔진

클래식 **Fallout 2** 및 호환 모드에서 한국어 글꼴과 줄바꿈을 지원하는 공통 출력 엔진입니다. **게임의 한국어 번역문은 포함하지 않습니다.** 해당 게임/모드의 한국어 번역 패치를 별도로 설치해야 합니다.

> **현재 시험판 준비 중:** 검증된 버전의 파일에만 설치할 수 있습니다. 지원 버전이 다르면 강제로 패치하지 않습니다. 새로운 실행 파일은 실제 게임에서 추가 테스트가 필요합니다.

## 다운로드

**[GitHub Releases에서 최신 시험판 확인](https://github.com/munument1/Fallout2-Korean-Text-Engine/releases)**

- `Fallout2-Korean-Text-Engine-Setup.exe`: Python 없이 실행하는 Windows 설치기 (릴리즈 자산이 게시된 경우)
- `korean-text-engine.zip`: 소스·설치 도구·출력 모듈이 포함된 개발자용 ZIP

※ 파일이 보이지 않는다면 아직 빌드/릴리즈가 완료되지 않은 것입니다. 소스 코드의 초록색 **Code → Download ZIP**은 설치 파일이 아닙니다.

## 설치 방법 (Windows)

1. Fallout 2나 사용하려는 모드를 **별도 폴더에 복사**하고, [공식 sfall 4.5.1](https://github.com/sfall-team/sfall/releases/tag/v4.5.1)의 `ddraw.dll`을 준비합니다. 기존 모드 구성과 `sfall.dat`은 보존합니다.
2. 위 릴리즈의 Windows 설치기 EXE를 실행하고, **게임 복사본 폴더**를 선택합니다.
3. 게임을 선택합니다. 원본 EXE가 한 가지 프로필과 일치하면 자동 선택하며, **여러 프로필에서 같은 EXE를 사용하는 경우 직접 선택**해야 합니다.
4. 별도로 확보한 **FO2_UPU_CHT_v34**의 `Fallout2.exe`와 원본 `fallout2font.dll`을 각각 지정합니다. Sonora, Nevada, Olympus 등 전용 EXE 모드는 비교용 **원본 US 1.02d `fallout2.exe`**도 필요합니다.
5. **검사 및 설치**를 누릅니다. 설치기가 파일 해시를 확인하고 원본을 백업합니다.
6. 게임별 한국어 번역 저장소에서 제공하는 **`korean-classic-data` 번역 ZIP**을 게임 실행 파일이 위치한 폴더에 별도로 적용합니다. Et Tu는 `Fallout1in2` 폴더가 대상입니다.

**복구:** 설치기에서 같은 게임 폴더를 선택한 후 **백업으로 복구**를 누릅니다. 백업 폴더는 `korean_engine_backup_v2`입니다. 단, 번역 ZIP으로 별도 설치한 파일은 복구되지 않습니다.

### 지원 대상으로 검사한 게임

| 게임/모드 | 프로필 |
| --- | --- |
| Fallout 2 US 1.02d | `stock` |
| Restoration Project Updated (RPU 2.4.34) | `rpu` |
| Fallout Et Tu (2.0.3911) | `ettu` |
| Fallout Sonora 클래식 / 지정된 개발본 | `sonora` / `sonora-dev` |
| Fallout Nevada Extended | `nevada` |
| Olympus 2207 1.2 | `olympus` |
| Fallout 1.5 Resurrection English 1.5 + KR 1.1 | `resurrection` |

지원 여부는 **지정된 EXE·라이브러리 버전 및 해시** 기준입니다. 설치·확인 화면을 시험한 기록으로, 전체 게임이나 장시간 플레이 검증을 뜻하지 않습니다. x64 CE/Fission은 아직 지원 대상으로 검증되지 않았습니다.

## 자주 묻는 질문

**Q. 왜 다른 파일을 직접 준비해야 하나요?**  
이 저장소는 게임 실행 파일, 공식 `ddraw.dll`, 기존 CJK 실행 파일과 DLL을 배포하지 않습니다. 사용자가 정당하게 보유한 파일을 설치 과정에서 검증하고 사용합니다.

**Q. 왜 설치가 거부되나요?**  
지원하지 않는 EXE, 공식 sfall 버전 불일치, 이미 수정된 파일, 잘못 지정한 CJK 파일 등이 원인일 수 있습니다. 임의의 파일을 강제로 패치하지 마세요.

**Q. 번역문도 같이 설치되나요?**  
아니요. 이 저장소는 한국어 **출력 엔진**이고, 번역 데이터는 각 모드의 별도 한국어 패치입니다.

## 개발 및 상세 기술 문서

- [기술 설명·명령행 설치·버전별 주의 사항](docs/TECHNICAL.md)
- [검증 기록](docs/validation.json) · [테스트 안내](docs/TESTING.md)
- 이전 방식의 [한국어 sfall 포크](https://github.com/munument1/Fallout2-sfall-KR)

새 출력 어댑터·설치 도구는 MIT, Galmuri 글꼴은 OFL을 따릅니다. 원본 게임·CJK 파일은 포함하지 않습니다.
