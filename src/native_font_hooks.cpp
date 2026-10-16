// Fallout 2 US 1.02d native font-manager adapter.
// Completely original adapter for the Watcom register calling convention.
// No CJK game executable or Chinese DLL code is embedded or copied.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstring>

extern "C" void __cdecl InitFont();
extern "C" void __cdecl SelectFont(int);
extern "C" int __cdecl GetTextWidth(const char*);
extern "C" int __cdecl GetTextHeight();
extern "C" void __cdecl TextOutput(const char*, int, int, BYTE*, int);

namespace {
constexpr uintptr_t kGameBase = 0x400000;
constexpr uintptr_t kModernManager = 0x518688;
constexpr uintptr_t kRegisteredManagers = 0x6ADBD0;
constexpr uintptr_t kRegisteredCount = 0x51E3B4;
constexpr uintptr_t kCurrentFont = 0x51E3B0;
constexpr uintptr_t kGlobalFontCallbacks = 0x51E3B8;
constexpr uintptr_t kOriginalSetCurrent = 0x442120;

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
    // The native .krinit section must exist and the boot hook be signed.
    if (pe->Signature != IMAGE_NT_SIGNATURE || pe->OptionalHeader.SizeOfImage < 0x300000)
        return false;
    return *reinterpret_cast<const DWORD*>(0x4CAF23) == 0x00225559;
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
}
