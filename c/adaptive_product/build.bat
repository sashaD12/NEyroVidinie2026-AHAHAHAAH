@echo off
setlocal
cd /d "%~dp0"

where clang >nul 2>nul
if %errorlevel%==0 (
  set CC=clang
  goto build
)

where gcc >nul 2>nul
if %errorlevel%==0 (
  set CC=gcc
  goto build
)

echo Looking for llvm-mingw...
for /d %%D in ("%ProgramFiles%\llvm-mingw*") do (
  if exist "%%D\bin\clang.exe" (
    set "PATH=%%D\bin;%PATH%"
    set CC=clang
    goto build
  )
)
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW.UCRT*") do (
  for /d %%E in ("%%D\llvm-mingw*") do (
    if exist "%%E\bin\clang.exe" (
      set "PATH=%%E\bin;%PATH%"
      set CC=clang
      goto build
    )
  )
)

echo No C compiler found. Install LLVM-MinGW or GCC first.
exit /b 1

:build
if not exist bin mkdir bin
echo Using %CC%
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/config.c -o src/config.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/assess.c -o src/assess.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/decide.c -o src/decide.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/select.c -o src/select.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/routes.c -o src/routes.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/pipeline.c -o src/pipeline.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/timing.c -o src/timing.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party -c src/io_stb.c -o src/io_stb.o
llvm-ar rcs libadaptive.a src/config.o src/assess.o src/decide.o src/select.o src/routes.o src/pipeline.o src/timing.o src/io_stb.o 2>nul
if errorlevel 1 ar rcs libadaptive.a src/config.o src/assess.o src/decide.o src/select.o src/routes.o src/pipeline.o src/timing.o src/io_stb.o
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party apps/ad_enhance.c -o bin/ad_enhance.exe libadaptive.a -lm
%CC% -std=c11 -O2 -Wall -Wextra -Iinclude -Ithird_party tests/test_core.c -o bin/test_core.exe libadaptive.a -lm
echo Build OK
bin\test_core.exe
exit /b %errorlevel%
