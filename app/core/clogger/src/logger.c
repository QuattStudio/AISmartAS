#include "logger.h"

#include <uv.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>

#if defined(_WIN32)
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <intrin.h>
#elif defined(__linux__) || defined(__APPLE__)
    #include <unistd.h>
    #include <sys/utsname.h>
    #include <sys/stat.h>
    #include <sys/types.h>
    #include <errno.h>
    #if defined(__x86_64__) || defined(__i386__)
        #include <cpuid.h>
    #endif
    #if defined(__linux__)
        #include <sys/sysinfo.h>
    #endif
#endif

#define LOGGER_QUEUE_CAPACITY 1024
#define LOGGER_MESSAGE_SIZE   2048
#define LOGGER_PATH_SIZE      512
#define LOGGER_TIME_SIZE      32

typedef struct log_record
{
    log_level level;
    char timestamp[LOGGER_TIME_SIZE];
    char message[LOGGER_MESSAGE_SIZE];
} log_record;

typedef struct logger_state
{
    /* Background worker */
    uv_thread_t worker;

    /* Synchronization */
    uv_mutex_t mutex;
    uv_cond_t hasMessages;
    uv_cond_t hasSpace;
    uv_cond_t flushed;
    uv_mutex_t outputMutex;

    /* Ring buffer */
    log_record queue[LOGGER_QUEUE_CAPACITY];
    char resolvedPath[LOGGER_PATH_SIZE];
    char sessionBuf[32];

    size_t head;
    size_t tail;
    size_t count;

    /* Configuration */
    log_level minimumLevel;

    FILE* file;

    /* State */
    bool initialized;
    bool stopping;
    bool workerRunning;

    /* Flush tracking */
    uint64_t submitted;
    uint64_t completed;

    logger_metadata_obj meta;

} logger_state;

static logger_state g_logger = {0};

static bool logger_detectLittleEndian(void)
{
    uint16_t word = 0x0001;
    return *((uint8_t*)&word) == 0x01;
}

static void logger_trimWhitespace(char* str)
{
    if (!str)
        return;

    size_t len = strlen(str);
    while (len > 0 && (str[len - 1] == ' ' || str[len - 1] == '\t' || str[len - 1] == '\n' || str[len - 1] == '\r'))
    {
        str[--len] = '\0';
    }

    size_t start = 0;
    while (str[start] == ' ' || str[start] == '\t')
    {
        start++;
    }

    if (start > 0)
    {
        memmove(str, str + start, len - start + 1);
    }
}

#if defined(__linux__)
static logger_u32 logger_linuxPhysicalCores(logger_u32 fallbackLogical)
{
    FILE* f = fopen("/proc/cpuinfo", "r");
    if (!f)
        return fallbackLogical;

    /* Track unique (physical_id, core_id) pairs up to 256 entries */
    int pkgIds[256];
    int coreIds[256];
    size_t pairCount = 0;

    int curPkg = 0;
    int curCore = -1;
    char line[256];

    while (fgets(line, sizeof(line), f))
    {
        if (strncmp(line, "physical id", 11) == 0)
        {
            char* colon = strchr(line, ':');
            if (colon) curPkg = atoi(colon + 1);
        }
        else if (strncmp(line, "core id", 7) == 0)
        {
            char* colon = strchr(line, ':');
            if (colon) curCore = atoi(colon + 1);
        }
        else if (line[0] == '\n' || line[0] == '\0')
        {
            if (curCore >= 0 && pairCount < 256)
            {
                bool seen = false;
                for (size_t i = 0; i < pairCount; ++i)
                {
                    if (pkgIds[i] == curPkg && coreIds[i] == curCore)
                    {
                        seen = true;
                        break;
                    }
                }
                if (!seen)
                {
                    pkgIds[pairCount] = curPkg;
                    coreIds[pairCount] = curCore;
                    pairCount++;
                }
            }
            curPkg = 0;
            curCore = -1;
        }
    }

    fclose(f);
    return (pairCount > 0) ? (logger_u32)pairCount : fallbackLogical;
}
#endif

