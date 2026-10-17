// Optional owner-data regression test for authentic CP949 Fallout 2 .msg data.
// Keeps translation data outside the repository. Usage:
//   real_translation_wrap_probe.exe <fallout2font.dll> <skill.msg> [stat.msg ...]
//
// Validates that *every* character from each description survives wrapping.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <regex>
#include <string>
#include <vector>

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) return 2;
    HMODULE dll = LoadLibraryW(argv[1]);
    if (!dll) { std::printf("dll_load_failed=%lu\n", GetLastError()); return 3; }
    auto init = reinterpret_cast<void(__cdecl*)()>(GetProcAddress(dll, "InitFont"));
    auto select = reinterpret_cast<void(__cdecl*)(int)>(GetProcAddress(dll, "SelectFont"));
    auto wrap = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*)>(
        GetProcAddress(dll, "KoreanWordWrap"));
    auto cardWrap = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*, uintptr_t)>(
        GetProcAddress(dll, "KoreanWordWrapForCaller"));
    if (!init || !select || !wrap || !cardWrap) return 4;
    init();
    select(101);
    const std::regex message(R"(^\{(\d+)\}\{[^}]*\}\{(.*)\}\s*$)");
    int total = 0;
    int failures = 0;
    int maxLines = 0;
    int moreThanTwelve = 0;
    for (int arg = 2; arg < argc; ++arg) {
        std::ifstream file(std::filesystem::path(argv[arg]), std::ios::binary);
        if (!file) { ++failures; continue; }
        std::string line;
        int checked = 0;
        while (std::getline(file, line)) {
            std::smatch parts;
            if (!std::regex_match(line, parts, message)) continue;
            int id = std::atoi(parts[1].str().c_str());
            if (id < 200 || id >= 240) continue;
            std::string desc = parts[2].str();
            if (desc.empty() || desc.size() >= 30000) continue;
            if (MultiByteToWideChar(949, MB_ERR_INVALID_CHARS, desc.data(),
                    static_cast<int>(desc.size()), nullptr, 0) <= 0) {
                ++failures; continue;
            }
            short standard[64]{}, card[64]{};
            short stdCount = 0, cardCount = 0;
            int a = wrap(desc.c_str(), 175, standard, &stdCount);
            int b = cardWrap(desc.c_str(), 175, card, &cardCount, 0x43AD01);
            ++total; ++checked;
            if (a != 0 || b != 0 || stdCount < 2 || stdCount > 64 ||
                cardCount != stdCount || standard[stdCount - 1] != desc.size()) {
                ++failures; continue;
            }
            for (int i = 1; i < stdCount; ++i) {
                int offset = standard[i - 1];
                int count = standard[i] - offset;
                if (standard[i] != card[i] || count < 1 ||
                    MultiByteToWideChar(949, MB_ERR_INVALID_CHARS,
                        desc.data() + offset, count, nullptr, 0) <= 0) {
                    ++failures; break;
                }
            }
            int lines = stdCount - 1;
            maxLines = std::max(maxLines, lines);
            if (lines > 12) ++moreThanTwelve;
        }
        std::printf("file=%d descriptions=%d\n", arg - 1, checked);
    }
    std::printf("authentic_messages=%d max_lines=%d over_12_lines=%d failures=%d\n",
                total, maxLines, moreThanTwelve, failures);
    FreeLibrary(dll);
    return (total < 3 || failures) ? 1 : 0;
}
