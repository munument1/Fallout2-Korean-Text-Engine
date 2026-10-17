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
    auto wordWrap = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*)>(GetProcAddress(dll, "KoreanWordWrap"));
    auto scopedWordWrap = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*, uintptr_t)>(GetProcAddress(dll, "KoreanWordWrapForCaller"));
    auto isUiKnob = reinterpret_cast<int(__cdecl*)(const char*, int)>(
        GetProcAddress(dll, "IsGameUiKnobPrefix"));
    auto nativeWordWrap = GetProcAddress(dll, "NativeWordWrap");
    if (!init || !clear || !select || !getWidth || !getHeight ||
        !output || !split || !outputL || !outputX ||
        !wordWrap || !scopedWordWrap || !nativeWordWrap || !isUiKnob) return 4;
    init();
    if (GetModuleHandleW(L"fallout2font_legacy.dll")) return 5;
    int failures = 0;
    for (int id : {101, 103}) {
        select(id);
        int height = getHeight();
        printf("font=%d height=%d\n", id, height);
        if (height < 6 || height > 64) ++failures;
        if (getWidth("Hello\r\n") != getWidth("Hello") || getWidth("\r") != 0) ++failures;
        // The vanilla UI's 0x95 marker has two forms: an isolated monitor
        // marker, and a prefix before dialog options. Both must be visible.
        // Unlike 0x95 B0 (a genuine two-byte CP949 syllable), 0x95 B0 A1
        // represents the marker followed by the CP949 syllable GA.
        const char knobOnly[] = {char(0x95), '\0'};
        const char knobOption[] = {char(0x95), ' ', char(0xb0), char(0xa1), '\0'};
        const char knobHangul[] = {char(0x95), char(0xb0), char(0xa1), '\0'};
        const char realCp949[] = {char(0x95), char(0xb0), '\0'};
        const char realCp949WithText[] = {char(0x95), char(0xb0), '.', '\0'};
        const char hangulGa[] = {char(0xb0), char(0xa1), '\0'};
        const char numberedOption[] = {'1', '.', ' ', char(0xb0), char(0xa1), '\0'};
        if (!isUiKnob(knobOnly, 1) || !isUiKnob(knobOption, 4) ||
            !isUiKnob(knobHangul, 3) || isUiKnob(realCp949, 2) ||
            isUiKnob(realCp949WithText, 3) || isUiKnob(numberedOption, 5) ||
            getWidth(knobOnly) < 2 ||
            getWidth(knobHangul) <= getWidth(hangulGa) ||
            getWidth(realCp949) < 2 || getWidth(numberedOption) <= getWidth(hangulGa))
            ++failures;
        std::vector<BYTE> markerPixels(64 * 64 + 32, 0);
        std::fill(markerPixels.end() - 32, markerPixels.end(), static_cast<BYTE>(0xa5));
        output(knobOnly, 64, 64, markerPixels.data(), 200);
        if (std::count(markerPixels.begin(), markerPixels.end() - 32, static_cast<BYTE>(200)) < 2 ||
            !std::all_of(markerPixels.end() - 32, markerPixels.end(),
                    [](BYTE value) { return value == 0xa5; }))
            ++failures;
        for (auto marker : {std::string(knobOnly), std::string(knobOption),
                            std::string(knobHangul), std::string(realCp949)}) {
            short starts[64]{}, count = 0;
            if (split(marker.c_str(), starts, &count, 200) || count != 2 ||
                starts[0] != 0 || starts[1] != marker.size())
                ++failures;
            if (wordWrap(marker.c_str(), 200, starts, &count) || count != 2 ||
                starts[0] != 0 || starts[1] != marker.size())
                ++failures;
        }
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
        if (wordWrap) {
            // Fallout's stock wordWrap was byte-oriented and bisected CP949.
            // Ensure our replacement returns byte positions at valid glyph boundaries.
            std::string paragraph;
            for (int k = 0; k < 54; ++k) {
                wchar_t ch = static_cast<wchar_t>(0xac00 + k * 3);
                char tmp[4]{};
                int n = WideCharToMultiByte(949, 0, &ch, 1, tmp, 4, nullptr, nullptr);
                paragraph.append(tmp, n);
                if (k % 7 == 6) paragraph.push_back(' ');
            }
            std::vector<char> stable(paragraph.begin(), paragraph.end());
            short points[65]{}, count = 0;
            points[64] = 0x1234;  // array guard
            if (wordWrap(paragraph.c_str(), 90, points, &count) != 0 ||
                points[0] != 0 || points[count - 1] != paragraph.size() ||
                count < 3 || count > 64 || points[64] != 0x1234)
                ++failures;
            else {
                for (int n = 1; n < count; ++n) {
                    int length = points[n] - points[n - 1];
                    wchar_t decoded[512]{};
                    if (length <= 0 ||
                        MultiByteToWideChar(949, MB_ERR_INVALID_CHARS,
                                            paragraph.data() + points[n - 1],
                                            length, decoded, 512) <= 0 ||
                        getWidth(paragraph.substr(points[n - 1], length).c_str()) > 90)
                        ++failures;
                }
            }
            if (stable != std::vector<char>(paragraph.begin(), paragraph.end())) ++failures;
            if (wordWrap("", 90, points, &count) != 0 ||
                count != 2 || points[0] != 0 || points[1] != 0)
                ++failures;
            if (wordWrap(paragraph.c_str(), 0, points, &count) != -1) ++failures;
            if (scopedWordWrap) {
                std::string longText(220, 'A');
                short general[65]{}, scoped[65]{}, ordinaryCount = 0, cardCount = 0;
                int generalStatus = scopedWordWrap(longText.c_str(), 75, general, &ordinaryCount, 0x123456);
                int cardStatus = scopedWordWrap(longText.c_str(), 75, scoped, &cardCount, 0x43ad01);
                // The card caller must not lose any lines/characters.
                if (generalStatus != 0 || cardStatus != 0 || ordinaryCount <= 13 ||
                    cardCount != ordinaryCount ||
                    scoped[cardCount - 1] != longText.size()) ++failures;
                else
                    for (int k = 0; k < cardCount; ++k)
                        if (general[k] != scoped[k]) ++failures;
            }
            if (nativeWordWrap) {
                short nativePoints[65]{}, directPoints[65]{};
                short nativeCount = 0, directCount = 0;
                auto* ptrText = paragraph.c_str();
                auto* ptrPoints = nativePoints;
                auto* ptrCount = &nativeCount;
                void* entry = reinterpret_cast<void*>(nativeWordWrap);
                int eaxResult = 100, ebxResult = 100;
                int beforeESP = 0, afterESP = 0;
                __asm {
                    push ebx
                    mov eax, ptrText
                    mov edx, 90
                    mov ebx, ptrPoints
                    mov ecx, ptrCount
                    mov beforeESP, esp
                    call entry
                    mov afterESP, esp
                    mov eaxResult, eax
                    mov ebxResult, ebx
                    pop ebx
                }
                int directResult = wordWrap(paragraph.c_str(), 90, directPoints, &directCount);
                if (eaxResult != directResult || ebxResult != directResult ||
                    beforeESP != afterESP || nativeCount != directCount)
                    ++failures;
                else
                    for (int i = 0; i < nativeCount; ++i)
                        if (nativePoints[i] != directPoints[i]) ++failures;
            }
        }
    }
    clear();
    if (GetModuleHandleW(L"fallout2font_legacy.dll")) ++failures;
    printf("modern_hangul=11172 legacy_dll=absent failures=%d\n", failures);
    FreeLibrary(dll);
    return failures ? 1 : 0;
}
