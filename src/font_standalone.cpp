// Experimental self-contained CP949 rasterizer for the Fallout 2 CJK font ABI.
// Copyright (c) Korean Text Engine contributors. No CJK DLL is loaded.
// Do not use in a released installer until game-level regression checks pass.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <string>
#include <vector>

namespace {
HMODULE selfModule;
std::wstring folder;
unsigned codePage = 949;
bool gameProcess = false;
bool softGreen = false;
bool softTextColors = false;
int fontId = 101;

struct Face {
    HDC dc = nullptr;
    HFONT font = nullptr;
    HGDIOBJ oldFont = nullptr;
    int height = 0;
    int step = 0;
};
Face faces[2];
bool initialized = false;

void fail(const wchar_t* message) {
    MessageBoxW(nullptr, message, L"Korean font renderer", MB_ICONERROR);
    ExitProcess(1);
}
Face& current() { return faces[fontId < 102 ? 0 : 1]; }

int nextBytes(const char* s, int available) {
    if (available >= 2 && IsDBCSLeadByteEx(codePage, static_cast<BYTE>(s[0]))) {
        wchar_t converted;
        if (MultiByteToWideChar(codePage, MB_ERR_INVALID_CHARS, s, 2, &converted, 1) == 1)
            return 2;
    }
    return 1;
}

// Fallout 2 uses 0x95 as its UI bullet (display monitor and dialog options).
// 0x95 is ALSO a valid CP949 lead byte. Treat it as a control glyph only when
// it is the first byte of a renderer string AND the remainder is independently
// valid CP949. This distinguishes a genuine CP949 pair such as 95 B0 from
// a monitor marker followed by Hangul (95 B0 A1 ...).
bool uiKnobPrefix(const char* text, int length) {
    if (!text || length < 1 || static_cast<BYTE>(text[0]) != 0x95)
        return false;
    if (length == 1)
        return true;
    return MultiByteToWideChar(codePage, MB_ERR_INVALID_CHARS,
                               text + 1, length - 1, nullptr, 0) > 0;
}

std::wstring unicode(const char* text, int length) {
    std::wstring result;
    if (!text || length <= 0) return result;
    result.reserve(length);
    // Legacy 0xFF and vanilla 0x95 are distinct Fallout UI markers.
    if (uiKnobPrefix(text, length)) {
        result.push_back(L'\x2022'); // CP1252 0x95 = bullet
        ++text;
        --length;
    } else if (static_cast<BYTE>(text[0]) == 0xff) {
        result.push_back(L'\x25cf');
        ++text;
        --length;
    }
    for (int index = 0; index < length;) {
        if (text[index] == '\t') { result.push_back(L' '); ++index; continue; }
        if (text[index] == '\n' || text[index] == '\r') { ++index; continue; }
        int width = nextBytes(text + index, length - index);
        wchar_t ch = 0;
        if (MultiByteToWideChar(codePage, MB_ERR_INVALID_CHARS, text + index, width, &ch, 1) == 1) {
            if (ch >= L' ') result.push_back(ch);
        } else if (width == 1 && IsDBCSLeadByteEx(codePage, static_cast<BYTE>(text[index])) && index + 1 == length) {
            break; // An incomplete DBCS sequence is not a drawable character.
        } else {
            result.push_back(L'?');
        }
        index += width;
    }
    return result;
}

int measuredWidth(const char* s, int length) {
    if (!initialized || !s || length <= 0) return 0;
    auto text = unicode(s, length);
    SIZE size{};
    if (text.empty()) return 0;
    if (!GetTextExtentPoint32W(current().dc, text.data(), static_cast<int>(text.size()), &size)) return 0;
    return size.cx;
}

int mapColor(int color) {
    if (!gameProcess) return color & 255;
    const auto table = reinterpret_cast<const BYTE*>(0x6a38d0);
    int index = color & 255;
    if (softGreen && index == table[992]) return table[(6 << 10) | (22 << 5) | 6];
    if (!softTextColors || index == 0 || index >= 229) return index;
    const auto rgb = reinterpret_cast<const BYTE*>(0x51df34) + index * 3;
    int r = rgb[0] >> 1, g = rgb[1] >> 1, b = rgb[2] >> 1;
    int peak = std::max(r, std::max(g, b)), low = std::min(r, std::min(g, b));
    if (peak < 16) return index;
    if (peak - low >= 4) {
        r = (r * 4 + peak + 2) / 5; g = (g * 4 + peak + 2) / 5; b = (b * 4 + peak + 2) / 5;
        if (peak > 22) {
            r = (r * 22 + peak / 2) / peak;
            g = (g * 22 + peak / 2) / peak;
            b = (b * 22 + peak / 2) / peak;
        }
    } else {
        if (peak <= 25) return index;
        r = (r * 25 + peak / 2) / peak;
        g = (g * 25 + peak / 2) / peak;
        b = (b * 25 + peak / 2) / peak;
    }
    return table[(r << 10) | (g << 5) | b];
}

void cleanup() {
    for (auto& face : faces) {
        if (face.dc && face.oldFont) SelectObject(face.dc, face.oldFont);
        if (face.font) DeleteObject(face.font);
        if (face.dc) DeleteDC(face.dc);
        face = Face{};
    }
    for (auto name : {L"Galmuri9.ttf", L"Galmuri11.ttf"}) {
        RemoveFontResourceExW((folder + L"fonts\\" + name).c_str(), FR_PRIVATE, nullptr);
    }
    initialized = false;
}

bool splitText(const char* text, short* starts, short* count, int maxWidth) {
    if (!text || !starts || !count || maxWidth <= 0) return false;
    const int length = static_cast<int>(strlen(text));
    if (length > 32767 || !initialized) return false;
    starts[0] = 0; *count = 1;
    int start = 0;
    while (start < length) {
        int end = start, lastSpace = -1;
        while (end < length) {
            if (text[end] == '\n' || text[end] == '\r') break;
            int charSize = end == 0 && uiKnobPrefix(text, length)
                               ? 1 : nextBytes(text + end, length - end);
            if (measuredWidth(text + start, end + charSize - start) > maxWidth) break;
            if (text[end] == ' ') lastSpace = end;
            end += charSize;
        }
        if (end == start) end = start + nextBytes(text + start, length - start);
        else if (end < length && text[end] != '\r' && text[end] != '\n' && lastSpace > start)
            end = lastSpace + 1;
        if (end < length && text[end] == '\r') ++end;
        if (end < length && text[end] == '\n') ++end;
        if (*count >= 64) return false;
        starts[(*count)++] = static_cast<short>(end);
        start = end;
    }
    if (*count == 1) starts[(*count)++] = 0;
    return true;
}
} // namespace

