"""User-facing Windows installer for the Korean text engine.

The GUI delegates patching and recovery to install_engine.py. Game, sfall,
and third-party CJK executables are not included in the installer binary.
Experimental builds can temporarily fetch a verified CJK EXE with consent.
"""
import argparse
import json
import tempfile
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pefile
from tools import install_engine as engine
from tools.runtime import sha
from tools.cjk_provider import download_verified_exe
from tools.native_pe import SUPPORTED_NATIVE_SHA256, RPU_HRP_SHA256

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


def detect_native_profile(directory):
    """Auto-select the engine target from an exact verified EXE and mod data.

    Only the stock Win32 1.02d and the independently verified 4.1.8 HRP
    bootstrap are supported. Other mod families need separate code analysis.
    """
    directory = Path(directory)
    # Et Tu can use an otherwise byte-identical Fallout2.exe while expecting
    # different mod settings and assets. Do not mislabel it as vanilla.
    if (directory.name.casefold() == "fallout1in2" or
            (directory / "mods" / "fallout1in2.dat").is_file() or
            (directory / "Fallout1in2.cfg").is_file()):
        return None
    exe = directory / "fallout2.exe"
    if not exe.is_file() or exe.is_symlink():
        return None
    try:
        digest = sha(exe.read_bytes())
        if digest not in SUPPORTED_NATIVE_SHA256:
            return None
        marker = directory / "mods" / "rpu.dat"
        if marker.is_file() and not marker.is_symlink():
            hi_res = directory / "fallout2HR.exe"
            if hi_res.exists() and (not hi_res.is_file() or hi_res.is_symlink() or
                                    sha(hi_res.read_bytes()) != digest):
                return None
            return "rpu"
        return "stock"
    except OSError:
        return None


def guess_profile(directory, matches):
    """Select only when unambiguous or the Et Tu directory is distinctive."""
    if len(matches) == 1:
        return matches[0]
    if Path(directory).name.casefold() == "fallout1in2" and "ettu" in matches:
        return "ettu"
    return None


