// Windows x86 build-time probe for the independent CJK font ABI.
// Uses no original Fallout binaries and fails if a legacy Chinese DLL is loaded.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <algorithm>
#include <cstdio>
#include <string>
#include <vector>

int wmain(int argc, wchar_t** argv) {
    if (argc != 2) return 2;
    HMODULE dll = LoadLibraryW(argv[1]);
    if (!dll) { printf("load_error=%lu\n", GetLastError()); return 3; }
    auto init = reinterpret_cast<void(__cdecl*)()>(GetProcAddress(dll, "InitFont"));
    auto clear = reinterpret_cast<void(__cdecl*)()>(GetProcAddress(dll, "ClearFont"));
    auto select = reinterpret_cast<void(__cdecl*)(int)>(GetProcAddress(dll, "SelectFont"));
    auto getWidth = reinterpret_cast<int(__cdecl*)(const char*)>(GetProcAddress(dll, "GetTextWidth"));
    auto getHeight = reinterpret_cast<int(__cdecl*)()>(GetProcAddress(dll, "GetTextHeight"));
    auto output = reinterpret_cast<void(__cdecl*)(const char*, int, int, BYTE*, int)>(GetProcAddress(dll, "TextOutput"));
    auto split = reinterpret_cast<int(__cdecl*)(const char*, short*, short*, int)>(GetProcAddress(dll, "SplitText"));
    auto outputL = reinterpret_cast<void(__cdecl*)(const char*, int, int, int*, BYTE*, int)>(GetProcAddress(dll, "TextOutputL"));
    auto outputX = reinterpret_cast<int(__cdecl*)(const char*, int*, int*, int, BYTE*, int)>(GetProcAddress(dll, "TextOutputX"));
    if (!init || !clear || !select || !getWidth || !getHeight || !output || !split || !outputL || !outputX) return 4;
    init();
    if (GetModuleHandleW(L"fallout2font_legacy.dll")) return 5;
    int failures = 0;
    for (int id : {101, 103}) {
        select(id);
        int height = getHeight();
        printf("font=%d height=%d\n", id, height);
        if (height < 6 || height > 64) ++failures;
        if (getWidth("Hello\r\n") != getWidth("Hello") || getWidth("\r") != 0) ++failures;
        std::string hangul;
        // Full 11,172 modern Hangul syllables and CP949 extension trail bytes.
        for (wchar_t ch = 0xac00; ch <= 0xd7a3; ++ch) {
            char mb[8]{};
            int n = WideCharToMultiByte(949, WC_NO_BEST_FIT_CHARS, &ch, 1, mb, sizeof(mb), nullptr, nullptr);
            if (n < 1) { ++failures; break; }
            hangul.append(mb, n);
        }
        for (size_t offset = 0; offset < hangul.size(); offset += 320) {
            std::string part = hangul.substr(offset, 320);
            short starts[64]{}, count = 0;
            if (split(part.c_str(), starts, &count, 200) || count < 2 || starts[count - 1] != part.size()) {
                ++failures; continue;
            }
            for (int n = 1; n < count; ++n) {
                int size = starts[n] - starts[n - 1];
                wchar_t check[512]{};
                if (size < 1 ||
                    MultiByteToWideChar(949, MB_ERR_INVALID_CHARS, part.data() + starts[n - 1], size,
                                        check, 512) <= 0 ||
                    getWidth(part.substr(starts[n - 1], size).c_str()) > 200) ++failures;
            }
        }
        wchar_t sample[] = {0xac00, 0xd7a3, 0x0041, 0x0042, 0x0000};
        char cp949[40]{};
        WideCharToMultiByte(949, 0, sample, -1, cp949, sizeof(cp949), nullptr, nullptr);
        std::vector<BYTE> buffer(256 * 90 + 64, 0);
        std::fill(buffer.end() - 64, buffer.end(), static_cast<BYTE>(0xa5));
        std::string original(cp949);
        output(cp949, 256, 256, buffer.data(), 200);
        if (original != cp949 || !std::all_of(buffer.end() - 64, buffer.end(),
                [](BYTE value) { return value == 0xa5; }) ||
            std::count(buffer.begin(), buffer.end() - 64, static_cast<BYTE>(200)) < 20) ++failures;
        int lines = 0;
        std::fill(buffer.begin(), buffer.end() - 64, static_cast<BYTE>(0));
        outputL("Hello world", 256, 256, &lines, buffer.data(), 200);
        if (lines != 1) ++failures;
        int offset = 0;
        int rect[4] = {0, 0, 256, 89};
        outputX("Hello world", &offset, rect, 256, buffer.data(), 200);
        if (offset != 0 || rect[1] <= 0) ++failures;
    }
    clear();
    if (GetModuleHandleW(L"fallout2font_legacy.dll")) ++failures;
    printf("modern_hangul=11172 legacy_dll=absent failures=%d\n", failures);
    FreeLibrary(dll);
    return failures ? 1 : 0;
}