extern "C" __declspec(dllexport) int __cdecl IsGameUiKnobPrefix(const char* text, int length) {
    return uiKnobPrefix(text, length) ? 1 : 0;
}

extern "C" void __cdecl InitFont() {
    if (initialized) return;
    wchar_t path[MAX_PATH];
    if (!GetModuleFileNameW(selfModule, path, MAX_PATH)) fail(L"Cannot resolve font DLL path.");
    folder = path; folder.resize(folder.find_last_of(L"\\/") + 1);
    auto ini = folder + L"fallout2font.ini";
    codePage = GetPrivateProfileIntW(L"MISC", L"CodePage", 949, ini.c_str());
    if (!IsValidCodePage(codePage)) fail(L"Unsupported font code page.");
    softGreen = GetPrivateProfileIntW(L"MISC", L"SoftGreen", 0, ini.c_str()) != 0;
    softTextColors = GetPrivateProfileIntW(L"MISC", L"SoftTextColors", 0, ini.c_str()) != 0;
    int adjust = GetPrivateProfileIntW(L"MISC", L"Adjust", 0, ini.c_str());
    for (auto name : {L"Galmuri9.ttf", L"Galmuri11.ttf"}) {
        auto file = folder + L"fonts\\" + name;
        if (GetFileAttributesW(file.c_str()) == INVALID_FILE_ATTRIBUTES ||
            !AddFontResourceExW(file.c_str(), FR_PRIVATE, nullptr)) fail(L"Required Galmuri font missing.");
    }
    for (int i = 0; i != 2; ++i) {
        auto section = i ? L"BUTTON" : L"TEXT";
        wchar_t name[128];
        GetPrivateProfileStringW(section, L"Name", i ? L"Galmuri11" : L"Galmuri9", name, 128, ini.c_str());
        int size = GetPrivateProfileIntW(section, L"Size", i ? 14 : 10, ini.c_str());
        int weight = GetPrivateProfileIntW(section, L"Weight", i ? 600 : 400, ini.c_str());
        if (size < 6 || size > 64 || weight < 0 || weight > 1000) fail(L"Invalid font size/weight.");
        auto& face = faces[i];
        face.dc = CreateCompatibleDC(nullptr);
        face.font = CreateFontW(-size, 0, 0, 0, weight, FALSE, FALSE, FALSE,
                               DEFAULT_CHARSET, OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS,
                               NONANTIALIASED_QUALITY, DEFAULT_PITCH, name);
        if (!face.dc || !face.font) fail(L"Cannot initialize raster font.");
        face.oldFont = SelectObject(face.dc, face.font);
        TEXTMETRICW tm{};
        if (!GetTextMetricsW(face.dc, &tm)) fail(L"Cannot measure raster font.");
        face.height = tm.tmHeight;
        // A larger glyph must never overlap the following line, even if the
        // old CJK DLL's negative spacing correction was requested in the INI.
        face.step = std::max(face.height, face.height + adjust - 1);
        SetBkMode(face.dc, OPAQUE);
        SetBkColor(face.dc, RGB(0, 0, 0));
        SetTextColor(face.dc, RGB(255, 255, 255));
        SetTextAlign(face.dc, TA_LEFT | TA_TOP | TA_NOUPDATECP);
    }
    // Unlike the CJK adapter, no game PE or imported DLL is altered here.
    auto game = reinterpret_cast<BYTE*>(GetModuleHandleW(nullptr));
    auto dos = reinterpret_cast<IMAGE_DOS_HEADER*>(game);
    if (dos->e_magic == IMAGE_DOS_SIGNATURE) {
        auto nt = reinterpret_cast<IMAGE_NT_HEADERS32*>(game + dos->e_lfanew);
        gameProcess = reinterpret_cast<uintptr_t>(game) == 0x400000 &&
                      nt->OptionalHeader.SizeOfImage >= 0x300000 &&
                      *reinterpret_cast<DWORD*>(game + 0xcaf23) == 0x00225559;
    }
    initialized = true;
}

