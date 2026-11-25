# import ctypes
# from enum import IntEnum
# import os
# from typing import Optional


# DLL_PATH = "./clogger.dll"
# DEFAULT_LOG_FILE_PATH = "logs/app.log"


# l_struct    = ctypes.Structure
# l_enum      = IntEnum

# l_int       = ctypes.c_int
# l_char      = ctypes.c_char
# l_charp     = ctypes.c_char_p
# l_boolean   = ctypes.c_bool
# l_u8        = ctypes.c_uint8
# l_u32       = ctypes.c_uint32
# l_u64       = ctypes.c_uint64

# _isLoggerInitialized = False


# class log_level(l_enum):
#     TRACE   = 0
#     DEBUG   = 1
#     INFO    = 2
#     WARNING = 3
#     ERROR   = 4
#     FATAL   = 5
#     NONE    = 255


# class _AppMeta(l_struct):
#     name:                   Optional[bytes]
#     version:                Optional[bytes]
#     buildProfile:           Optional[bytes]
#     buildId:                Optional[bytes]
#     activeBackend:          Optional[bytes]

#     _fields_ = [
#         ("name",            l_charp),
#         ("version",         l_charp),
#         ("buildProfile",    l_charp),
#         ("buildId",         l_charp),
#         ("activeBackend",   l_charp),
#     ]


# class _CompilerMeta(l_struct):
#     name:                   Optional[bytes]
#     version:                Optional[bytes]
#     flags:                  Optional[bytes]
#     std:                    Optional[bytes]
#     crtMode:                Optional[bytes]

#     _fields_ = [
#         ("name",            l_charp),
#         ("version",         l_charp),
#         ("flags",           l_charp),
#         ("std",             l_charp),
#         ("crtMode",         l_charp),
#     ]


# class _ToolChainMeta(l_struct):
#     compiler:               _CompilerMeta
#     ptrBits:                int
#     isLittleEndian:         bool

#     _fields_ = [
#         ("compiler",        _CompilerMeta),
#         ("ptrBits",         l_u8),
#         ("isLittleEndian",  l_boolean),
#     ]


# class _PlatformMeta(l_struct):
#     os:                     Optional[bytes]
#     backends:               Optional[bytes]

#     _fields_ = [
#         ("os",              l_charp),
#         ("backends",        l_charp),
#     ]


# class _CoresMeta(l_struct):
#     physical:               int
#     logical:                int

#     _fields_ = [
#         ("physical",        l_u32),
#         ("logical",         l_u32),
#     ]


# class _HardwareMeta(l_struct):
#     arch:                   Optional[bytes]
#     cpu:                    Optional[bytes]
#     isa:                    Optional[bytes]
#     cores:                  _CoresMeta
#     ram:                    int
#     cacheLineBytes:         int
#     pageSizeBytes:          int

#     _fields_ = [
#         ("arch",            l_charp),
#         ("cpu",             l_charp),
#         ("isa",             l_charp),
#         ("cores",           _CoresMeta),
#         ("ram",             l_u64),
#         ("cacheLineBytes",  l_u32),
#         ("pageSizeBytes",   l_u32),
#     ]


# class _MainMeta(l_struct):
#     fileName:               Optional[bytes]
#     session:                Optional[bytes]
#     pid:                    int
#     minLevel:               int

#     _fields_ = [
#         ("fileName",        l_charp),
#         ("session",         l_charp),
#         ("pid",             l_u32),
#         ("minLevel",        l_u32),
#     ]


# class logger_metadata_obj(l_struct):
#     app:                    _AppMeta
#     toolChain:              _ToolChainMeta
#     platform:               _PlatformMeta
#     hardware:               _HardwareMeta
#     main:                   _MainMeta

#     _fields_ = [
#         ("app",             _AppMeta),
#         ("toolChain",       _ToolChainMeta),
#         ("platform",        _PlatformMeta),
#         ("hardware",        _HardwareMeta),
#         ("main",            _MainMeta),
#     ]


# def _bind_function(dll: ctypes.CDLL, func_name: str, argtypes: list, restype):
#     fn = getattr(dll, func_name)
#     fn.argtypes = argtypes
#     fn.restype = restype
#     return fn


# def _to_bytes(val: Optional[str]) -> Optional[bytes]:
#     if val is None:
#         return None
#     return val.encode("utf-8")


