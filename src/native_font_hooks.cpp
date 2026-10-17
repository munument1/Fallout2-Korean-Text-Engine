// Fallout 2 US 1.02d native font-manager adapter.
// Completely original adapter for the Watcom register calling convention.
// No CJK game executable or Chinese DLL code is embedded or copied.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <string>
#ifdef KOREAN_WRAP_TRACE
#include <cstdio>
#endif

extern "C" void __cdecl InitFont();
extern "C" void __cdecl SelectFont(int);
extern "C" int __cdecl GetTextWidth(const char*);
extern "C" int __cdecl GetTextHeight();
extern "C" void __cdecl TextOutput(const char*, int, int, BYTE*, int);
extern "C" int __cdecl IsGameUiKnobPrefix(const char*, int);

namespace {
constexpr uintptr_t kGameBase = 0x400000;
constexpr uintptr_t kModernManager = 0x518688;
constexpr uintptr_t kRegisteredManagers = 0x6ADBD0;
constexpr uintptr_t kRegisteredCount = 0x51E3B4;
constexpr uintptr_t kCurrentFont = 0x51E3B0;
constexpr uintptr_t kGlobalFontCallbacks = 0x51E3B8;
constexpr uintptr_t kOriginalSetCurrent = 0x442120;
constexpr uintptr_t kOriginalWordWrap = 0x4BC6F0;
constexpr unsigned char kWordWrapPrologue[] = {0x56, 0x57, 0x55, 0x83, 0xEC, 0x0C};

struct FontManager {
    int minFont;
    int maxFont;
    void* setCurrent;
    void* draw;
    void* height;
    void* width;
    void* charWidth;
    void* monoWidth;
    void* letterSpacing;
    void* bufferSize;
    void* monoCharWidth;
};
static_assert(sizeof(FontManager) == 44, "Unexpected x86 FontManager layout");

volatile LONG installed = 0;
#ifdef KOREAN_WRAP_TRACE
void traceWrap(const char* phase, const void* string, int width, const void* points, const void* count) {
    char dir[MAX_PATH]{};
    if (!GetTempPathA(MAX_PATH, dir)) return;
    strcat_s(dir, "fallout2-korean-wraptrace.log");
    HANDLE file = CreateFileA(dir, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                              OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return;
    char message[240]{};
    int len = snprintf(message, sizeof(message), "%s text=%p width=%d breakpoints=%p count=%p\r\n",
                       phase, string, width, points, count);
    DWORD written = 0;
    if (len > 0) WriteFile(file, message, static_cast<DWORD>(len < 238 ? len : 238), &written, nullptr);
    CloseHandle(file);
}
#endif

int __cdecl charWidth(int character) {
    char text[3]{};
    unsigned int cp = static_cast<unsigned int>(character);
    if (cp > 255) {
        text[0] = static_cast<char>((cp >> 8) & 255);
        text[1] = static_cast<char>(cp & 255);
    } else {
        text[0] = static_cast<char>(cp & 255);
    }
    return GetTextWidth(text);
}

int __cdecl bufferSize(const char* text) {
    if (!text) return 0;
    const int width = GetTextWidth(text);
    const int height = GetTextHeight();
    if (width < 0 || height < 0 || width > 32767 || height > 128) return 0;
    return width * height;
}

int __cdecl monoCharacterWidth() {
    // The largest Hangul syllable fits within the fullwidth cell.
    return GetTextWidth("\xB0\xA1");
}

bool inGame() {
    auto* image = reinterpret_cast<const BYTE*>(kGameBase);
    if (*reinterpret_cast<const WORD*>(image) != IMAGE_DOS_SIGNATURE) return false;
    auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(image);
    if (dos->e_lfanew <= 0 || dos->e_lfanew > 1024) return false;
    auto* pe = reinterpret_cast<const IMAGE_NT_HEADERS32*>(image + dos->e_lfanew);
    // On compatible Fallout 2 variants the enlarged .rsrc section moves our
    // independent loader. Verify the hook targets the actual .krinit section
    // instead of relying on the old fixed sfall/CJK jump displacement.
    if (pe->Signature != IMAGE_NT_SIGNATURE || pe->OptionalHeader.SizeOfImage < 0x300000 ||
        pe->FileHeader.NumberOfSections != 7)
        return false;
    const auto* sections = IMAGE_FIRST_SECTION(pe);
    const auto& nativeSection = sections[6];
    if (std::memcmp(nativeSection.Name, ".krinit", 7) != 0 ||
        nativeSection.Misc.VirtualSize != 0x1000 ||
        nativeSection.SizeOfRawData != 0x1000 ||
        *reinterpret_cast<const BYTE*>(0x4CAF22) != 0xE9)
        return false;
    const int32_t displacement = *reinterpret_cast<const int32_t*>(0x4CAF23);
    const uintptr_t target = 0x4CAF27 + displacement;
    return target == kGameBase + nativeSection.VirtualAddress + 0x480 &&
           *reinterpret_cast<const WORD*>(target) == 0x609c;
}

bool writeManager(FontManager* manager, FontManager const& replacement) {
    DWORD oldProtection;
    if (!VirtualProtect(manager, sizeof(*manager), PAGE_READWRITE, &oldProtection))
        return false;
    std::memcpy(manager, &replacement, sizeof(*manager));
    DWORD unused;
    VirtualProtect(manager, sizeof(*manager), oldProtection, &unused);
    return true;
}

bool installWordWrapHook(void* callback) {
    auto* function = reinterpret_cast<BYTE*>(kOriginalWordWrap);
    // Other hooks or different game builds may alter this function.
    // Never force-install over an unfamiliar prologue.
    if (std::memcmp(function, kWordWrapPrologue, sizeof(kWordWrapPrologue)) != 0)
        return false;
    DWORD old = 0;
    if (!VirtualProtect(function, 5, PAGE_EXECUTE_READWRITE, &old))
        return false;
    BYTE jump[5] = {0xE9};
    auto from = reinterpret_cast<uintptr_t>(function) + sizeof(jump);
    auto to = reinterpret_cast<uintptr_t>(callback);
    *reinterpret_cast<int32_t*>(&jump[1]) = static_cast<int32_t>(to - from);
    std::memcpy(function, jump, sizeof(jump));
    FlushInstructionCache(GetCurrentProcess(), function, sizeof(jump));
    DWORD ignored;
    VirtualProtect(function, 5, old, &ignored);
    return true;
}
}

// Watcom: font in EAX, registers otherwise preserved.
extern "C" __declspec(naked) void __cdecl NativeSetCurrent() {
    __asm {
        pushad
        push eax
        call SelectFont
        add esp, 4
        popad
        push 0442120h
        ret
    }
}

// Watcom: dest=EAX, CP949 source=EDX, pixel limit=EBX, pitch=ECX,
// color=[ESP+4]. The callee removes one pushed color parameter.
extern "C" __declspec(naked) void __cdecl NativeDrawText() {
    __asm {
        pushad
        mov ebp, esp
        push dword ptr [ebp+36]
        push dword ptr [ebp+28]
        push dword ptr [ebp+24]
        push dword ptr [ebp+16]
        push dword ptr [ebp+20]
        call TextOutput
        add esp, 20
        popad
        ret 4
    }
}

extern "C" __declspec(naked) void __cdecl NativeStringWidth() {
    __asm {
        pushad
        push dword ptr [esp+28]
        call GetTextWidth
        add esp, 4
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(naked) void __cdecl NativeCharacterWidth() {
    __asm {
        pushad
        push dword ptr [esp+28]
        call charWidth
        add esp, 4
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(naked) void __cdecl NativeBufferSize() {
    __asm {
        pushad
        push dword ptr [esp+28]
        call bufferSize
        add esp, 4
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(naked) void __cdecl NativeMonospaceCell() {
    __asm {
        pushad
        call monoCharacterWidth
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(naked) void __cdecl NativeHeight() {
    __asm {
        pushad
        call GetTextHeight
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(naked) void __cdecl NativeLetterSpacing() {
    __asm { xor eax, eax }
    __asm { ret }
}

// Original wordWrap scans individual 8-bit bytes and can bisect CP949
// syllables. Rewrite byte boundaries using Windows CP949 lead/trail decoding.
// The returned offsets are still byte offsets, as required by Fallout 2.
extern "C" __declspec(dllexport) int __cdecl KoreanWordWrap(
    const char* text, int maxWidth, short* positions, short* count) {
#ifdef KOREAN_WRAP_TRACE
    traceWrap("ENTER", text, maxWidth, positions, count);
#endif
    if (!text || !positions || !count || maxWidth <= 0) return -1;
    const size_t bytes = strnlen(text, 32768);
    if (bytes > 32767 || bytes == 32768) return -1;

    // Match the Fallout 2 WORD_WRAP_MAX_COUNT layout.
    positions[0] = 0;
    for (int i = 1; i < 64; ++i) positions[i] = -1;
    *count = 1;
    if (bytes == 0) { positions[1] = 0; *count = 2; return 0; }

    size_t start = 0;
    while (start < bytes) {
#ifdef KOREAN_WRAP_TRACE
        traceWrap("LINE", text, static_cast<int>(start), positions, count);
#endif
        size_t next = start;
        size_t lastSpace = static_cast<size_t>(-1);
        while (next < bytes) {
            if (text[next] == '\r' || text[next] == '\n') break;
            int charLen = 1;
            BYTE lead = static_cast<BYTE>(text[next]);
            if (next == 0 && IsGameUiKnobPrefix(text, static_cast<int>(bytes))) {
                charLen = 1;
            } else if (next + 1 < bytes && IsDBCSLeadByteEx(949, lead)) {
                wchar_t decoded;
                if (MultiByteToWideChar(949, MB_ERR_INVALID_CHARS, text + next, 2, &decoded, 1) == 1)
                    charLen = 2;
            }
            std::string segment(text + start, next + charLen - start);
            if (GetTextWidth(segment.c_str()) > maxWidth) {
                // At least one character per line, even if it is wider
                // than the available box. Never split a multibyte syllable.
                if (next == start) next += charLen;
                else if (lastSpace != static_cast<size_t>(-1) && lastSpace > start)
                    next = lastSpace + 1;
                break;
            }
            if (text[next] == ' ' || text[next] == '-') lastSpace = next;
            next += charLen;
        }
        if (next < bytes && text[next] == '\r') ++next;
        if (next < bytes && text[next] == '\n') ++next;
        if (next <= start || *count >= 64) return -1;
        positions[(*count)++] = static_cast<short>(next);
        start = next;
    }
#ifdef KOREAN_WRAP_TRACE
    traceWrap("EXIT", text, static_cast<int>(*count), positions, count);
#endif
    return 0;
}

extern "C" __declspec(dllexport) int __cdecl KoreanWordWrapForCaller(
    const char* text, int maxWidth, short* positions, short* count,
    uintptr_t returnAddress) {
    // Never discard text solely because the UI card has a limited height.
    // Doing so regressed content visibility relative to existing Korean
    // translations. Retain all valid CP949 line offsets for every caller;
    // reflow/layout must be handled separately, without truncation.
    (void)returnAddress;
    return KoreanWordWrap(text, maxWidth, positions, count);
}

// Watcom wordWrap(string=EAX, width=EDX, startPtrs=EBX, countPtr=ECX).
extern "C" __declspec(dllexport, naked) void __cdecl NativeWordWrap() {
    __asm {
        pushad
        // Snapshot ESP: each PUSH changes it, so relative addressing
        // from ESP during argument construction corrupts subsequent args.
        mov ebp, esp
        push dword ptr [ebp+32] // caller return address, for scoped UI layout
        push dword ptr [ebp+24] // ECX: count pointer
        push dword ptr [ebp+16] // EBX: breakpoints pointer
        push dword ptr [ebp+20] // EDX: width
        push dword ptr [ebp+28] // EAX: string
        call KoreanWordWrapForCaller
        add esp, 20
        // The original routine writes the return status into EBX and
        // immediately copies it to EAX; both must reflect the same value.
        mov [esp+16], eax
        mov [esp+28], eax
        popad
        ret
    }
}

extern "C" __declspec(dllexport) void __cdecl InitKoreanEngine() {
    if (!inGame()) return;
    if (InterlockedCompareExchange(&installed, 1, 0) != 0) return;
    InitFont();
    FontManager* source = reinterpret_cast<FontManager*>(kModernManager);
    if (source->minFont != 100 || source->maxFont != 110 ||
        reinterpret_cast<uintptr_t>(source->setCurrent) != kOriginalSetCurrent) {
        InterlockedExchange(&installed, 0);
        return;
    }
    FontManager adapted = *source;
    adapted.setCurrent = reinterpret_cast<void*>(&NativeSetCurrent);
    adapted.draw = reinterpret_cast<void*>(&NativeDrawText);
    adapted.height = reinterpret_cast<void*>(&NativeHeight);
    adapted.width = reinterpret_cast<void*>(&NativeStringWidth);
    adapted.charWidth = reinterpret_cast<void*>(&NativeCharacterWidth);
    adapted.monoWidth = reinterpret_cast<void*>(&NativeStringWidth);
    adapted.letterSpacing = reinterpret_cast<void*>(&NativeLetterSpacing);
    adapted.bufferSize = reinterpret_cast<void*>(&NativeBufferSize);
    adapted.monoCharWidth = reinterpret_cast<void*>(&NativeMonospaceCell);
    if (!writeManager(source, adapted)) {
        InterlockedExchange(&installed, 0);
        return;
    }
    // If Fallout 2 copied the manager into its registry before we loaded,
    // update that copy as well. Otherwise its later registration uses 'source'.
    const int count = *reinterpret_cast<volatile int*>(kRegisteredCount);
    if (count >= 0 && count <= 10) {
        auto managers = reinterpret_cast<FontManager*>(kRegisteredManagers);
        for (int n = 0; n < count; ++n) {
            if (managers[n].minFont == 100 && managers[n].maxFont == 110)
                writeManager(&managers[n], adapted);
        }
        int current = *reinterpret_cast<volatile int*>(kCurrentFont);
        if (current >= 100 && current <= 110) {
            auto globals = reinterpret_cast<void**>(kGlobalFontCallbacks);
            DWORD old;
            if (VirtualProtect(globals, 8 * sizeof(void*), PAGE_READWRITE, &old)) {
                globals[0] = adapted.draw;
                globals[1] = adapted.height;
                globals[2] = adapted.width;
                globals[3] = adapted.charWidth;
                globals[4] = adapted.monoWidth;
                globals[5] = adapted.letterSpacing;
                globals[6] = adapted.bufferSize;
                globals[7] = adapted.monoCharWidth;
                DWORD ignored;
                VirtualProtect(globals, 8 * sizeof(void*), old, &ignored);
                SelectFont(current);
            }
        }
    }
    OutputDebugStringA("Fallout2 Korean Engine: registered native Watcom font adapter\n");
    if (!installWordWrapHook(reinterpret_cast<void*>(&NativeWordWrap)))
        OutputDebugStringA("Fallout2 Korean Engine: word wrapping hook was not installed\n");
}