extern "C" void __cdecl ClearFont() { cleanup(); }
extern "C" void __cdecl SelectFont(int id) { fontId = id; }
extern "C" int __cdecl GetTextWidth(const char* text) {
    return text ? measuredWidth(text, static_cast<int>(strlen(text))) : 0;
}
extern "C" int __cdecl GetTextHeight() { return initialized ? current().height : 0; }
extern "C" int __cdecl SplitText(const char* s, short* starts, short* count, int w) {
    return splitText(s, starts, count, w) ? 0 : 1;
}

extern "C" void __cdecl TextOutput(const char* s, int w, int pitch, unsigned char* dst, int color) {
    if (!initialized || !s || !dst || w <= 0 || pitch <= 0) return;
    auto text = unicode(s, static_cast<int>(strlen(s)));
    if (text.empty()) return;
    auto& face = current();
    int width = std::min({w, pitch, measuredWidth(s, static_cast<int>(strlen(s)))});
    int height = face.height;
    if (width <= 0 || width > 8192 || height <= 0 || height > 128) return;
    BITMAPINFO bitmap{};
    bitmap.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bitmap.bmiHeader.biWidth = width;
    bitmap.bmiHeader.biHeight = -height; // top-down GDI buffer
    bitmap.bmiHeader.biPlanes = 1;
    bitmap.bmiHeader.biBitCount = 32;
    bitmap.bmiHeader.biCompression = BI_RGB;
    void* pixels = nullptr;
    auto dib = CreateDIBSection(face.dc, &bitmap, DIB_RGB_COLORS, &pixels, nullptr, 0);
    if (!dib || !pixels) { if (dib) DeleteObject(dib); return; }
    HGDIOBJ previous = SelectObject(face.dc, dib);
    PatBlt(face.dc, 0, 0, width, height, BLACKNESS);
    TextOutW(face.dc, 0, 0, text.data(), static_cast<int>(text.size()));
    GdiFlush();
    int ink = mapColor(color);
    auto source = static_cast<const DWORD*>(pixels);
    for (int y = 0; y < height; ++y)
        for (int x = 0; x < width; ++x)
            if ((source[static_cast<size_t>(y) * width + x] & 0x00ffffff) != 0)
                dst[static_cast<size_t>(y) * pitch + x] = static_cast<BYTE>(ink);
    SelectObject(face.dc, previous);
    DeleteObject(dib);
}

extern "C" void __cdecl TextOutputL(const char* text, int w, int pitch, int* lines,
                                      unsigned char* dst, int color) {
    if (!text || !lines || !dst || *lines < 0 || w <= 0 || pitch <= 0 || !initialized) return;
    short starts[64]{}, count = 0;
    if (!splitText(text, starts, &count, w)) return;
    for (int i = 1; i < count; ++i) {
        std::string line(text + starts[i - 1], starts[i] - starts[i - 1]);
        TextOutput(line.c_str(), w, pitch, dst + static_cast<size_t>(*lines) * current().step * pitch, color);
        ++*lines;
    }
}

extern "C" int __cdecl TextOutputX(const char* text, int* offset, int* rect, int pitch,
                                     unsigned char* dst, int color) {
    if (!text || !rect || !dst || pitch <= 0 || !initialized ||
        rect[0] < 0 || rect[1] < 0 || rect[2] <= rect[0]) return 0;
    const int length = static_cast<int>(strlen(text));
    int initial = offset ? *offset : 0;
    if (initial < 0 || initial > length) return rect[1];
    short starts[64]{}, count = 0;
    int width = rect[2] - rect[0];
    if (!splitText(text + initial, starts, &count, width)) return rect[1];
    int consumed = 0;
    for (int i = 1; i < count; ++i) {
        if (rect[1] + current().height > rect[3]) break;
        std::string line(text + initial + starts[i - 1], starts[i] - starts[i - 1]);
        TextOutput(line.c_str(), width, pitch, dst + static_cast<size_t>(rect[1]) * pitch, color);
        rect[1] += current().step;
        consumed = starts[i];
    }
    if (offset) *offset = initial + consumed < length ? initial + consumed : 0;
    return rect[1];
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) { selfModule = module; DisableThreadLibraryCalls(module); }
    return TRUE;
}
