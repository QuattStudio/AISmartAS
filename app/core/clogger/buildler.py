




# import os
# import sys
# from cffi import FFI

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CLOGGER_DIR = os.path.join(BASE_DIR, "app", "core", "clogger")

# ffibuilder = FFI()

# ffibuilder.cdef("""
#     typedef const char* logger_cstr;
#     typedef uint8_t     logger_u8;
#     typedef uint32_t    logger_u32;
#     typedef uint64_t    logger_u64;

#     typedef struct logger_metadata_obj
#     {
#         struct
#         {
#             logger_cstr name;
#             logger_cstr version;
#             logger_cstr buildProfile;
#             logger_cstr buildId;
#             logger_cstr activeBackend;
#         } app;

#         struct
#         {
#             struct
#             {
#                 logger_cstr name;
#                 logger_cstr version;
#                 logger_cstr flags;
#                 logger_cstr std;
#                 logger_cstr crtMode;
#             } compiler;

#             logger_u8   ptrBits;
#             bool        isLittleEndian;
#         } toolChain;

#         struct
#         {
#             logger_cstr os;
#             logger_cstr backends;
#         } platform;

#         struct
#         {
#             logger_cstr arch;
#             logger_cstr cpu;
#             logger_cstr isa;

#             struct
#             {
#                 logger_u32 physical;
#                 logger_u32 logical;
#             } cores;

#             logger_u64    ram;
#             logger_u32    cacheLineBytes;
#             logger_u32    pageSizeBytes;
#         } hardware;

#         struct
#         {
#             logger_cstr fileName;
#             logger_cstr session;
#             logger_u32  pid;
#             logger_u32  minLevel;
#         } main;

#     } logger_metadata_obj;

#     typedef enum log_level
#     {
#         LOG_LEVEL_TRACE = 0,
#         LOG_LEVEL_DEBUG,
#         LOG_LEVEL_INFO,
#         LOG_LEVEL_WARNING,
#         LOG_LEVEL_ERROR,
#         LOG_LEVEL_FATAL,
#         LOG_LEVEL_NONE
#     } log_level;

#     bool logger_init(const char* filePath, log_level minimumLevel, logger_metadata_obj *userMeta);
#     void logger_setLevel(log_level level);
#     void logger_flush(void);
#     void logger_shutdown(void);
#     logger_metadata_obj logger_getMetaData(void);

#     /* Non-variadic helper for CFFI since cdef does not support '...' */
#     void logger_write_msg(log_level level, const char* msg);
# """)

# extra_compile_args = [
#     "-O2",
#     "-flto",
#     "-ffunction-sections",
#     "-fdata-sections",
# ]

# extra_link_args = [
#     "-O2",
#     "-flto",
#     "-Wl,--gc-sections",
#     os.path.join(CLOGGER_DIR, "libuv.a"),
# ]

# libraries = []

# if sys.platform.startswith("win"):
#     libraries.extend([
#         "synchronization",
#         "ws2_32",
#         "iphlpapi",
#         "userenv",
#         "psapi",
#         "shell32",
#         "advapi32",
#         "dbghelp",
#         "ole32",
#     ])
# else:
#     libraries.extend(["pthread", "dl", "m"])

# ffibuilder.set_source(
#     "_clogger",
#     """
#     #define LOGGER_BUILD_SHARED
#     #include "logger.h"

#     void logger_write(log_level level, const char* format, ...);

#     static void logger_write_msg(log_level level, const char* msg)
#     {
#         if (msg)
#         {
#             logger_write(level, "%s", msg);
#         }
#     }
#     """,
#     sources=[os.path.join(CLOGGER_DIR, "src", "logger.c")],
#     include_dirs=[
#         os.path.join(CLOGGER_DIR, "include"),
#         os.path.join(CLOGGER_DIR, "external"),
#     ],
#     library_dirs=[CLOGGER_DIR],
#     libraries=libraries,
#     extra_compile_args=extra_compile_args,
#     extra_link_args=extra_link_args,
# )

# if __name__ == "__main__":
#     ffibuilder.compile(verbose=True)




    



import os
import sys
import setuptools.dist
from cffi import FFI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

