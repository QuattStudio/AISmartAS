
// #ifndef LOGGER_HEADER
// #define LOGGER_HEADER

// #if defined(_WIN32) || defined(__CYGWIN__)
//     #if defined(LOGGER_BUILD_SHARED)
//         #define LOGGER_API __declspec(dllexport)
//     #else
//         #define LOGGER_API __declspec(dllimport)
//     #endif
// #elif defined(__GNUC__) || defined(__clang__)
//     #if defined(LOGGER_BUILD_SHARED)
//         #define LOGGER_API __attribute__((visibility("default")))
//     #else
//         #define LOGGER_API
//     #endif
// #else
//     #define LOGGER_API
// #endif

// #include <stdbool.h>
// #include <stdint.h>

// typedef const char* logger_cstr;

// typedef uint8_t     logger_u8;
// typedef uint32_t    logger_u32;
// typedef uint64_t    logger_u64;

// typedef struct logger_metadata_obj
// {
//     struct
//     {
//         logger_cstr name;
//         logger_cstr version;
//         logger_cstr buildProfile;   /* e.g. "Debug", "Release", "RelWithDebInfo" */
//         logger_cstr buildId;        /* e.g. git commit hash / build stamp */
//         logger_cstr activeBackend;  /* e.g. "D3D12" (what actually ran vs. supported) */
//     } app;

//     struct
//     {
//         struct
//         {
//             logger_cstr name;
//             logger_cstr version;
//             logger_cstr flags;       /* e.g. "-O2 -mavx2 -ffreestanding -nostdlib" */
//             logger_cstr std;         /* e.g. "C11", "C17" */
//             logger_cstr crtMode;     /* e.g. "Zero-CRT / Custom", "MSVCRT", "glibc" */
//         } compiler;

//         logger_u8   ptrBits;            /* e.g. 64 or 32 */
//         bool        isLittleEndian;     /* true for little-endian */
//     } toolChain;

//     struct
//     {
//         logger_cstr os;
//         logger_cstr backends;   /* e.g. "D3D11, D3D12, Vulkan, Software" */
//     } platform;

//     struct
//     {
//         logger_cstr arch;
//         logger_cstr cpu;
//         logger_cstr isa;        /* e.g. "SSE2 AVX AVX2 FMA" */

//         struct
//         {
//             logger_u32 physical; /* physical core count */
//             logger_u32 logical;  /* hardware thread count */
//         } cores;

//         logger_u64    ram;
//         logger_u32    cacheLineBytes;    /* e.g. 64 */
//         logger_u32    pageSizeBytes;     /* e.g. 4096 */
//     } hardware;

//     struct
//     {
//         logger_cstr fileName;
//         logger_cstr session;
//         logger_u32  pid;
//         logger_u32  minLevel;
//     } main;

// } logger_metadata_obj;

// typedef enum log_level
// {
//     LOG_LEVEL_TRACE = 0,
//     LOG_LEVEL_DEBUG,
//     LOG_LEVEL_INFO,
//     LOG_LEVEL_WARNING,
//     LOG_LEVEL_ERROR,
//     LOG_LEVEL_FATAL,
//     LOG_LEVEL_NONE
// } log_level;

// /* Initialize the asynchronous logger. */
// LOGGER_API bool logger_init(const char* filePath, log_level minimumLevel, logger_metadata_obj *userMeta);

// /* Change minimum logging level. */
// LOGGER_API void logger_setLevel(log_level level);

// /* Flush pending logs to disk. */
// LOGGER_API void logger_flush(void);

// /* Stop worker and release resources. */
// LOGGER_API void logger_shutdown(void);

// /* Internal logging implementation. */
// LOGGER_API void logger_write(
//     log_level level,
//     const char* format,
//     ...
// );

// LOGGER_API logger_metadata_obj logger_getMetaData(void);

// /* Convenient logging macros. */
// #define LOG_TRACE(...)     logger_write(LOG_LEVEL_TRACE, __VA_ARGS__)

// #define LOG_DEBUG(...)     logger_write(LOG_LEVEL_DEBUG, __VA_ARGS__)

// #define LOG_INFO(...)     logger_write(LOG_LEVEL_INFO, __VA_ARGS__)

// #define LOG_WARNING(...)     logger_write(LOG_LEVEL_WARNING, __VA_ARGS__)

