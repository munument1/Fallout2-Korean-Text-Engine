# Fallout 2 Korean Text Engine — 기술 설명 및 고급 설치

공식 sfall DLL을 수정하지 않고 클래식 Fallout 2에 CP949 한국어 출력·글꼴·줄바꿈을 제공하는 공통 출력 모듈이다. 번역 데이터는 각 모드의 번역 저장소에서 별도로 관리한다.

현재 시험 기준은 **공식 sfall 4.5.1**, TEXT=Galmuri9 / Size 10 / Weight 400, BUTTON=Galmuri11 / Size 14 / Weight 600이다. 게임의 언어는 `language=korean`을 사용한다.

## 검증 범위

| 프로필 | 기존 모드 기준 | 확인 결과 |
| --- | --- | --- |
| `stock` | US 1.02d | 초기 코어의 선택 화면 확인 |
| `rpu` | RPU 2.4.34 | 실제 한국어 번역과 보완한 배경 설명·메뉴 확인 |
| `ettu` | EtTu 2.0.3911 | 기존 번역 유지·변경 문구 이행, 본문과 보완한 한국어 메뉴 확인 |
| `sonora` | 기존 Sonora 클래식 설치본 | 메뉴 배치·버튼 크기·굵기 확인 |
| `sonora-dev` | Sonora eng_repack `de13b880ced4` 개발본 | 요청한 확인 화면·한글·줄바꿈 및 수정한 하단 글머리 기호 정상 |
| `nevada` | 기존 Nevada Extended 설치본 | 동일 설정 재실행 후 정상 표시 |
| `olympus` | Olympus 2207 1.2 설치본 | 전용 메뉴 복구 후 확인 화면 정상 |
| `resurrection` | Resurrection English 1.5 + KR1.1 | 기존 런처·외부 고해상도 패치 유지 후 확인 화면 정상 |

전체 UI나 장시간 플레이 검증을 뜻하지 않는다. 네바다의 첫 실행 종료는 같은 설정 재실행에서 재현되지 않았으며 원인은 미확정이다. x64 CE/Fission은 아직 지원 판정하지 않았다. 새 sfall 버전은 별도로 검증한다.

[실행 검증 기록](docs/validation.json). 설치 도구는 여덟 프로필에서 게임 시험 EXE와 결과 해시가 같은지, 설정 보존·설치·복구·미검증 파일 거부를 검사했다. EtTu는 2.0.3911, Sonora는 위 개발 커밋까지 별도로 이행·검증했다.

## 포함 파일

- 새 `fallout2font.dll`과 해당 C++ 소스·빌드 파일: 한국어/Unicode GDI 출력, 실제 폭에 따른 줄바꿈, CR/LF 처리, 원문 보존, 차분한 글자색.
- Galmuri9/11 및 OFL 라이선스.
- 사용자 제공 파일에서 검증한 런타임을 구성하는 설치 도구와 파일 해시 목록.

**게임 EXE, 공식/개조 sfall `ddraw.dll`, 기존 CJK 글꼴 DLL은 포함하지 않는다.** 설치 도구는 사용자가 가진 CJK EXE에 한국어용 추가 수정 61바이트를 반영하고, 모드 전용 코드·데이터 및 리소스를 보존한다. 검증된 원본 EXE 해시만 허용한다.

## 설치

게임을 종료하고 독립 복사본에서 실행한다. 기존 Steam 원본 설치 경로는 도구가 보호한다. 이전 방식의 한국어 `ddraw.dll`을 계속 사용하는 구성과 섞지 않는다.