def self_test(require_native=False):
    """CI tests the bundled manifest/adapter without modifying a game."""
    manifest = manifest_data()
    for name, expected in manifest["assets"].items():
        if sha((engine.ROOT / name).read_bytes()) != expected:
            raise ValueError("Bundled file failed hash verification: " + name)
    assert "stock" in manifest["profiles"]
    prototype = engine.ROOT / "standalone-font.dll"
    if prototype.is_file():
        pe = pefile.PE(data=prototype.read_bytes())
        required = {"InitFont", "ClearFont", "SelectFont", "GetTextWidth",
                    "GetTextHeight", "TextOutput", "TextOutputL", "TextOutputX", "SplitText"}
        exports = {symbol.name.decode("ascii") for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols
                   if symbol.name}
        if pe.FILE_HEADER.Machine != 0x14c or not required <= exports:
            raise ValueError("Bundled experimental font DLL has wrong ABI.")
        if require_native and "InitKoreanEngine" not in exports:
            raise ValueError("Bundled DLL lacks InitKoreanEngine native entry point.")
    elif require_native:
        raise ValueError("Native installer build is missing standalone-font.dll.")
    return 0


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fallout 2 한국어 출력 엔진")
        self.geometry("730x520")
        self.minsize(650, 485)
        self.manifest = manifest_data()
        self.experimental = (engine.ROOT / "standalone-font.dll").is_file()
        self.native_mode = False
        if self.experimental:
            native = pefile.PE(data=(engine.ROOT / "standalone-font.dll").read_bytes())
            exports = {symbol.name.decode("ascii") for symbol in native.DIRECTORY_ENTRY_EXPORT.symbols
                       if symbol.name}
            self.native_mode = "InitKoreanEngine" in exports
        self.auto_source = tk.BooleanVar(value=self.experimental and not self.native_mode)
        self.target = tk.StringVar()
        self.cjk_folder = tk.StringVar()
        self.profile_title = tk.StringVar()
        self.base = tk.StringVar()
        self.keep_menu = tk.BooleanVar(value=False)
        self.configure_sfall = tk.BooleanVar(value=False)
        self.advanced = tk.BooleanVar(value=False)
        self.summary = tk.StringVar(value="게임 폴더를 선택해 주세요.")
        self.cjk_summary = tk.StringVar(value="CJK EXE 공급원을 직접 지정할 때만 이 폴더를 선택하세요.")
        self._details_visible = False
        self._layout()

    def _layout(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Fallout 2 한국어 출력 엔진",
                  font=("Malgun Gothic", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text=("독립형 한국어 출력 엔진: Fallout 2 계열 게임/모드 폴더 하나만 선택하세요."
                               if self.native_mode else
                               "시험판: 게임 폴더만 선택 → 확인 후 설치. 기존 파일 자동 백업."
                               if self.experimental else
                               "폴더 2개 선택 → 설치. 기존 파일은 자동으로 백업합니다."),
                  font=("Malgun Gothic", 10)).pack(anchor="w", pady=(4, 14))

        self._folder_row(outer, "① 게임/모드 폴더", self.target, self._inspect_game)
        ttk.Label(outer, textvariable=self.summary, wraplength=670,
                  foreground="#555").pack(anchor="w", pady=(3, 7))

        if not self.native_mode:
            ttk.Label(outer, text="게임 종류", font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        self.combo = ttk.Combobox(outer, textvariable=self.profile_title,
                                  state="readonly", values=list(PROFILE_TITLES.values()),
                                  width=48)
        if not self.native_mode:
            self.combo.pack(anchor="w", pady=(2, 10))

        if self.native_mode:
            ttk.Label(outer,
                      text="호환되는 Fallout 2 Watcom 실행 파일을 내부 구조로 자동 검사합니다. 게임 종류 선택이나 중국어 CJK 파일이 필요 없습니다.",
                      foreground="#555", wraplength=670).pack(anchor="w", pady=(2, 8))
        elif self.experimental:
            ttk.Label(outer, text="독립형 글꼴 렌더러 시험판: 기존 CJK DLL은 사용하지 않습니다.",
                      foreground="#555", wraplength=670).pack(anchor="w")
            ttk.Checkbutton(outer,
                            text="NovaRain 저장소의 검증된 CJK EXE를 임시로 자동 다운로드 (아직 EXE는 의존)",
                            variable=self.auto_source, command=self._toggle_auto_source).pack(anchor="w", pady=(4, 5))
            self.cjk_block = ttk.Frame(outer)
            self._folder_row(self.cjk_block, "선택 사항: 직접 보유한 CJK EXE 폴더", self.cjk_folder,
                             self._inspect_cjk)
            ttk.Label(self.cjk_block, textvariable=self.cjk_summary, wraplength=670,
                      foreground="#555").pack(anchor="w", pady=(3, 8))
            if not self.auto_source.get():
                self.cjk_block.pack(fill="x")
        else:
            self._folder_row(outer, "② CJK 원본 파일 폴더 (FO2_UPU_CHT_v34)", self.cjk_folder,
                             self._inspect_cjk)
            ttk.Label(outer, textvariable=self.cjk_summary, wraplength=670,
                      foreground="#555").pack(anchor="w", pady=(3, 8))

        if not self.native_mode:
            ttk.Checkbutton(outer, text="고급 설정 (추가 원본 EXE · 메뉴 설정)",
                            variable=self.advanced, command=self._toggle_advanced).pack(anchor="w")
        self.advanced_frame = ttk.Frame(outer)
        if not self.native_mode:
            self._file_row(self.advanced_frame, "원본 Fallout 2 US 1.02d EXE (일부 모드에서 필요)", self.base)
        ttk.Checkbutton(self.advanced_frame, text="기존 메뉴 표시 설정 유지",
                        variable=self.keep_menu).pack(anchor="w", pady=(4, 3))
        ttk.Checkbutton(self.advanced_frame,
                        text="모드 전용 HiResMode 추가 호환 설정 (필요한 경우에만)",
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

    def _toggle_auto_source(self):
        if not self.experimental:
            return
        if self.auto_source.get():
            self.cjk_block.pack_forget()
        else:
            self.cjk_block.pack(fill="x", before=self.actions)

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
            if self.native_mode:
                if (path / engine.BACKUP / "manifest.json").is_file():
                    self.summary.set("이미 설치된 폴더입니다. 아래 '설치 전 상태로 복구' 버튼을 이용하세요.")
                else:
                    executables = engine.detect_native_executables(path)
                    config = engine.detect_native_config(path, executables.keys())
                    self.summary.set("자동 호환성 검사 통과: " + ", ".join(executables) +
                                     " / 설정: " + config)
                return
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
        if self.native_mode:
            return
        if self.experimental:
            cjk = _matching_file(self.cjk_folder.get(), "Fallout2.exe",
                                 self.manifest["cjk_exe_sha256"])
            self.cjk_summary.set("검증된 CJK EXE를 찾았습니다." if cjk else
                                 "이 폴더에 해시가 일치하는 Fallout2.exe가 필요합니다.")
            return
        exe, dll = find_cjk_files(self.cjk_folder.get(), self.manifest)
        if exe and dll:
            self.cjk_summary.set("확인 완료: 필요한 CJK 원본 파일 2개를 찾았습니다.")
        else:
            self.cjk_summary.set("필요한 CJK EXE와 글꼴 DLL이 이 폴더에 모두 있는지 확인하세요.")

    def _arguments(self, dry_run, download_directory=None):
        if not self.target.get():
            raise ValueError("게임 폴더를 선택하세요.")
        target = engine.validate_target(Path(self.target.get()))
        if self.native_mode:
            executables = engine.detect_native_executables(target)
            engine.detect_native_config(target, executables.keys())
            profile = None
        else:
            profile = PROFILE_BY_TITLE.get(self.profile_title.get())
            if not profile or profile not in detect_profiles(target, self.manifest):
                raise ValueError("지원하는 게임 종류를 선택하세요. 원본 파일 버전이 다르면 설치할 수 없습니다.")
        if self.native_mode:
            cjk_exe, legacy = None, None
            standalone = engine.ROOT / "standalone-font.dll"
        elif self.experimental:
            if self.auto_source.get():
                if download_directory is None:
                    raise ValueError("Temporary CJK download folder is missing.")
                cjk_exe = download_verified_exe(
                    Path(download_directory) / "Fallout2.exe", self.manifest["cjk_exe_sha256"])
            else:
                cjk_exe = _matching_file(self.cjk_folder.get(), "Fallout2.exe",
                                         self.manifest["cjk_exe_sha256"])
                if cjk_exe is None:
                    raise ValueError("검증된 CJK 실행 파일을 선택하거나 자동 다운로드를 켜세요.")
            legacy = None
            standalone = engine.ROOT / "standalone-font.dll"
        else:
            if not self.cjk_folder.get():
                raise ValueError("CJK 원본 폴더를 선택하세요.")
            cjk_exe, legacy = find_cjk_files(self.cjk_folder.get(), self.manifest)
            if cjk_exe is None or legacy is None:
                raise ValueError("CJK 원본 폴더를 선택하세요. FO2_UPU_CHT_v34의 EXE와 DLL이 필요합니다.")
            standalone = None
        # Korean text drawing needs the game/CJK font bridge, not sfall.
        # ExtraCRC is managed automatically; advanced settings cover mod-specific HRP fixes.
        engine.inspect_sfall(target, self.manifest)

        stock = None
        if not self.native_mode:
            profile_spec = self.manifest["profiles"][profile]
            game_exe = target / profile_spec["exe"]
        if not self.native_mode and sha(game_exe.read_bytes()) != self.manifest["stock_sha256"]:
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
            standalone_font=standalone,
            native_exe=self.native_mode,
            base_exe=stock, keep_menu_settings=(self.keep_menu.get() or self.native_mode),
            configure_sfall=self.configure_sfall.get(), dry_run=dry_run)

    def _install(self):
        try:
            if self.experimental and not self.native_mode and self.auto_source.get():
                if not messagebox.askyesno(
                    "CJK 실행 파일 임시 다운로드",
                    "자체 한글 렌더러는 중국어 글꼴 DLL을 사용하지 않습니다.\n"
                    "다만 현재는 기존 CJK EXE의 엔진 훅 코드가 필요합니다.\n\n"
                    "NovaRain의 공식 GitHub 저장소에서 원본 EXE를 임시로 받아 "
                    "SHA-256을 검증하고 설치 후 임시 파일을 삭제할까요?\n"
                    "기존 게임 파일은 백업합니다.", parent=self):
                    return
            with tempfile.TemporaryDirectory(prefix="fo2k-experimental-") as temporary:
                target, arguments = self._arguments(dry_run=True, download_directory=temporary)
                self._apply_install(target, arguments)
        except (OSError, ValueError, UnicodeError, pefile.PEFormatError, KeyError) as exc:
            self._append("설치 오류: " + str(exc))
            messagebox.showerror("설치할 수 없습니다", str(exc), parent=self)

    def _apply_install(self, target, arguments):
            check = engine.install(arguments, target)
            self._append("설치 검사: " + json.dumps(check, ensure_ascii=False))
            if check["sfall_status"] == "existing-unverified":
                messagebox.showwarning("기존 sfall 버전",
                    "설치된 sfall은 유지됩니다. 기존 파일과 설정을 보존하며 "
                    "한국어 출력 연결만 적용합니다.\n"
                    "해당 sfall 버전과 수정 EXE의 실제 게임 호환성은 별도 확인이 필요합니다.",
                    parent=self)
            setting_notice = ("기존 ddraw.ini에 한국어 EXE용 ExtraCRC를 추가합니다.\n"
                              if check.get("sfall_crc_added") else
                              "기존 sfall의 CRC 설정은 변경하지 않습니다.\n")
            if not messagebox.askyesno("설치 확인",
                    "선택한 게임 폴더에 한국어 출력 엔진을 설치합니다.\n"
                    + ("중국어 폰트 DLL 없이 자체 렌더러를 사용합니다.\n"
                       if self.experimental else "")
                    + setting_notice +
                    "수정되는 원본 파일은 자동 백업합니다. 계속할까요?", parent=self):
                return
            arguments.dry_run = False
            outcome = engine.install(arguments, target)
            self._append("설치 완료: " + json.dumps(outcome, ensure_ascii=False))
            if self.native_mode and not outcome.get("korean_translation_detected"):
                completion = (
                    "한국어 출력 엔진을 설치했습니다.\n"
                    "현재 한국어 MSG 번역이 감지되지 않아 언어 설정은 유지했습니다.\n"
                    "한국어 번역 ZIP을 적용한 뒤 엔진을 복구하고 다시 설치하면 "
                    "한국어 언어 설정이 자동 반영됩니다."
                )
            else:
                completion = (
                    "한국어 출력 엔진을 설치했습니다.\n"
                    "별도로 적용한 한국어 번역문을 게임에서 확인하세요."
                )
            messagebox.showinfo("설치 완료", completion, parent=self)
            self.summary.set("설치 완료 · 필요하면 복구 버튼으로 원상 복구할 수 있습니다.")

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
        if self.native_mode:
            messagebox.showinfo("Fallout 2 범용 독립형 한국어 엔진",
                "① 게임을 종료하고 기존 설치 폴더를 선택하세요. Steam 설치 폴더도 지원합니다.\n"
                "② 시험용 전체 복사본 준비는 선택 사항입니다. 게임 종류나 중국어 파일 선택은 필요 없습니다.\n"
                "③ 호환 Watcom EXE를 구조 검사한 뒤 원본을 백업하고 한국어 로더를 설치합니다.\n"
                "④ 기존 sfall이 있다면 모드 설정을 유지하면서 필요한 ExtraCRC만 등록합니다.\n"
                "⑤ 별도 번역 MSG가 없는 게임은 현재 언어 설정을 유지합니다.\n"
                "⑥ 메뉴, 대화, 인벤토리, 전투 및 저장/불러오기를 직접 확인하세요.\n\n"
                "엔진 ABI가 변경되었거나 오래된 sfall과 충돌하면 안전하게 설치를 중단합니다.\n"
                "Olympus/Nevada 전용 Extended sfall을 일반 버전으로 바꾸지 마세요.\n"
                "기존 파일의 복구는 아래 복구 버튼으로 실행할 수 있습니다.",
                parent=self)
            return
        if self.experimental:
            messagebox.showinfo("독립 렌더러 시험판 안내",
                "① 기존 게임 폴더를 사용합니다. 시험용 복사본 준비는 선택 사항입니다.\n"
                "② 게임 폴더만 선택합니다.\n"
                "③ 설치 전에 외부 NovaRain 저장소의 CJK EXE 임시 다운로드를 승인합니다.\n"
                "   EXE는 SHA-256 검사 후 사용하며 중국어 글꼴 DLL은 받지 않습니다.\n"
                "④ 글꼴 출력은 자체 C++/GDI 엔진이 담당합니다.\n"
                "⑤ 실게임 한글 출력과 sfall 호환성을 시험하고 복구할 수 있습니다.\n\n"
                "아직 순정 EXE용 자체 훅이 없으므로 CJK EXE 코드에 의존합니다.\n"
                "정식 릴리즈가 아닌 시험용 설치기입니다.", parent=self)
            return
        messagebox.showinfo("간단 설치 안내",
            "① 기존 Fallout 2 / 호환 모드 폴더를 선택합니다. 복사본 준비는 선택 사항입니다.\n"
            "   sfall은 순정판 한글 출력에 필수는 아닙니다.\n"
            "   모드가 sfall을 요구하면 기존 구성을 유지하세요.\n"
            "   필요한 ExtraCRC는 기존 설정을 보존한 채 자동으로 추가합니다.\n"
            "   모드별 HiResMode 변경이 필요할 때만 고급 설정을 켜세요.\n\n"
            "② 보유한 FO2_UPU_CHT_v34의 압축을 풀고 폴더를 선택합니다.\n"
            "   EXE와 기존 글꼴 DLL이 같은 폴더에 있어야 합니다.\n\n"
            "③ 설치하기 버튼을 누릅니다.\n"
            "   전용 EXE 모드는 원본 Fallout 2 EXE를 추가로 물어볼 수 있습니다.\n\n"
            "④ 게임별 한국어 번역 패치는 별도로 적용합니다.\n"
            "   Et Tu는 Fallout1in2 폴더를 선택하세요.", parent=self)


if __name__ == "__main__":
    try:
        if "--native-self-test" in sys.argv:
            raise SystemExit(self_test(require_native=True))
        if "--self-test" in sys.argv:
            raise SystemExit(self_test())
        Installer().mainloop()
    except Exception as error:
        if "--self-test" in sys.argv or "--native-self-test" in sys.argv:
            print(error, file=sys.stderr)
            raise SystemExit(1)
        raise
