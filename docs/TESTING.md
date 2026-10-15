# 검사 입력과 범위

기본 unittest는 배포 자산 해시를 검사한다. 실제 원본 파일을 사용하는 검사는 KOREAN_ENGINE_TEST_INPUTS 환경 변수로 로컬 JSON을 지정했을 때만 실행한다. 게임/CJK 파일을 저장소나 GitHub Actions 로그에 올리지 않는다.

```json
{
  "stock": "D:/GameInputs/US-1.02d/fallout2.exe",
  "cjk_exe": "D:/GameInputs/CJK/Fallout2.exe",
  "legacy_font": "D:/GameInputs/CJK/fallout2font.dll",
  "sfall_dll": "D:/GameInputs/sfall-4.5.1/ddraw.dll",
  "originals": {
    "stock": "D:/GameInputs/US-1.02d/fallout2.exe",
    "rpu": "D:/GameInputs/US-1.02d/fallout2.exe",
    "ettu": "D:/GameInputs/US-1.02d/fallout2.exe",
    "sonora": "D:/GameInputs/Sonora/FSonoraDLC.exe",
    "nevada": "D:/GameInputs/Nevada/Nevada.exe",
    "olympus": "D:/GameInputs/Olympus/olympus.exe",
    "resurrection": "D:/GameInputs/Resurrection/FALLOUT2"
  }
}
```

검사는 임시 폴더의 복사본에만 쓴다. 일곱 프로필의 파생 EXE가 실제 화면 시험본의 해시와 같은지, 공식 sfall 보존, 모드 설정과 CP949 주석 보존, 설치 전 검사 무변경, 복구, 미검증 EXE/sfall 거부, 사용자 변경 후 자동 복구 중단을 확인한다.

레이아웃·대화·전투·장시간 플레이는 이 자동 검사로 증명하지 않는다. 사용자 화면 확인 기록은 validation.json에 별도로 기록한다.

리저렉션 입력은 확장자 없는 원본 `FALLOUT2` 경로다. 같은 폴더에 원본 `fores.exe`, `f2_res.dll`, `ddraw.ini`, `fores.cfg`, `f2_res.ini`를 둔다. 런처·외부 HRP 보존, 미검증 런처 거부, `HiResMode=0`, 리저렉션 전용 시작 맵·DAT 경로 보존과 복구도 검사한다.
