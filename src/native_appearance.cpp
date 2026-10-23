// CP949 adapter for the separate HeroAppearance wrapper in official sfall 4.5.1.
// The original linked list is released by sfall, so allocate with its own CRT.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstring>

extern "C" int __cdecl KoreanWordWrap(const char*, int, short*, short*);

namespace {
struct AppearanceLine { DWORD offset; AppearanceLine* next; };
using Allocate = void* (__cdecl*)(size_t);
Allocate sfallAllocate = nullptr;

bool makeAppearanceLines(const char* text, DWORD* lines, AppearanceLine* first,
                         Allocate allocate) {
    if (!text || !lines || !first || !allocate) return false;
    first->offset = 0;
    first->next = nullptr;
    *lines = 0;
    short offsets[64]{}, count = 0;
    if (KoreanWordWrap(text, 160, offsets, &count) != 0 || count < 2) return false;
    *lines = count - 1;
    if (*lines == 1) return true;
    auto* current = first;
    for (short n = 1; n < count; ++n) {
        auto* node = static_cast<AppearanceLine*>(allocate(sizeof(AppearanceLine)));
        if (!node) { *lines = 0; return false; }
        // DrawCharNote expects a zero-offset sentinel for its final substring.
        node->offset = n == count - 1 ? 0 : offsets[n];
        node->next = nullptr;
        current->next = node;
        current = node;
    }
    return true;
}

// MSVC optimizes the original static function: text=ECX, unused EDX,
// line count and first node on the stack, callee pops eight bytes.
bool __fastcall appearanceWrap(const char* text, void*, DWORD* lines, AppearanceLine* first) {
    return makeAppearanceLines(text, lines, first, sfallAllocate);
}

bool matches(const BYTE* at, const BYTE* signature, size_t bytes) {
    return std::memcmp(at, signature, bytes) == 0;
}
}

extern "C" void __cdecl InstallKoreanAppearanceHook() {
    auto* base = reinterpret_cast<BYTE*>(GetModuleHandleW(L"ddraw.dll"));
    if (!base) return;
    auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 1024) return;
    auto* pe = reinterpret_cast<IMAGE_NT_HEADERS32*>(base + dos->e_lfanew);
    if (pe->Signature != IMAGE_NT_SIGNATURE || pe->FileHeader.Machine != IMAGE_FILE_MACHINE_I386 ||
        pe->OptionalHeader.SizeOfImage != 0x118000 || pe->FileHeader.TimeDateStamp != 0x4b3d3b00) return;
    // Fingerprints contain no relocated addresses. Reject other versions/hooks.
    const BYTE wrap[] = {0x55,0x8b,0xec,0x83,0xec,0x10,0x8b,0x45,0x08,0x53,0x56,0x57,
                        0x89,0x4d,0xf4,0xc7,0x00,0x01,0x00,0x00,0x00,0x3e,0xff,0x15,
                        0xd4,0xe3,0x51,0x00,0x3d,0xa0,0x00,0x00,0x00};
    const BYTE call[] = {0x8b,0xcb,0x8d,0x45,0x18,0x57,0x50,0xe8,0xc6,0xf1,0xff,0xff};
    const BYTE allocator[] = {0x55,0x8b,0xec,0xeb,0x1f,0xff,0x75,0x08,0xe8,0xdd,0xe7,0x00,0x00};
    if (!matches(base + 0x51430, wrap, sizeof(wrap)) ||
        !matches(base + 0x5225e, call, sizeof(call)) ||
        !matches(base + 0x8733b, allocator, sizeof(allocator))) return;
    DWORD old;
    auto* target = base + 0x51430;
    if (!VirtualProtect(target, 6, PAGE_EXECUTE_READWRITE, &old)) return;
    sfallAllocate = reinterpret_cast<Allocate>(base + 0x8733b);
    BYTE jump[6] = {0xe9,0,0,0,0,0x90};
    const auto displacement = static_cast<int32_t>(reinterpret_cast<uintptr_t>(&appearanceWrap)
                                                   - reinterpret_cast<uintptr_t>(target + 5));
    std::memcpy(jump + 1, &displacement, sizeof(displacement));
    std::memcpy(target, jump, sizeof(jump));
    FlushInstructionCache(GetCurrentProcess(), target, sizeof(jump));
    DWORD ignored;
    VirtualProtect(target, 6, old, &ignored);
    OutputDebugStringA("Fallout2 Korean Engine: adapted sfall 4.5.1 appearance wrapping\n");
}