static void logger_detectCompiler(logger_metadata_obj* meta, char* msvcVerBuf, size_t msvcVerCap)
{
#if defined(__clang__)
    (void)msvcVerBuf;
    (void)msvcVerCap;
    meta->toolChain.compiler.name = "Clang";
    meta->toolChain.compiler.version = __clang_version__;
#elif defined(_MSC_VER)
    snprintf(msvcVerBuf, msvcVerCap, "MSVC %d", _MSC_VER);
    meta->toolChain.compiler.name = "MSVC";
    meta->toolChain.compiler.version = msvcVerBuf;
#elif defined(__GNUC__)
    (void)msvcVerBuf;
    (void)msvcVerCap;
    meta->toolChain.compiler.name = "GCC";
    meta->toolChain.compiler.version = __VERSION__;
#else
    (void)msvcVerBuf;
    (void)msvcVerCap;
    meta->toolChain.compiler.name = "Unknown";
    meta->toolChain.compiler.version = "Unknown";
#endif

#if defined(__STDC_VERSION__)
    #if __STDC_VERSION__ >= 202311L
        meta->toolChain.compiler.std = "C23";
    #elif __STDC_VERSION__ >= 201710L
        meta->toolChain.compiler.std = "C17";
    #elif __STDC_VERSION__ >= 201112L
        meta->toolChain.compiler.std = "C11";
    #elif __STDC_VERSION__ >= 199901L
        meta->toolChain.compiler.std = "C99";
    #else
        meta->toolChain.compiler.std = "C90";
    #endif
#else
    meta->toolChain.compiler.std = "Pre-C99";
#endif

#if defined(LOGGER_BUILD_FLAGS)
    meta->toolChain.compiler.flags = LOGGER_BUILD_FLAGS;
#else
    meta->toolChain.compiler.flags = "Not specified";
#endif

#if defined(LOGGER_CRT_MODE)
    meta->toolChain.compiler.crtMode = LOGGER_CRT_MODE;
#elif defined(_WIN32)
    meta->toolChain.compiler.crtMode = "Win32 / MSVCRT";
#else
    meta->toolChain.compiler.crtMode = "POSIX / libc";
#endif

    meta->toolChain.ptrBits = (logger_u8)(sizeof(void*) * 8U);
    meta->toolChain.isLittleEndian = logger_detectLittleEndian();
}