# def _format_pythonStyle(message: object, *args, **kwargs) -> str:
#     text = str(message)
#     if args or kwargs:
#         return text.format(*args, **kwargs)
#     return text


# class Logger:
#     def __init__(self, dllPath: str = DLL_PATH):
#         if not os.path.exists(dllPath):
#             raise FileNotFoundError(f"Logger library not found: {dllPath}")

#         self._dll = ctypes.CDLL(dllPath)

#         self._init = _bind_function(
#             self._dll,
#             "logger_init",
#             [l_charp, l_int, ctypes.POINTER(logger_metadata_obj)],
#             l_boolean,
#         )
#         self._set_level = _bind_function(
#             self._dll,
#             "logger_setLevel",
#             [l_int],
#             None,
#         )
#         self._flush = _bind_function(
#             self._dll,
#             "logger_flush",
#             None,
#             None,
#         )
#         self._shutdown = _bind_function(
#             self._dll,
#             "logger_shutdown",
#             None,
#             None,
#         )
#         self._write = _bind_function(
#             self._dll,
#             "logger_write",
#             [
#                 l_int,
#                 l_charp,
#             ],
#             None,
#         )
#         self._get_metadata = _bind_function(
#             self._dll,
#             "logger_getMetaData",
#             None,
#             logger_metadata_obj,
#         )

#     def initialize(
#         self,
#         file_path: str = DEFAULT_LOG_FILE_PATH,
#         minimum_level: log_level = log_level.TRACE,
#         userMeta: Optional[logger_metadata_obj] = None,
#     ) -> bool:
#         global _isLoggerInitialized

#         if not _isLoggerInitialized:
#             meta_ptr = ctypes.byref(userMeta) if userMeta is not None else None
#             _isLoggerInitialized = True

#             print("Logging sub-system initialized.")

#             return self._init(_to_bytes(file_path), int(minimum_level), meta_ptr)

#         print("WARNING: Trying to initialize logging sub-system while it was already initialized")

#         return False

#     def setLevel(self, level: log_level) -> None:
#         self._set_level(int(level))

#     def disable(self):
#         self.setLevel(log_level.NONE)

#     def flush(self) -> None:
#         self._flush()

#     def shutdown(self) -> None:
#         self._shutdown()

#     def getMetadata(self) -> logger_metadata_obj:
#         return self._get_metadata()

#     def write(self, level: log_level, message: object, *args, **kwargs) -> None:
#         rendered = _format_pythonStyle(message, *args, **kwargs)
#         self._write(
#             int(level),
#             b"%s",
#             _to_bytes(rendered),
#         )

#     def trace(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.TRACE, message, *args, **kwargs)

#     def debug(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.DEBUG, message, *args, **kwargs)

#     def info(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.INFO, message, *args, **kwargs)

#     def warning(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.WARNING, message, *args, **kwargs)

#     def error(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.ERROR, message, *args, **kwargs)

#     def fatal(self, message: object, *args, **kwargs) -> None:
#         self.write(log_level.FATAL, message, *args, **kwargs)


# if __name__ == "__main__":
#     log = Logger(DLL_PATH)

#     meta = logger_metadata_obj()
#     meta.app.name = b"Test Py Logger App"

#     if log.initialize(userMeta=meta):
#         workers = 4
#         log.info(f"Engine started with {workers} workers")

#         log.debug("Frame {} took {:.2f} ms", 108, 4.356)
#         log.warning("Backend={backend}, ratio={ratio:.1%}", backend="D3D11", ratio=0.875)

#         log.info("100% raw string with literal {braces} untouched")
#         log.trace("trace")
#         log.fatal("fatal")

#         log.flush()
#         log.shutdown()


# logger = Logger(DLL_PATH)


# __all__ = [
#     # All constants
#     "logger",
#     "DLL_PATH",
#     "DEFAULT_LOG_FILE_PATH",

#     # All types
#     "log_level",
#     "logger_metadata_obj",

#     # All classes
#     "Logger",
# ]



















from enum import IntEnum
from typing import Optional

from _clogger import ffi, lib


DEFAULT_LOG_FILE_PATH = "logs/app.log"

_isLoggerInitialized = False


class log_level(IntEnum):
    TRACE   = lib.LOG_LEVEL_TRACE
    DEBUG   = lib.LOG_LEVEL_DEBUG
    INFO    = lib.LOG_LEVEL_INFO
    WARNING = lib.LOG_LEVEL_WARNING
    ERROR   = lib.LOG_LEVEL_ERROR
    FATAL   = lib.LOG_LEVEL_FATAL
    NONE    = lib.LOG_LEVEL_NONE


