@echo off

cls


if /i "%~1" == "-cside" (
    gcc -Iapp/core/clogger/include -Iapp/core/clogger/external -Lapp/core/clogger -shared -DLOGGER_BUILD_SHARED app/core/clogger/src/logger.c -O2 -flto -ffunction-sections -fdata-sections -Wl,--gc-sections -o clogger.dll app/core/clogger/libuv.a -lsynchronization -lws2_32 -liphlpapi -luserenv -lpsapi -lshell32 -ladvapi32 -ldbghelp -lole32 -Wl,--out-implib,app/core/clogger/libclogger.a
    strip clogger.dll
) else if /i "%~1" == "" (
    python app/main.py
)