// #define LOG_ERROR(...)     logger_write(LOG_LEVEL_ERROR, __VA_ARGS__)

// #define LOG_FATAL(...)     logger_write(LOG_LEVEL_FATAL, __VA_ARGS__)

// #endif





















#ifndef LOGGER_HEADER
#define LOGGER_HEADER

#if defined(_WIN32) || defined(__CYGWIN__)
    #if defined(LOGGER_BUILD_SHARED)
        #define LOGGER_API __declspec(dllexport)
    #else
        #define LOGGER_API __declspec(dllimport)
    #endif
#elif defined(__GNUC__) || defined(__clang__)
    #if defined(LOGGER_BUILD_SHARED)
        #define LOGGER_API __attribute__((visibility("default")))
    #else
        #define LOGGER_API
    #endif
#else
    #define LOGGER_API
#endif

#include <stdbool.h>
#include <stdint.h>

typedef const char* logger_cstr;

typedef uint8_t     logger_u8;
typedef uint32_t    logger_u32;
typedef uint64_t    logger_u64;

typedef struct logger_metadata_obj
{
    struct
    {
        logger_cstr name;
        logger_cstr version;
        logger_cstr buildProfile;   /* e.g. "Debug", "Release", "RelWithDebInfo" */
        logger_cstr buildId;        /* e.g. git commit hash / build stamp */
        logger_cstr activeBackend;  /* e.g. "D3D12" (what actually ran vs. supported) */
    } app;

    struct
    {
        struct
        {
            logger_cstr name;
            logger_cstr version;
            logger_cstr flags;       /* e.g. "-O2 -mavx2 -ffreestanding -nostdlib" */
            logger_cstr std;         /* e.g. "C11", "C17" */
            logger_cstr crtMode;     /* e.g. "Zero-CRT / Custom", "MSVCRT", "glibc" */
        } compiler;

        logger_u8   ptrBits;            /* e.g. 64 or 32 */
        bool        isLittleEndian;     /* true for little-endian */
    } toolChain;

    struct
    {
        logger_cstr os;
        logger_cstr backends;   /* e.g. "D3D11, D3D12, Vulkan, Software" */
    } platform;

    struct
    {
        logger_cstr arch;
        logger_cstr cpu;
        logger_cstr isa;        /* e.g. "SSE2 AVX AVX2 FMA" */

        struct
        {
            logger_u32 physical; /* physical core count */
            logger_u32 logical;  /* hardware thread count */
        } cores;

        logger_u64    ram;
        logger_u32    cacheLineBytes;    /* e.g. 64 */
        logger_u32    pageSizeBytes;     /* e.g. 4096 */
    } hardware;

    struct
    {
        logger_cstr fileName;
        logger_cstr session;
        logger_u32  pid;
        logger_u32  minLevel;
    } main;

} logger_metadata_obj;

typedef enum log_level
{
    LOG_LEVEL_TRACE = 0,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_FATAL,
    LOG_LEVEL_NONE
} log_level;

/* Initialize the asynchronous logger. */
LOGGER_API bool logger_init(const char* filePath, log_level minimumLevel, logger_metadata_obj *userMeta);

/* Change minimum logging level. */
LOGGER_API void logger_setLevel(log_level level);

/* Flush pending logs to disk. */
LOGGER_API void logger_flush(void);

/* Stop worker and release resources. */
LOGGER_API void logger_shutdown(void);

/* Internal logging implementation. */
LOGGER_API void logger_write(
    log_level level,
    const char* format,
    ...
);

LOGGER_API logger_metadata_obj logger_getMetaData(void);

/* Convenient logging macros. */
#define LOG_TRACE(...)     logger_write(LOG_LEVEL_TRACE, __VA_ARGS__)

#define LOG_DEBUG(...)     logger_write(LOG_LEVEL_DEBUG, __VA_ARGS__)

#define LOG_INFO(...)      logger_write(LOG_LEVEL_INFO, __VA_ARGS__)

#define LOG_WARNING(...)   logger_write(LOG_LEVEL_WARNING, __VA_ARGS__)

#define LOG_ERROR(...)     logger_write(LOG_LEVEL_ERROR, __VA_ARGS__)

#define LOG_FATAL(...)     logger_write(LOG_LEVEL_FATAL, __VA_ARGS__)

#endif