logger_metadata_obj = ffi.typeof("logger_metadata_obj")


def _to_cstr(val: Optional[str], keepalive: list) -> Optional[object]:
    if val is None:
        return ffi.NULL
    c_buf = ffi.new("char[]", val.encode("utf-8"))
    keepalive.append(c_buf)
    return c_buf


def _format_pythonStyle(message: object, *args, **kwargs) -> str:
    text = str(message)
    if args or kwargs:
        return text.format(*args, **kwargs)
    return text


class Logger:
    def __init__(self):
        self._keepalive: list = []

    def create_metadata(
        self,
        *,
        name: Optional[str] = None,
        version: Optional[str] = None,
        buildProfile: Optional[str] = None,
        buildId: Optional[str] = None,
        activeBackend: Optional[str] = None,
        backends: Optional[str] = None,
        flags: Optional[str] = None,
        crtMode: Optional[str] = None,
    ):
        meta = ffi.new("logger_metadata_obj *")
        meta.app.name = _to_cstr(name, self._keepalive)
        meta.app.version = _to_cstr(version, self._keepalive)
        meta.app.buildProfile = _to_cstr(buildProfile, self._keepalive)
        meta.app.buildId = _to_cstr(buildId, self._keepalive)
        meta.app.activeBackend = _to_cstr(activeBackend, self._keepalive)
        meta.platform.backends = _to_cstr(backends, self._keepalive)
        meta.toolChain.compiler.flags = _to_cstr(flags, self._keepalive)
        meta.toolChain.compiler.crtMode = _to_cstr(crtMode, self._keepalive)
        return meta

    def initialize(
        self,
        file_path: str = DEFAULT_LOG_FILE_PATH,
        minimum_level: log_level = log_level.TRACE,
        userMeta=None,
    ) -> bool:
        global _isLoggerInitialized

        if not _isLoggerInitialized:
            c_path = _to_cstr(file_path, self._keepalive)
            meta_ptr = userMeta if userMeta is not None else ffi.NULL

            ok = bool(lib.logger_init(c_path, int(minimum_level), meta_ptr))
            if ok:
                _isLoggerInitialized = True
                print("Logging sub-system initialized.")
            return ok

        print("WARNING: Trying to initialize logging sub-system while it was already initialized")
        return False

    def setLevel(self, level: log_level) -> None:
        lib.logger_setLevel(int(level))

    def disable(self) -> None:
        self.setLevel(log_level.NONE)

    def flush(self) -> None:
        lib.logger_flush()

    def shutdown(self) -> None:
        global _isLoggerInitialized
        lib.logger_shutdown()
        _isLoggerInitialized = False

    def getMetadata(self):
        return lib.logger_getMetaData()

    def write(self, level: log_level, message: object, *args, **kwargs) -> None:
        rendered = _format_pythonStyle(message, *args, **kwargs)
        c_msg = ffi.new("char[]", rendered.encode("utf-8"))
        lib.logger_write_msg(int(level), c_msg)

    def trace(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.TRACE, message, *args, **kwargs)

    def debug(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.DEBUG, message, *args, **kwargs)

    def info(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.INFO, message, *args, **kwargs)

    def warning(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.WARNING, message, *args, **kwargs)

    def error(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.ERROR, message, *args, **kwargs)

    def fatal(self, message: object, *args, **kwargs) -> None:
        self.write(log_level.FATAL, message, *args, **kwargs)


logger = Logger()


if __name__ == "__main__":
    meta = logger.create_metadata(name="Test Py Logger App")

    if logger.initialize(userMeta=meta):
        workers = 4
        logger.info(f"Engine started with {workers} workers")

        logger.debug("Frame {} took {:.2f} ms", 108, 4.356)
        logger.warning("Backend={backend}, ratio={ratio:.1%}", backend="D3D11", ratio=0.875)

        logger.info("100% raw string with literal {braces} untouched")
        logger.trace("trace")
        logger.fatal("fatal")

        logger.flush()
        logger.shutdown()


__all__ = [
    "logger",
    "DEFAULT_LOG_FILE_PATH",
    "log_level",
    "logger_metadata_obj",
    "Logger",
]