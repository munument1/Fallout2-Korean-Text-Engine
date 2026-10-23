#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <regex>
#include <string>
#include "../src/native_appearance.cpp"

static int (__cdecl* wrapFn)(const char*, int, short*, short*);
extern "C" int __cdecl KoreanWordWrap(const char* s, int w, short* p, short* n) {
    return wrapFn(s, w, p, n);
}

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) return 2;
    HMODULE dll = LoadLibraryW(argv[1]);
    if (!dll) return 3;
    auto init = reinterpret_cast<void(__cdecl*)()>(GetProcAddress(dll, "InitFont"));
    auto select = reinterpret_cast<void(__cdecl*)(int)>(GetProcAddress(dll, "SelectFont"));
    auto width = reinterpret_cast<int(__cdecl*)(const char*)>(GetProcAddress(dll, "GetTextWidth"));
    wrapFn = reinterpret_cast<decltype(wrapFn)>(GetProcAddress(dll, "KoreanWordWrap"));
    if (!init || !select || !width || !wrapFn) return 4;
    init(); select(101);
    sfallAllocate = &std::malloc;
    int messages = 0, failures = 0;
    const std::regex message(R"(^\{101\}\{[^}]*\}\{(.*)\}\s*$)");
    for (const auto& entry : std::filesystem::recursive_directory_iterator(argv[2])) {
        if (entry.path().extension() != L".msg") continue;
        std::ifstream file(entry.path(), std::ios::binary);
        std::string line;
        while (std::getline(file, line)) {
            std::smatch match;
            if (!std::regex_match(line, match, message)) continue;
            std::string text = match[1].str();
            AppearanceLine first{};
            DWORD count = 0;
            if (!appearanceWrap(text.c_str(), nullptr, &count, &first)) { ++failures; continue; }
            ++messages;
            auto* node = &first;
            size_t consumed = 0;
            for (DWORD i = 0; i < count; ++i) {
                size_t end = node->next && node->next->offset ? node->next->offset : text.size();
                if (end <= consumed || end > text.size()) { ++failures; break; }
                auto part = text.substr(consumed, end - consumed);
                if (MultiByteToWideChar(949, MB_ERR_INVALID_CHARS, part.data(), static_cast<int>(part.size()), nullptr, 0) <= 0 ||
                    width(part.c_str()) > 160) ++failures;
                consumed = end;
                node = node->next;
            }
            if (consumed != text.size() || count > 11) ++failures;
            std::printf("appearance=%d lines=%lu bytes=%zu complete=%d\n", messages, count, text.size(), consumed == text.size());
            node = first.next;
            while (node) { auto* next = node->next; std::free(node); node = next; }
        }
    }
    // Repeated construction must not reuse uninitialized offsets or links.
    for (int i = 0; i < 1000; ++i) {
        AppearanceLine first{0xcccccccc, reinterpret_cast<AppearanceLine*>(1)};
        DWORD count;
        if (!makeAppearanceLines("Short note", &count, &first, &std::malloc) || count != 1 || first.offset || first.next) ++failures;
    }
    std::printf("messages=%d failures=%d\n", messages, failures);
    return messages < 13 || failures ? 1 : 0;
}
