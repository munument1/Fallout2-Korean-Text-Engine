"""Simple Windows UI for the verified Fallout 2 Korean text-engine installer.

This is only a front end: all actual patching, backup and hash checks remain
in install_engine.py. Game/sfall/CJK executables are never bundled.
"""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pefile
from tools import install_engine as engine
from tools.runtime import sha

PROFILE_TITLES = {
    "stock": "Fallout 2 (US 1.02d)",
    "rpu": "Fallout 2 - RPU",
    "ettu": "Fallout 1 in 2 (Et Tu)",
    "sonora": "Fallout Sonora (Classic)",
    "sonora-dev": "Fallout Sonora (Development)",
    "nevada": "Fallout Nevada Extended",
    "olympus": "Olympus 2207",
    "resurrection": "Fallout 1.5 Resurrection",
}


def manifest_data():
    return json.loads((engine.ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))


def detect_profiles(directory, manifest):
    """Return all known profiles matching an unmodified executable hash.

    Some profiles intentionally share the same game EXE. The UI must ask the
    user to disambiguate rather than guessing a mod from a common EXE.
    """
    directory = Path(directory)
    matches = []
    for key, spec in manifest["profiles"].items():
        path = directory / spec["exe"]
        if not path.is_file() or path.is_symlink():
            continue
        try:
            if sha(path.read_bytes()) != spec["original_sha256"]:
                continue
            if any(not (directory / name).is_file() or
                   sha((directory / name).read_bytes()) != digest
                   for name, digest in spec.get("required_files", {}).items()):
                continue
        except OSError:
            continue
        matches.append(key)
    return matches