# Make sure gcc (MinGW-w64) is found if it is not already in PATH
mingw_bin = r"C:\mingw64\bin"
if os.path.isdir(mingw_bin) and mingw_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = mingw_bin + os.pathsep + os.environ.get("PATH", "")

ffibuilder = FFI()

ffibuilder.cdef("""
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
            logger_cstr buildProfile;
            logger_cstr buildId;
            logger_cstr activeBackend;
        } app;

        struct
        {
            struct
            {
                logger_cstr name;
                logger_cstr version;
                logger_cstr flags;
                logger_cstr std;
                logger_cstr crtMode;
            } compiler;

            logger_u8   ptrBits;
            bool        isLittleEndian;
        } toolChain;

        struct
        {
            logger_cstr os;
            logger_cstr backends;
        } platform;

        struct
        {
            logger_cstr arch;
            logger_cstr cpu;
            logger_cstr isa;

            struct
            {
                logger_u32 physical;
                logger_u32 logical;
            } cores;

            logger_u64    ram;
            logger_u32    cacheLineBytes;
            logger_u32    pageSizeBytes;
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

    bool logger_init(const char* filePath, log_level minimumLevel, logger_metadata_obj *userMeta);
    void logger_setLevel(log_level level);
    void logger_flush(void);
    void logger_shutdown(void);
    logger_metadata_obj logger_getMetaData(void);

    /* Non-variadic helper for CFFI since cdef does not support '...' */
    void logger_write_msg(log_level level, const char* msg);
""")

extra_compile_args = [
    "-O2",
    "-flto",
    "-ffunction-sections",
    "-fdata-sections",
]

extra_link_args = [
    "-O2",
    "-flto",
    "-Wl,--gc-sections",
    os.path.join(BASE_DIR, "libuv.a"),
]

libraries = []

if sys.platform.startswith("win"):
    libraries.extend([
        "synchronization",
        "ws2_32",
        "iphlpapi",
        "userenv",
        "psapi",
        "shell32",
        "advapi32",
        "dbghelp",
        "ole32",
    ])
else:
    libraries.extend(["pthread", "dl", "m"])

ffibuilder.set_source(
    "_clogger",
    """
    // #define LOGGER_BUILD_SHARED
    #include "logger.h"

    void logger_write(log_level level, const char* format, ...);

    static void logger_write_msg(log_level level, const char* msg)
    {
        if (msg)
        {
            logger_write(level, "%s", msg);
        }
    }
    """,
    sources=[os.path.join(BASE_DIR, "src", "logger.c")],
    include_dirs=[
        os.path.join(BASE_DIR, "include"),
        os.path.join(BASE_DIR, "external"),
    ],
    define_macros=[("LOGGER_BUILD_SHARED", "1")],
    library_dirs=[BASE_DIR],
    libraries=libraries,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

if sys.platform.startswith("win"):
    _orig_dist_init = setuptools.dist.Distribution.__init__

    def _mingw_dist_init(self, attrs=None):
        attrs = dict(attrs or {})
        args = list(attrs.get("script_args") or [])
        if "build_ext" not in args:
            args.append("build_ext")
        if not any(a.startswith("--compiler") for a in args):
            args.append("--compiler=mingw32")
        attrs["script_args"] = args
        _orig_dist_init(self, attrs)

    setuptools.dist.Distribution.__init__ = _mingw_dist_init

if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    import sys
    import setuptools._distutils.ccompiler as _dc
    from setuptools.command.build_ext import build_ext as _build_ext

    if sys.platform.startswith("win"):
        _orig_new_compiler = _dc.new_compiler

        def _force_mingw(plat=None, compiler=None, verbose=0, dry_run=0, force=0):
            return _orig_new_compiler(
                plat=plat,
                compiler="mingw32",
                verbose=verbose,
                dry_run=dry_run,
                force=force,
            )

        _dc.new_compiler = _force_mingw

        _orig_init_opts = _build_ext.initialize_options

        def _force_build_ext_mingw(self):
            _orig_init_opts(self)
            self.compiler = "mingw32"

    _build_ext.initialize_options = _force_build_ext_mingw
    ffibuilder.compile(verbose=True)


