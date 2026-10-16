"""User-facing Windows installer for the verified Korean text engine.

The GUI delegates all patching and recovery to install_engine.py. Game,
sfall and third-party CJK executables are never included in this package.
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
    "stock": "Fallout 2 (원본)",
    "rpu": "Fallout 2 - Restoration Project Updated",
    "ettu": "Fallout Et Tu (Fallout 1 in 2)",
    "sonora": "Fallout Sonora",
    "sonora-dev": "Fallout Sonora (개발판)",
    "nevada": "Fallout Nevada Extended",
    "olympus": "Olympus 2207",
    "resurrection": "Fallout 1.5 Resurrection",
}
PROFILE_BY_TITLE = {title: key for key, title in PROFILE_TITLES.items()}


def manifest_data():
    return json.loads((engine.ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))


def _matching_file(directory, filename, expected_sha):
    """Match exact file content; never trust a filename alone."""
    path = Path(directory)
    if not path.is_dir():
        return None
    try:
        for item in path.iterdir():
            if item.name.casefold() != filename.casefold():
                continue
            if not item.is_file() or item.is_symlink():
                continue
            if sha(item.read_bytes()) == expected_sha:
                return item
    except OSError:
        return None
    return None


def find_cjk_files(directory, manifest):
    """Locate the exact two supported third-party CJK files in one folder."""
    exe = _matching_file(directory, "Fallout2.exe", manifest["cjk_exe_sha256"])
    dll = _matching_file(directory, "fallout2font.dll", manifest["legacy_font_sha256"])
    return (exe, dll) if exe and dll else (None, None)


def suggest_stock_exe(directory, manifest):
    """Check only the chosen folder and its parent, not the entire drive."""
    root = Path(directory)
    for candidate_dir in (root, root.parent):
        original = _matching_file(candidate_dir, "fallout2.exe", manifest["stock_sha256"])
        if original:
            return original
    return None


def detect_profiles(directory, manifest):
    """Return exact verified profiles; shared EXEs may be ambiguous."""
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


def guess_profile(directory, matches):
    """Select only when unambiguous or the Et Tu directory is distinctive."""
    if len(matches) == 1:
        return matches[0]
    if Path(directory).name.casefold() == "fallout1in2" and "ettu" in matches:
        return "ettu"
    return None


def self_test():
    """CI tests the bundled manifest/adapter without modifying a game."""
    manifest = manifest_data()
    for name, expected in manifest["assets"].items():
        if sha((engine.ROOT / name).read_bytes()) != expected:
            raise ValueError("Bundled file failed hash verification: " + name)
    assert "stock" in manifest["profiles"]
    return 0


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fallout 2 한국어 출력 엔진")
        self.geometry("730x520")
        self.minsize(650, 485)
        self.manifest = manifest_data()
        self.target = tk.StringVar()
        self.cjk_folder = tk.StringVar()
        self.profile_title = tk.StringVar()
        self.base = tk.StringVar()
        self.keep_menu = tk.BooleanVar(value=False)
        self.configure_sfall = tk.BooleanVar(value=False)
        self.advanced = tk.BooleanVar(value=False)
        self.summary = tk.StringVar(value="게임 폴더를 선택해 주세요.")
        self.cjk_summary = tk.StringVar(value="CJK 파일을 압축 해제한 폴더를 선택해 주세요.")
        self._details_visible = False
        self._layout()

    def _layout(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Fallout 2 한국어 출력 엔진",
                  font=("Malgun Gothic", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="폴더 2개 선택 → 설치. 기존 파일은 자동으로 백업합니다.",
                  font=("Malgun Gothic", 10)).pack(anchor="w", pady=(4, 14))

        self._folder_row(outer, "① 게임/모드 폴더", self.target, self._inspect_game)
        ttk.Label(outer, textvariable=self.summary, wraplength=670,
                  foreground="#555").pack(anchor="w", pady=(3, 7))

        ttk.Label(outer, text="게임 종류", font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        self.combo = ttk.Combobox(outer, textvariable=self.profile_title,
                                  state="readonly", values=list(PROFILE_TITLES.values()),
                                  width=48)
        self.combo.pack(anchor="w", pady=(2, 10))

        self._folder_row(outer, "② CJK 원본 파일 폴더 (FO2_UPU_CHT_v34)", self.cjk_folder,
                         self._inspect_cjk)
        ttk.Label(outer, textvariable=self.cjk_summary, wraplength=670,
                  foreground="#555").pack(anchor="w", pady=(3, 8))

        ttk.Checkbutton(outer, text="고급 설정 (추가 원본 EXE · 메뉴 설정)",
                        variable=self.advanced, command=self._toggle_advanced).pack(anchor="w")
        self.advanced_frame = ttk.Frame(outer)
        self._file_row(self.advanced_frame, "원본 Fallout 2 US 1.02d EXE (일부 모드에서 필요)", self.base)
        ttk.Checkbutton(self.advanced_frame, text="기존 메뉴 표시 설정 유지",
                        variable=self.keep_menu).pack(anchor="w", pady=(4, 3))
        ttk.Checkbutton(self.advanced_frame,
                        text="sfall 호환 설정 적용 (ddraw.ini 수정, 필요할 때만)",
                        variable=self.configure_sfall).pack(anchor="w", pady=(4, 3))

        actions = ttk.Frame(outer)
        self.actions = actions
        actions.pack(fill="x", pady=(17, 6))
        ttk.Button(actions, text="설치하기", command=self._install).pack(side="left", padx=(0, 9))
        ttk.Button(actions, text="설치 전 상태로 복구", command=self._restore).pack(side="left")
        ttk.Button(actions, text="사용법", command=self._help).pack(side="right")

        ttk.Label(outer, text="한국어 번역문은 해당 모드의 한국어 패치를 별도로 설치해야 합니다.",
                  foreground="#555", wraplength=665).pack(anchor="w", pady=(6, 4))
        ttk.Button(outer, text="오류 및 작업 기록 보기", command=self._toggle_log).pack(anchor="w")
        self.log = tk.Text(outer, height=5, wrap="word", state="disabled")
        # Debug output hidden by default to keep the ordinary installation simple.

    def _folder_row(self, outer, label, variable, on_pick):
        ttk.Label(outer, text=label, font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(3, 2))
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x",
                                                   expand=True, padx=(0, 8))
        def choose():
            selection = filedialog.askdirectory(parent=self)
            if selection:
                variable.set(selection)
                on_pick()
        ttk.Button(row, text="폴더 선택", command=choose).pack(side="right")

    def _file_row(self, outer, label, variable):
        ttk.Label(outer, text=label).pack(anchor="w", pady=(8, 2))
        row = ttk.Frame(outer)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x",
                                                   expand=True, padx=(0, 8))
        def choose():
            selection = filedialog.askopenfilename(parent=self)
            if selection:
                variable.set(selection)
        ttk.Button(row, text="찾아보기", command=choose).pack(side="right")

    def _toggle_advanced(self):
        if self.advanced.get():
            self.advanced_frame.pack(fill="x", before=self.actions)
        else:
            self.advanced_frame.pack_forget()

    def _toggle_log(self):
        if self._details_visible:
            self.log.pack_forget()
        else:
            self.log.pack(fill="both", expand=True, pady=(5, 0))
        self._details_visible = not self._details_visible

    def _append(self, value):
        self.log.configure(state="normal")
        self.log.insert("end", value + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _inspect_game(self):
        self.profile_title.set("")
        path = Path(self.target.get())
        if not path.is_dir():
            self.summary.set("게임 폴더를 찾을 수 없습니다.")
            return
        try:
            path = engine.validate_target(path)
            matches = detect_profiles(path, self.manifest)
            self.combo.configure(values=[PROFILE_TITLES[key] for key in matches])
            selected = guess_profile(path, matches)
            if selected:
                self.profile_title.set(PROFILE_TITLES[selected])
                self.summary.set("확인 완료: " + PROFILE_TITLES[selected])
            elif matches:
                self.summary.set("여러 모드가 같은 실행 파일을 사용합니다. 게임 종류만 선택해 주세요.")
            elif (path / engine.BACKUP / "manifest.json").is_file():
                self.summary.set("이미 설치된 폴더일 수 있습니다. 복구 버튼을 이용하세요.")
            else:
                self.summary.set("지원하는 버전의 게임 실행 파일을 찾지 못했습니다.")
        except (OSError, ValueError) as exc:
            self.summary.set(str(exc))

    def _inspect_cjk(self):
        exe, dll = find_cjk_files(self.cjk_folder.get(), self.manifest)
        if exe and dll:
            self.cjk_summary.set("확인 완료: 필요한 CJK 원본 파일 2개를 찾았습니다.")
        else:
            self.cjk_summary.set("필요한 CJK EXE와 글꼴 DLL이 이 폴더에 모두 있는지 확인하세요.")

    def _arguments(self, dry_run):
        if not self.target.get():
            raise ValueError("게임 폴더를 선택하세요.")
        target = engine.validate_target(Path(self.target.get()))
        profile = PROFILE_BY_TITLE.get(self.profile_title.get())
        if not profile or profile not in detect_profiles(target, self.manifest):
            raise ValueError("지원하는 게임 종류를 선택하세요. 원본 파일 버전이 다르면 설치할 수 없습니다.")
        if not self.cjk_folder.get():
            raise ValueError("CJK 원본 폴더를 선택하세요.")
        cjk_exe, legacy = find_cjk_files(self.cjk_folder.get(), self.manifest)
        if cjk_exe is None or legacy is None:
            raise ValueError("CJK 원본 폴더를 선택하세요. FO2_UPU_CHT_v34의 EXE와 DLL이 필요합니다.")
        # Korean text drawing needs the game/CJK font bridge, not sfall.
        # The core installer optionally configures a mod's existing sfall.
        engine.inspect_sfall(target, self.manifest)

        profile_spec = self.manifest["profiles"][profile]
        game_exe = target / profile_spec["exe"]
        stock = None
        if sha(game_exe.read_bytes()) != self.manifest["stock_sha256"]:
            stock = Path(self.base.get()) if self.base.get() else suggest_stock_exe(target, self.manifest)
            if stock is None:
                selection = filedialog.askopenfilename(parent=self,
                    title="원본 Fallout 2 US 1.02d의 fallout2.exe 선택",
                    filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")])
                if not selection:
                    raise ValueError("이 모드에는 원본 Fallout 2 US 1.02d 실행 파일이 필요합니다.")
                stock = Path(selection)
            if not stock.is_file() or sha(stock.read_bytes()) != self.manifest["stock_sha256"]:
                raise ValueError("선택한 파일이 지원하는 원본 Fallout 2 US 1.02d EXE가 아닙니다.")
        return target, argparse.Namespace(
            profile=profile, cjk_exe=cjk_exe, legacy_font=legacy,
            base_exe=stock, keep_menu_settings=self.keep_menu.get(),
            configure_sfall=self.configure_sfall.get(), dry_run=dry_run)

    def _install(self):
        try:
            target, arguments = self._arguments(dry_run=True)
            check = engine.install(arguments, target)
            self._append("설치 검사: " + json.dumps(check, ensure_ascii=False))
            if check["sfall_status"] == "existing-unverified":
                messagebox.showwarning("기존 sfall 버전",
                    "설치된 sfall은 유지됩니다. 기존 파일과 설정을 보존하며 "
                    "한국어 출력 연결만 적용합니다.\n"
                    "해당 sfall 버전과 수정 EXE의 실제 게임 호환성은 별도 확인이 필요합니다.",
                    parent=self)
            if not messagebox.askyesno("설치 확인",
                    "게임 복사본에 한국어 출력 엔진을 설치합니다.\n"
                    "기존 파일은 자동 백업합니다. 계속할까요?", parent=self):
                return
            arguments.dry_run = False
            outcome = engine.install(arguments, target)
            self._append("설치 완료: " + json.dumps(outcome, ensure_ascii=False))
            messagebox.showinfo("설치 완료",
                "한국어 출력 엔진을 설치했습니다.\n"
                "이제 해당 게임의 한국어 번역 패치를 적용하세요.", parent=self)
            self.summary.set("설치 완료 · 필요하면 복구 버튼으로 원상 복구할 수 있습니다.")
        except (OSError, ValueError, UnicodeError, pefile.PEFormatError, KeyError) as exc:
            self._append("설치 오류: " + str(exc))
            messagebox.showerror("설치할 수 없습니다", str(exc), parent=self)

    def _restore(self):
        try:
            target = engine.validate_target(Path(self.target.get()))
            engine.restore(target, dry_run=True)
            if not messagebox.askyesno("복구 확인",
                    "기존 백업으로 설치 전 상태를 복구할까요?\n"
                    "별도로 적용한 번역 패치 파일은 복구되지 않습니다.", parent=self):
                return
            outcome = engine.restore(target, dry_run=False)
            self._append("복구 완료: " + json.dumps(outcome, ensure_ascii=False))
            self.summary.set("기존 파일로 복구했습니다.")
            messagebox.showinfo("복구 완료", "엔진 설치 이전 상태로 복구했습니다.", parent=self)
        except (OSError, ValueError, KeyError) as exc:
            self._append("복구 오류: " + str(exc))
            messagebox.showerror("복구할 수 없습니다", str(exc), parent=self)

    def _help(self):
        messagebox.showinfo("간단 설치 안내",
            "① Fallout 2 / 호환 모드를 별도 폴더에 준비합니다.\n"
            "   sfall은 순정판 한글 출력에 필수는 아닙니다.\n"
            "   모드가 sfall을 요구하면 기존 구성을 유지하세요.\n"
            "   수정된 EXE가 sfall과 호환되지 않을 경우 설치가 중단되며\n"
            "   고급 설정에서 명시적으로 허용할 수 있습니다.\n\n"
            "② 보유한 FO2_UPU_CHT_v34의 압축을 풀고 폴더를 선택합니다.\n"
            "   EXE와 기존 글꼴 DLL이 같은 폴더에 있어야 합니다.\n\n"
            "③ 설치하기 버튼을 누릅니다.\n"
            "   전용 EXE 모드는 원본 Fallout 2 EXE를 추가로 물어볼 수 있습니다.\n\n"
            "④ 게임별 한국어 번역 패치는 별도로 적용합니다.\n"
            "   Et Tu는 Fallout1in2 폴더를 선택하세요.", parent=self)


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