def self_test():
    """Used by CI to check that the frozen EXE contains verified data."""
    manifest = manifest_data()
    for name, expected in manifest["assets"].items():
        if sha((engine.ROOT / name).read_bytes()) != expected:
            raise ValueError("Bundled file failed hash verification: " + name)
    assert "stock" in manifest["profiles"]
    return 0


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fallout 2 한국어 출력 엔진 설치기")
        self.geometry("780x640")
        self.minsize(690, 575)
        self.manifest = manifest_data()
        self.target = tk.StringVar()
        self.profile = tk.StringVar()
        self.donor = tk.StringVar()
        self.legacy = tk.StringVar()
        self.base = tk.StringVar()
        self.keep_menu = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="게임 복사본 폴더를 선택하세요.")
        self._layout()

    def _layout(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Fallout 2 한국어 출력 엔진", font=("Malgun Gothic", 16, "bold")).pack(anchor="w")
        ttk.Label(outer, text="원본 게임 폴더가 아닌 별도 복사본에서 작업하세요. 번역 데이터는 별도 설치입니다.",
                  wraplength=730).pack(anchor="w", pady=(6, 12))
        self._picker(outer, "1. 게임/모드 복사본 폴더", self.target, folder=True, callback=self._inspect)
        ttk.Label(outer, text="2. 지원 게임 선택").pack(anchor="w", pady=(8, 2))
        self.combo = ttk.Combobox(outer, textvariable=self.profile, state="readonly",
                                  values=list(PROFILE_TITLES), width=35)
        self.combo.pack(anchor="w")
        ttk.Label(outer, text="자동 검출이 여러 개면 정확한 모드를 직접 선택하세요.", foreground="#555").pack(anchor="w")
        ttk.Label(outer, textvariable=self.status, wraplength=730).pack(anchor="w", pady=(4, 8))
        self._picker(outer, "3. 별도로 확보한 CJK Fallout2.exe (FO2_UPU_CHT_v34)", self.donor)
        self._picker(outer, "4. 같은 CJK 패키지의 기존 fallout2font.dll", self.legacy)
        self._picker(outer, "5. 원본 US 1.02d fallout2.exe (전용 EXE 모드에서 필요)", self.base)
        ttk.Checkbutton(outer, text="기존 메뉴 표시 설정 유지", variable=self.keep_menu).pack(anchor="w", pady=(4, 10))
        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        ttk.Button(actions, text="검사 및 설치", command=self._install).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="백업으로 복구", command=self._restore).pack(side="left")
        ttk.Button(actions, text="사용 방법", command=self._help).pack(side="right")
        ttk.Label(outer, text="실행 기록").pack(anchor="w", pady=(12, 2))
        self.log = tk.Text(outer, height=9, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def _picker(self, parent, title, variable, folder=False, callback=None):
        ttk.Label(parent, text=title).pack(anchor="w", pady=(4, 2))
        row = ttk.Frame(parent)
        row.pack(fill="x")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        def browse():
            selected = (filedialog.askdirectory(parent=self) if folder
                        else filedialog.askopenfilename(parent=self))
            if selected:
                variable.set(selected)
                if callback:
                    callback()
        ttk.Button(row, text="찾아보기", command=browse).pack(side="right")

    def _append(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def _inspect(self):
        self.profile.set("")
        path = Path(self.target.get())
        if not path.is_dir():
            self.status.set("먼저 존재하는 게임 폴더를 선택하세요.")
            return
        try:
            path = engine.validate_target(path)
            matches = detect_profiles(path, self.manifest)
            if len(matches) == 1:
                self.profile.set(matches[0])
                self.status.set("자동 확인: " + PROFILE_TITLES[matches[0]])
            elif matches:
                self.status.set("여러 게임이 같은 EXE를 사용합니다. 아래 중 정확한 모드를 고르세요: " +
                                ", ".join(matches))
            else:
                self.status.set("알려진 원본 EXE를 찾지 못했습니다. 설치 전 파일과 버전을 확인하세요.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def _arguments(self, dry_run):
        if not self.profile.get() or self.profile.get() not in self.manifest["profiles"]:
            raise ValueError("지원 게임 프로필을 먼저 선택하세요.")
        if not self.donor.get() or not self.legacy.get():
            raise ValueError("CJK EXE와 기존 폰트 DLL을 모두 지정하세요.")
        target = engine.validate_target(Path(self.target.get()))
        return target, argparse.Namespace(
            profile=self.profile.get(),
            cjk_exe=Path(self.donor.get()),
            legacy_font=Path(self.legacy.get()),
            base_exe=Path(self.base.get()) if self.base.get() else None,
            keep_menu_settings=self.keep_menu.get(),
            dry_run=dry_run,
        )

    def _install(self):
        try:
            target, arguments = self._arguments(dry_run=True)
            report = engine.install(arguments, target)
            self._append("사전 검사 통과: " + json.dumps(report, ensure_ascii=False))
            if not messagebox.askyesno("설치 확인",
                "검증된 파일입니다. 게임 폴더에 한국어 출력 엔진을 설치할까요?\n"
                "원본 파일은 korean_engine_backup_v2에 백업됩니다.", parent=self):
                return
            arguments.dry_run = False
            result = engine.install(arguments, target)
            self._append("설치 완료: " + json.dumps(result, ensure_ascii=False))
            messagebox.showinfo("설치 완료",
                "한국어 출력 엔진을 설치했습니다.\n게임별 한국어 번역 ZIP은 별도로 적용하세요.", parent=self)
        except (OSError, ValueError, UnicodeError, pefile.PEFormatError, KeyError) as exc:
            self._append("설치 실패 (변경 없음 또는 자동 롤백): " + str(exc))
            messagebox.showerror("설치 실패", str(exc), parent=self)

    def _restore(self):
        try:
            target = engine.validate_target(Path(self.target.get()))
            engine.restore(target, dry_run=True)
            if not messagebox.askyesno("복구 확인",
                "엔진 설치 전에 백업한 파일로 복구할까요?\n번역 ZIP 내용은 복구 대상이 아닙니다.", parent=self):
                return
            result = engine.restore(target, dry_run=False)
            self._append("복구 완료: " + json.dumps(result, ensure_ascii=False))
            messagebox.showinfo("복구 완료", "출력 엔진 설치 이전 상태로 복구했습니다.", parent=self)
        except (OSError, ValueError, KeyError) as exc:
            self._append("복구 실패: " + str(exc))
            messagebox.showerror("복구 실패", str(exc), parent=self)

    def _help(self):
        messagebox.showinfo("필요한 파일",
            "1. 게임과 공식 sfall 4.5.1을 별도 복사본에 준비\n"
            "2. 별도 확보한 FO2_UPU_CHT_v34의 EXE 및 글꼴 DLL 지정\n"
            "3. 전용 EXE를 쓰는 모드는 원본 US 1.02d EXE도 지정\n"
            "4. 검사 및 설치 후 게임별 번역 데이터를 따로 설치\n\n"
            "알려진 파일 해시가 맞지 않으면 설치를 중단합니다.\n"
            "Et Tu의 대상 폴더는 Fallout1in2입니다.", parent=self)


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            raise SystemExit(self_test())
        Installer().mainloop()
    except Exception as error:
        if "--self-test" in sys.argv:
            print(error, file=sys.stderr)
            raise SystemExit(1)
        raise