static void logger_detectPlatformAndHardware(
    logger_metadata_obj* meta,
    char* cpuBuf, size_t cpuCap,
    char* isaBuf, size_t isaCap)
{
#if defined(__x86_64__) || defined(_M_X64)
    meta->hardware.arch = "x86_64";
#elif defined(__aarch64__) || defined(_M_ARM64)
    meta->hardware.arch = "aarch64";
#elif defined(__i386__) || defined(_M_IX86)
    meta->hardware.arch = "x86";
#else
    meta->hardware.arch = "Unknown";
#endif

    snprintf(cpuBuf, cpuCap, "%s", "Unknown CPU");
    isaBuf[0] = '\0';
    meta->hardware.cores.physical = 1;
    meta->hardware.cores.logical = 1;
    meta->hardware.ram = 0;
    meta->hardware.cacheLineBytes = 64;
    meta->hardware.pageSizeBytes = 4096;

#if defined(_WIN32)
    meta->platform.os = "Windows";
    meta->main.pid = (logger_u32)GetCurrentProcessId();

    SYSTEM_INFO sysInfo;
    GetSystemInfo(&sysInfo);
    meta->hardware.cores.logical = (logger_u32)sysInfo.dwNumberOfProcessors;
    meta->hardware.cores.physical = (logger_u32)sysInfo.dwNumberOfProcessors;
    meta->hardware.pageSizeBytes = (logger_u32)sysInfo.dwPageSize;

    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(memStatus);
    if (GlobalMemoryStatusEx(&memStatus))
    {
        meta->hardware.ram = (logger_u64)(memStatus.ullTotalPhys / (1024ULL * 1024ULL));
    }

    DWORD bufLen = 0;
    GetLogicalProcessorInformation(NULL, &bufLen);
    if (bufLen > 0)
    {
        PSYSTEM_LOGICAL_PROCESSOR_INFORMATION info =
            (PSYSTEM_LOGICAL_PROCESSOR_INFORMATION)malloc(bufLen);
        if (info && GetLogicalProcessorInformation(info, &bufLen))
        {
            logger_u32 physCount = 0;
            size_t count = bufLen / sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION);
            for (size_t i = 0; i < count; ++i)
            {
                if (info[i].Relationship == RelationProcessorCore)
                {
                    physCount++;
                }
                else if (info[i].Relationship == RelationCache &&
                         info[i].Cache.Level == 1 &&
                         info[i].Cache.LineSize > 0)
                {
                    meta->hardware.cacheLineBytes = (logger_u32)info[i].Cache.LineSize;
                }
            }
            if (physCount > 0)
                meta->hardware.cores.physical = physCount;
        }
        free(info);
    }

    #if defined(_M_X64) || defined(_M_IX86)
    int cpuInfo[4] = {0};
    char brand[49] = {0};
    __cpuid(cpuInfo, 0x80000000);
    unsigned int maxExtId = (unsigned int)cpuInfo[0];
    if (maxExtId >= 0x80000004)
    {
        __cpuid((int*)(brand + 0),  0x80000002);
        __cpuid((int*)(brand + 16), 0x80000003);
        __cpuid((int*)(brand + 32), 0x80000004);
        brand[48] = '\0';
        logger_trimWhitespace(brand);
        snprintf(cpuBuf, cpuCap, "%s", brand);
    }

    int info1[4] = {0}, info7[4] = {0};
    __cpuid(info1, 1);
    __cpuidex(info7, 7, 0);

    size_t pos = 0;
    if (info1[3] & (1 << 26)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "SSE2 ");
    if (info1[2] & (1 << 0))  pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "SSE3 ");
    if (info1[2] & (1 << 12)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "FMA ");
    if (info1[2] & (1 << 28)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX ");
    if (info7[1] & (1 << 5))  pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX2 ");
    if (info7[1] & (1 << 16)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX-512F ");
    logger_trimWhitespace(isaBuf);
    #endif

#elif defined(__linux__) || defined(__APPLE__)
    struct utsname uts;
    meta->platform.os = (uname(&uts) == 0) ? uts.sysname : "POSIX";
    meta->main.pid = (logger_u32)getpid();

    long pageSz = sysconf(_SC_PAGESIZE);
    if (pageSz > 0)
        meta->hardware.pageSizeBytes = (logger_u32)pageSz;

    long nprocs = sysconf(_SC_NPROCESSORS_ONLN);
    if (nprocs > 0)
    {
        meta->hardware.cores.logical = (logger_u32)nprocs;
        meta->hardware.cores.physical = (logger_u32)nprocs;
    }

    #if defined(__linux__)
    meta->hardware.cores.physical = logger_linuxPhysicalCores(meta->hardware.cores.logical);

    struct sysinfo si;
    if (sysinfo(&si) == 0)
    {
        meta->hardware.ram = (logger_u64)(((uint64_t)si.totalram * si.mem_unit) / (1024ULL * 1024ULL));
    }

    long l1Line = sysconf(_SC_LEVEL1_DCACHE_LINESIZE);
    if (l1Line > 0)
        meta->hardware.cacheLineBytes = (logger_u32)l1Line;
    #endif

    #if defined(__x86_64__) || defined(__i386__)
    unsigned int eax, ebx, ecx, edx;
    char brand[49] = {0};
    if (__get_cpuid(0x80000000, &eax, &ebx, &ecx, &edx) && eax >= 0x80000004)
    {
        __cpuid(0x80000002, *(unsigned int*)(brand + 0),  *(unsigned int*)(brand + 4),  *(unsigned int*)(brand + 8),  *(unsigned int*)(brand + 12));
        __cpuid(0x80000003, *(unsigned int*)(brand + 16), *(unsigned int*)(brand + 20), *(unsigned int*)(brand + 24), *(unsigned int*)(brand + 28));
        __cpuid(0x80000004, *(unsigned int*)(brand + 32), *(unsigned int*)(brand + 36), *(unsigned int*)(brand + 40), *(unsigned int*)(brand + 44));
        brand[48] = '\0';
        logger_trimWhitespace(brand);
        snprintf(cpuBuf, cpuCap, "%s", brand);
    }

    unsigned int a1, b1, c1, d1, a7, b7, c7, d7;
    if (__get_cpuid(1, &a1, &b1, &c1, &d1))
    {
        size_t pos = 0;
        if (d1 & (1U << 26)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "SSE2 ");
        if (c1 & (1U << 0))  pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "SSE3 ");
        if (c1 & (1U << 12)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "FMA ");
        if (c1 & (1U << 28)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX ");
        if (__get_cpuid_count(7, 0, &a7, &b7, &c7, &d7))
        {
            if (b7 & (1U << 5))  pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX2 ");
            if (b7 & (1U << 16)) pos += (size_t)snprintf(isaBuf + pos, isaCap - pos, "AVX-512F ");
        }
        logger_trimWhitespace(isaBuf);
    }
    #endif
#endif

    meta->hardware.cpu = cpuBuf;
    meta->hardware.isa = isaBuf[0] ? isaBuf : "Baseline / Scalar";
}

static void logger_makeSessionStamp(char* out, size_t cap)
{
    if (!out || cap == 0)
        return;

    out[0] = '\0';

    time_t now = time(NULL);
    if (now == (time_t)-1)
        return;

    struct tm localTm;

#if defined(_WIN32)
    if (localtime_s(&localTm, &now) != 0)
        return;
#else
    if (!localtime_r(&now, &localTm))
        return;
#endif

    strftime(out, cap, "%Y%m%d_%H%M%S", &localTm);
}

static void logger_fillMetadata(
    logger_metadata_obj* meta,
    const logger_metadata_obj* userMeta,
    const char* resolvedFileName,
    const char* sessionStamp,
    log_level minLevel)
{
    static char s_cpuBuf[64];
    static char s_isaBuf[128];
    static char s_msvcVerBuf[32];

    memset(meta, 0, sizeof(*meta));

    logger_detectCompiler(meta, s_msvcVerBuf, sizeof(s_msvcVerBuf));
    logger_detectPlatformAndHardware(meta, s_cpuBuf, sizeof(s_cpuBuf), s_isaBuf, sizeof(s_isaBuf));

    /* Safe defaults */
    meta->app.name          = "App-Unknown";
    meta->app.version       = "0.0.0";
    meta->app.buildProfile  = "Unknown";
    meta->app.buildId       = "Dev";
    meta->app.activeBackend = "None";
    meta->platform.backends = "None";

    if (userMeta)
    {
        if (userMeta->app.name)          meta->app.name          = userMeta->app.name;
        if (userMeta->app.version)       meta->app.version       = userMeta->app.version;
        if (userMeta->app.buildProfile)  meta->app.buildProfile  = userMeta->app.buildProfile;
        if (userMeta->app.buildId)       meta->app.buildId       = userMeta->app.buildId;
        if (userMeta->app.activeBackend) meta->app.activeBackend = userMeta->app.activeBackend;
        if (userMeta->platform.backends) meta->platform.backends = userMeta->platform.backends;

        if (userMeta->toolChain.compiler.flags)   meta->toolChain.compiler.flags   = userMeta->toolChain.compiler.flags;
        if (userMeta->toolChain.compiler.crtMode) meta->toolChain.compiler.crtMode = userMeta->toolChain.compiler.crtMode;
    }

    meta->main.fileName = resolvedFileName ? resolvedFileName : "";
    meta->main.session  = sessionStamp ? sessionStamp : "";
    meta->main.minLevel = (logger_u32)minLevel;
}

static const char* log_levelName(log_level level)
{
    switch (level)
    {
        case LOG_LEVEL_TRACE:   return "TRACE";
        case LOG_LEVEL_DEBUG:   return "DEBUG";
        case LOG_LEVEL_INFO:    return "INFO";
        case LOG_LEVEL_WARNING: return "WARNING";
        case LOG_LEVEL_ERROR:   return "ERROR";
        case LOG_LEVEL_FATAL:   return "FATAL";
        default:                return "UNKNOWN";
    }
}

static const char* log_levelColor(log_level level)
{
    switch (level)
    {
        case LOG_LEVEL_TRACE:   return "\x1b[90m";
        case LOG_LEVEL_DEBUG:   return "\x1b[38;2;50;230;180m";
        case LOG_LEVEL_INFO:    return "\x1b[38;2;39;138;163m";
        case LOG_LEVEL_WARNING: return "\x1b[33m";
        case LOG_LEVEL_ERROR:   return "\x1b[31m";
        case LOG_LEVEL_FATAL:   return "\x1b[1;37;41m";
        default:                return "\x1b[0m";
    }
}

#define ANSI_RESET "\x1b[0m"

static bool g_colorEnabled = true;

static void logger_enableColors(void)
{
#ifdef _WIN32
    HANDLE handle = GetStdHandle(STD_OUTPUT_HANDLE);

    DWORD mode;

    if (handle == INVALID_HANDLE_VALUE ||
        handle == NULL ||
        !GetConsoleMode(handle, &mode))
    {
        g_colorEnabled = false;
        return;
    }

    if (!SetConsoleMode(
            handle,
            mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    {
        g_colorEnabled = false;
    }
#endif
}

static void logger_makeTimestamp(char* output, size_t capacity)
{
    time_t now = time(NULL);

    struct tm local;

#ifdef _WIN32
    localtime_s(&local, &now);
#else
    localtime_r(&now, &local);
#endif

    strftime(
        output,
        capacity,
        "%Y-%m-%d %H:%M:%S",
        &local
    );
}

static void logger_output(const log_record* record)
{
    const char* name = log_levelName(record->level);
    const char* color = log_levelColor(record->level);

    /* Terminal output */
    if (g_colorEnabled)
    {
        fprintf(
            stdout,
            "%s[%s] [%-7s] > %s%s\n",
            color,
            record->timestamp,
            name,
            record->message,
            ANSI_RESET
        );
    }
    else
    {
        fprintf(
            stdout,
            "[%s] [%-7s] > %s\n",
            record->timestamp,
            name,
            record->message
        );
    }

    fflush(stdout);

    /* File output: deliberately no ANSI colors */
    if (g_logger.file)
    {
        fprintf(
            g_logger.file,
            "[%s] [%-7s] > %s\n",
            record->timestamp,
            name,
            record->message
        );

        if (record->level >= LOG_LEVEL_ERROR)
            fflush(g_logger.file);
    }
}

static bool logger_createSingleDir(const char* dirPath)
{
    if (!dirPath || dirPath[0] == '\0')
        return true;

    /* Skip drive-only like "C:" or "." */
    if (strcmp(dirPath, ".") == 0)
        return true;

    size_t len = strlen(dirPath);
    if (len == 2 && dirPath[1] == ':')
        return true;

#if defined(_WIN32)
    if (CreateDirectoryA(dirPath, NULL))
        return true;

    DWORD err = GetLastError();
    return (err == ERROR_ALREADY_EXISTS);
#else
    if (mkdir(dirPath, 0755) == 0)
        return true;

    return (errno == EEXIST);
#endif
}

static bool logger_ensureParentDirs(const char* filePath)
{
    if (!filePath || filePath[0] == '\0')
        return false;

    char temp[LOGGER_PATH_SIZE];
    int written = snprintf(temp, sizeof(temp), "%s", filePath);
    if (written < 0 || (size_t)written >= sizeof(temp))
        return false;

    for (size_t i = 0; temp[i] != '\0'; ++i)
    {
        if (temp[i] == '/' || temp[i] == '\\')
        {
            /* Skip leading slash ("/var/...") or drive root ("C:/...") */
            if (i == 0 || (i == 2 && temp[1] == ':'))
                continue;

            char saved = temp[i];
            temp[i] = '\0';

            bool ok = logger_createSingleDir(temp);
            temp[i] = saved;

            if (!ok)
                return false;
        }
    }

    return true;
}

static FILE* logger_openUniqueFile(
    const char* filePath,
    const char* sessionStamp,
    char* outPath,
    size_t outCapacity)
{
    if (!filePath || !sessionStamp || sessionStamp[0] == '\0' || !outPath || outCapacity == 0)
        return NULL;

    char base[LOGGER_PATH_SIZE];
    snprintf(base, sizeof(base), "%s", filePath);

    /* Strip trailing ".log" if present so we get "app_20261124_001900.log" */
    size_t len = strlen(base);
    if (len > 4 && strcmp(base + len - 4, ".log") == 0)
    {
        base[len - 4] = '\0';
    }

    /* Try <base>_<YYYYMMDD_HHMMSS>.log first */
    int written = snprintf(outPath, outCapacity, "%s_%s.log", base, sessionStamp);
    if (written < 0 || (size_t)written >= outCapacity)
        return NULL;

    FILE* existing = fopen(outPath, "rb");
    if (!existing)
    {
        return fopen(outPath, "wb");
    }
    fclose(existing);

    /* Fallback if another run starts inside the exact same second */
    for (int suffix = 1; suffix < 1000; ++suffix)
    {
        written = snprintf(
            outPath,
            outCapacity,
            "%s_%s_%d.log",
            base,
            sessionStamp,
            suffix
        );
        if (written < 0 || (size_t)written >= outCapacity)
            return NULL;

        existing = fopen(outPath, "rb");
        if (!existing)
        {
            return fopen(outPath, "wb");
        }
        fclose(existing);
    }

    return NULL;
}

static void logger_writeHeader(FILE* file, const logger_metadata_obj* meta)
{
    if (!file || !meta)
        return;

    const char* levelName = log_levelName((log_level)meta->main.minLevel);
    const char* endianStr = meta->toolChain.isLittleEndian ? "Little-Endian" : "Big-Endian";

    fprintf(
        file,
        "================================================================================\n"
        "[App]\n"
        "  Name           : %s\n"
        "  Version        : %s\n"
        "  Build Profile  : %s\n"
        "  Build ID       : %s\n"
        "  Active Backend : %s\n"
        "\n"
        "[ToolChain]\n"
        "  Compiler       : %s (%s)\n"
        "  C Standard     : %s\n"
        "  Flags          : %s\n"
        "  CRT Mode       : %s\n"
        "  Pointer Width  : %u-bit\n"
        "  Endianness     : %s\n"
        "\n"
        "[Platform]\n"
        "  OS             : %s\n"
        "  Backends       : %s\n"
        "\n"
        "[Hardware]\n"
        "  Architecture   : %s\n"
        "  CPU            : %s\n"
        "  ISA / SIMD     : %s\n"
        "  Cores          : %u Physical / %u Logical\n"
        "  RAM            : %llu MB\n"
        "  Cache Line     : %u bytes\n"
        "  Page Size      : %u bytes\n"
        "\n"
        "[Main / Session]\n"
        "  File Name      : %s\n"
        "  Session        : %s\n"
        "  PID            : %u\n"
        "  Min Level      : %s\n"
        "================================================================================\n\n",
        meta->app.name ? meta->app.name : "N/A",
        meta->app.version ? meta->app.version : "N/A",
        meta->app.buildProfile ? meta->app.buildProfile : "N/A",
        meta->app.buildId ? meta->app.buildId : "N/A",
        meta->app.activeBackend ? meta->app.activeBackend : "N/A",

        meta->toolChain.compiler.name ? meta->toolChain.compiler.name : "Unknown",
        meta->toolChain.compiler.version ? meta->toolChain.compiler.version : "Unknown",
        meta->toolChain.compiler.std ? meta->toolChain.compiler.std : "Unknown",
        meta->toolChain.compiler.flags ? meta->toolChain.compiler.flags : "N/A",
        meta->toolChain.compiler.crtMode ? meta->toolChain.compiler.crtMode : "N/A",
        (unsigned int)meta->toolChain.ptrBits,
        endianStr,

        meta->platform.os ? meta->platform.os : "Unknown",
        meta->platform.backends ? meta->platform.backends : "None",

        meta->hardware.arch ? meta->hardware.arch : "Unknown",
        meta->hardware.cpu ? meta->hardware.cpu : "Unknown",
        meta->hardware.isa ? meta->hardware.isa : "None",
        (unsigned int)meta->hardware.cores.physical,
        (unsigned int)meta->hardware.cores.logical,
        (unsigned long long)meta->hardware.ram,
        (unsigned int)meta->hardware.cacheLineBytes,
        (unsigned int)meta->hardware.pageSizeBytes,

        meta->main.fileName ? meta->main.fileName : "N/A",
        meta->main.session ? meta->main.session : "N/A",
        (unsigned int)meta->main.pid,
        levelName
    );

    fflush(file);
}

static void logger_worker(void* argument)
{
    (void)argument;

    for (;;)
    {
        log_record record;

        uv_mutex_lock(&g_logger.mutex);

        /* Sleep until a message arrives or shutdown begins. */
        while (g_logger.count == 0 && !g_logger.stopping)
        {
            uv_cond_wait(
                &g_logger.hasMessages,
                &g_logger.mutex
            );
        }

        /* Stop only after the queue has been drained. */
        if (g_logger.count == 0 && g_logger.stopping)
        {
            uv_mutex_unlock(&g_logger.mutex);
            break;
        }

        /* Read from the ring buffer. */
        record = g_logger.queue[g_logger.head];

        g_logger.head =
            (g_logger.head + 1) % LOGGER_QUEUE_CAPACITY;

        g_logger.count--;

        uv_cond_signal(&g_logger.hasSpace);

        uv_mutex_unlock(&g_logger.mutex);

        /* Perform actual I/O outside the queue lock. */
        uv_mutex_lock(&g_logger.outputMutex);

        logger_output(&record);

        uv_mutex_unlock(&g_logger.outputMutex);

        uv_mutex_lock(&g_logger.mutex);

        g_logger.completed++;

        if (g_logger.completed == g_logger.submitted)
        {
            uv_cond_broadcast(&g_logger.flushed);
        }

        uv_mutex_unlock(&g_logger.mutex);
    }

    /* Final file flush. */
    uv_mutex_lock(&g_logger.outputMutex);

    if (g_logger.file)
    {
        fflush(g_logger.file);
        fclose(g_logger.file);
        g_logger.file = NULL;
    }

    uv_mutex_unlock(&g_logger.outputMutex);
}

bool logger_init(const char* filePath, log_level minimumLevel, logger_metadata_obj *userMeta)
{
    if (g_logger.initialized || !filePath)
        return false;

    memset(&g_logger, 0, sizeof(g_logger));

    if (!logger_ensureParentDirs(filePath))
        return false;

    logger_makeSessionStamp(g_logger.sessionBuf, sizeof(g_logger.sessionBuf));

    g_logger.file = logger_openUniqueFile(
        filePath,
        g_logger.sessionBuf,
        g_logger.resolvedPath,
        sizeof(g_logger.resolvedPath)
    );

    if (!g_logger.file)
        return false;

    logger_fillMetadata(
        &g_logger.meta,
        userMeta,
        g_logger.resolvedPath,
        g_logger.sessionBuf,
        minimumLevel
    );

    g_logger.meta.main.session  = g_logger.sessionBuf;
    g_logger.meta.main.fileName = g_logger.resolvedPath;

    logger_writeHeader(g_logger.file, &g_logger.meta);

    if (!g_logger.file)
        return false;

    if (uv_mutex_init(&g_logger.mutex) != 0)
        goto fail_file;

    if (uv_mutex_init(&g_logger.outputMutex) != 0)
        goto fail_mutex;

    if (uv_cond_init(&g_logger.hasMessages) != 0)
        goto fail_output_mutex;

    if (uv_cond_init(&g_logger.hasSpace) != 0)
        goto fail_messages;

    if (uv_cond_init(&g_logger.flushed) != 0)
        goto fail_space;

    g_logger.minimumLevel = minimumLevel;

    logger_enableColors();

    g_logger.initialized = true;
    g_logger.workerRunning = true;

    if (uv_thread_create(
            &g_logger.worker,
            logger_worker,
            NULL) != 0)
    {
        g_logger.workerRunning = false;
        g_logger.initialized = false;
        goto fail_flushed;
    }

    return true;

fail_flushed:
    uv_cond_destroy(&g_logger.flushed);

fail_space:
    uv_cond_destroy(&g_logger.hasSpace);

fail_messages:
    uv_cond_destroy(&g_logger.hasMessages);

fail_output_mutex:
    uv_mutex_destroy(&g_logger.outputMutex);

fail_mutex:
    uv_mutex_destroy(&g_logger.mutex);

fail_file:
    fclose(g_logger.file);
    g_logger.file = NULL;

    return false;
}

void logger_write(
    log_level level,
    const char* format,
    ...)
{
    if (!g_logger.initialized || !format)
        return;

    uv_mutex_lock(&g_logger.mutex);

    /* 1. Bail out immediately before formatting or copying anything */
    if (level < g_logger.minimumLevel || g_logger.stopping)
    {
        uv_mutex_unlock(&g_logger.mutex);
        return;
    }

    /* 2. Wait for an open ring buffer slot */
    while (g_logger.count == LOGGER_QUEUE_CAPACITY && !g_logger.stopping)
    {
        uv_cond_wait(&g_logger.hasSpace, &g_logger.mutex);
    }

    if (g_logger.stopping)
    {
        uv_mutex_unlock(&g_logger.mutex);
        return;
    }

    /* 3. Point directly to the destination slot (zero stack buffer, zero struct copy) */
    log_record* slot = &g_logger.queue[g_logger.tail];

    slot->level = level;
    logger_makeTimestamp(slot->timestamp, sizeof(slot->timestamp));

    va_list args;
    va_start(args, format);
    vsnprintf(slot->message, sizeof(slot->message), format, args);
    va_end(args);

    /* 4. Commit the slot */
    g_logger.tail = (g_logger.tail + 1) % LOGGER_QUEUE_CAPACITY;
    g_logger.count++;
    g_logger.submitted++;

    uv_cond_signal(&g_logger.hasMessages);
    uv_mutex_unlock(&g_logger.mutex);
}

void logger_setLevel(log_level level)
{
    if (!g_logger.initialized)
        return;

    uv_mutex_lock(&g_logger.mutex);

    g_logger.minimumLevel = level;

    uv_mutex_unlock(&g_logger.mutex);
}

void logger_flush(void)
{
    if (!g_logger.initialized)
        return;

    uv_mutex_lock(&g_logger.mutex);

    uint64_t target = g_logger.submitted;

    while (g_logger.completed < target)
    {
        uv_cond_wait(
            &g_logger.flushed,
            &g_logger.mutex
        );
    }

    uv_mutex_unlock(&g_logger.mutex);

    uv_mutex_lock(&g_logger.outputMutex);

    if (g_logger.file)
        fflush(g_logger.file);

    uv_mutex_unlock(&g_logger.outputMutex);
}

void logger_shutdown(void)
{
    if (!g_logger.initialized)
        return;

    uv_mutex_lock(&g_logger.mutex);

    g_logger.stopping = true;

    /* Wake worker and any producers waiting for space. */
    uv_cond_broadcast(&g_logger.hasMessages);
    uv_cond_broadcast(&g_logger.hasSpace);

    uv_mutex_unlock(&g_logger.mutex);

    /* Wait until the worker exits. */
    uv_thread_join(&g_logger.worker);

    g_logger.workerRunning = false;
    g_logger.initialized = false;

    uv_cond_destroy(&g_logger.flushed);
    uv_cond_destroy(&g_logger.hasSpace);
    uv_cond_destroy(&g_logger.hasMessages);

    uv_mutex_destroy(&g_logger.outputMutex);
    uv_mutex_destroy(&g_logger.mutex);
}

logger_metadata_obj logger_getMetaData(void)
{
    return g_logger.meta;
}
