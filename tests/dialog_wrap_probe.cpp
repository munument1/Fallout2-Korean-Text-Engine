// Read-only regression probe for authentic, owner-supplied CP949 dialog .msg.
// No translated text is shipped with this executable.
//
// Usage: dialog_wrap_probe.exe <native-font.dll> <dialog-folder> [limit]
// Default: up to 2500 verified, nonempty messages (across multiple .msg files).
// The test deliberately includes long NPC lines and potential player choices.
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

struct Metrics {
    int checked = 0;
    int failed = 0;
    int invalidCp949 = 0;
    int tooLong = 0;
    int files = 0;
    int maxLines = 0;
    int maxBytes = 0;
};

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) return 2;
    HMODULE module = LoadLibraryW(argv[1]);
    if (!module) return 3;
    auto init = reinterpret_cast<void(__cdecl*)()>(GetProcAddress(module, "InitFont"));
    auto select = reinterpret_cast<void(__cdecl*)(int)>(GetProcAddress(module, "SelectFont"));
    auto wrap = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*)>(
        GetProcAddress(module, "KoreanWordWrap"));
    auto scoped = reinterpret_cast<int(__cdecl*)(const char*, int, short*, short*, uintptr_t)>(
        GetProcAddress(module, "KoreanWordWrapForCaller"));
    if (!init || !select || !wrap || !scoped) return 4;
    init();
    select(101);

    const int limit = argc >= 4 ? std::max(1, std::min(25000, _wtoi(argv[3]))) : 2500;
    Metrics metrics;
    const std::regex msg(R"(^\{(\d+)\}\{[^}]*\}\{(.*)\}\s*$)");
    // These are deliberately conservative widths. Every break must be a CP949
    // code-point boundary and concatenation must recreate the exact original.
    const int widths[] = {175, 280};
    auto folder = std::filesystem::path(argv[2]);
    if (!std::filesystem::is_directory(folder)) return 5;
    for (auto const& entry : std::filesystem::directory_iterator(folder)) {
        if (!entry.is_regular_file() || entry.path().extension() != L".msg") continue;
        std::ifstream file(entry.path(), std::ios::binary);
        if (!file) continue;
        ++metrics.files;
        std::string line;
        while (metrics.checked < limit && std::getline(file, line)) {
            std::smatch match;
            if (!std::regex_match(line, match, msg)) continue;
            std::string text = match[2].str();
            if (text.empty()) continue;
            if (text.size() > 1000) { ++metrics.tooLong; continue; }
            if (MultiByteToWideChar(949, MB_ERR_INVALID_CHARS, text.data(),
                static_cast<int>(text.size()), nullptr, 0) <= 0) {
                ++metrics.invalidCp949;
                continue;
            }
            ++metrics.checked;
            metrics.maxBytes = std::max(metrics.maxBytes, static_cast<int>(text.size()));
            for (int width : widths) {
                short points[64]{};
                short scopedPoints[64]{};
                short count = 0, scopedCount = 0;
                int a = wrap(text.c_str(), width, points, &count);
                // Dialog calls use return addresses other than 0x43AD01.
                int b = scoped(text.c_str(), width, scopedPoints, &scopedCount, 0x456789);
                if (a != 0 || b != 0 || count < 2 || count > 64 ||
                    scopedCount != count || points[0] != 0 ||
                    points[count-1] != text.size()) {
                    ++metrics.failed;
                    continue;
                }
                metrics.maxLines = std::max(metrics.maxLines, static_cast<int>(count-1));
                for (int k = 1; k < count; ++k) {
                    int begin = points[k-1];
                    int end = points[k];
                    if (begin < 0 || end <= begin || end > text.size() ||
                        points[k] != scopedPoints[k] ||
                        MultiByteToWideChar(949, MB_ERR_INVALID_CHARS,
                            text.data() + begin, end - begin, nullptr, 0) <= 0) {
                        ++metrics.failed;
                        break;
                    }
                }
            }
        }
        if (metrics.checked >= limit) break;
    }
    std::printf("files=%d checked=%d widths=175,280 max_lines=%d max_bytes=%d invalid_cp949_skipped=%d oversized_skipped=%d failures=%d\n",
        metrics.files, metrics.checked, metrics.maxLines, metrics.maxBytes,
        metrics.invalidCp949, metrics.tooLong, metrics.failed);
    FreeLibrary(module);
    return metrics.checked < 50 || metrics.failed ? 1 : 0;
}
