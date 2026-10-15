@echo off
where cl >nul 2>nul
if errorlevel 1 (echo Run from an x86 Visual Studio Developer Command Prompt & exit /b 1)
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /O2 /MT /LD /utf-8 src\font_minimal.cpp /link /Brepro /DEF:src\font_bridge.def /OUT:fallout2font.dll gdi32.lib user32.lib