1. 해당 모드와 [공식 sfall 4.5.1](https://github.com/sfall-team/sfall/releases/tag/v4.5.1)을 준비한다. 공식 `ddraw.dll`·`sfall.dat`를 사용하고 모드의 기존 설정·스크립트·DAT는 유지한다.
2. Python 3.10 이상에서 이 저장소의 의존성을 설치한다.

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. 직접 보유한 `FO2_UPU_CHT_v34`의 **원본 CJK Fallout2.exe와 fallout2font.dll**을 별도로 준비한다. 허용 해시는 `runtime-manifest.json`에 있다. 기존 RPU v28의 한국어 sfall DLL은 대상이 아니다.
4. 아래 예시에서 게임 복사본·CJK 파일 경로와 프로필을 자신의 환경에 맞춘다. 먼저 `--dry-run`으로 확인한 뒤 같은 명령에서 `--dry-run`을 빼고 설치한다.

   ```powershell
   python tools/install_engine.py 'D:\Games\RPU-test' --profile rpu --cjk-exe 'D:\CJK\Fallout2.exe' --legacy-font 'D:\CJK\fallout2font.dll' --dry-run
   ```

   소노라·네바다·올림푸스처럼 전용 EXE를 쓰는 모드는 원본 US 1.02d EXE 비교용 경로도 추가한다.

   ```powershell
   python tools/install_engine.py 'D:\Games\Nevada-test' --profile nevada --cjk-exe 'D:\CJK\Fallout2.exe' --legacy-font 'D:\CJK\fallout2font.dll' --base-exe 'D:\Games\Vanilla\fallout2.exe' --dry-run
   ```

5. 모드 번역 저장소에서 만든 새 방식 `korean-classic-data` ZIP을 실제 모드 실행 파일이 있는 폴더에 적용한다. 에투는 Fallout1in2 폴더다. 번역 데이터와 엔진을 서로 다른 모드용으로 섞지 않는다.

설치 도구는 EXE·글꼴 파일 외에 `ExtraCRC`, `language=korean`, 번역 INI 경로, 검증한 메뉴 표시 항목과 리저렉션의 고해상도 중복 방지 설정을 적용한다. 게임 해상도나 모드 스크립트는 바꾸지 않는다. 기존 메뉴 설정을 유지하려면 `--keep-menu-settings`를 추가한다. 올림푸스는 전용 메뉴 그림을 활성화해야 하므로 그 예외를 프로필에 포함했다.

리저렉션은 **Resurrection 폴더**에 `--profile resurrection`으로 적용한다. 확장자 없는 `FALLOUT2`가 실제 게임 파일이고 `fores.exe`는 원본 그대로 유지할 전용 런처다. 설치 후에도 **`fores.exe`로 실행**한다. 도구는 검증한 런처와 `f2_res.dll` 해시를 확인하고, 외부 고해상도 패치와의 중복을 피하도록 `ddraw.ini`의 `[Main] HiResMode=0`을 설정한다. `--keep-menu-settings`를 써도 이 중복 방지 설정은 적용한다.

소노라 개발본은 먼저 [한국어 저장소의 런타임 준비 도구](https://github.com/munument1/Fallout2-Sonora-KR/blob/main/docs/SONORA_DEVELOPMENT_KO.md)로 `1.16.4-sfall` 원본에서 고정된 개발 커밋을 구성한다. **`--profile sonora-dev`와 `--base-exe`**를 지정하고 `fallout2.exe`로 실행한다. 기존 `FSonoraDLC.exe`용 `sonora` 프로필과 구분한다. 외부 HRP 중복 방지용 `HiResMode=0`을 사용하며 원본 EXE의 모드 변경 38바이트를 보존한다.

이 개발본의 외부 HRP 4.1.8은 하단 메시지창에 CP949와 충돌하는 `0x95` 글머리 기호를 별도로 넣는다. 검증된 **`f2_res.dll`의 상수 두 바이트만 `0xFF`로 변경**한다(파일 오프셋 `0x15085`, `0x150A6`). 원본 DLL을 백업하고 `--restore`로 복구하며, 정상 한글 바이트를 치환하지 않는다. 공식 sfall DLL과 배포 한국어 출력 DLL은 그대로다. 다른 HRP 파일이나 버전은 강제로 허용하지 않는다.

모드 프로필은 `translations\korean.ini`를 사용한다. 이 파일은 새 번역 ZIP에 포함된다. 일반 순정 `stock` 프로필은 기존 번역 INI 설정을 유지한다.

## 복구

설치 전 파일은 게임 복사본의 `korean_engine_backup_v2`에 보관한다.

```powershell
python tools/install_engine.py 'D:\Games\RPU-test' --restore --dry-run
python tools/install_engine.py 'D:\Games\RPU-test' --restore
```

설치 후 사용자가 변경한 파일이 있으면 자동 복구를 중단하여 덮어쓰지 않는다. 복구한 백업도 보존한다. 번역 ZIP으로 적용한 파일은 엔진 복구 대상과 별개다.

## 빌드·검사

x86 Visual Studio Developer Command Prompt에서 `build.cmd`를 실행한다. 소스 검사용 빌드와 현재 게임 확인을 마친 배포 DLL의 해시는 구분한다. DLL을 새로 빌드했으면 검증 후 manifest의 자산 해시도 갱신해야 한다.

```shell
python -m unittest discover -s tests -v
python tools/package_engine.py --output dist/korean-text-engine.zip
```

게임 입력 파일은 공개 테스트에 넣지 않는다. `KOREAN_ENGINE_TEST_INPUTS`에 로컬 JSON 경로를 지정하면 실제 검증 원본을 사용하는 설치·복구 검사를 실행한다. 입력 형식은 [테스트 안내](docs/TESTING.md)를 따른다.

## 라이선스와 기존 방식

새 어댑터·도구의 소스는 MIT, Galmuri는 OFL이다. 사용자가 별도로 제공하는 기존 게임/CJK 파일에 새 라이선스를 부여하지 않는다. [이전 한국어 sfall 포크](https://github.com/munument1/Fallout2-sfall-KR)의 릴리스·이력은 보존하며 새 방식의 출력 모듈은 이 저장소에서 관리한다.
