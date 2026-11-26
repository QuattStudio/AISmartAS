

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
import os
import platform
import struct
import sys
import threading
from typing import Optional

if sys.platform == "win32":
    import ctypes


DEFAULT_LOG_FILE_PATH = "logs/app.log"
LOGGER_QUEUE_CAPACITY = 1024

_isLoggerInitialized = False


class log_level(IntEnum):
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    FATAL = 5
    NONE = 255


@dataclass
class _AppMeta:
    name: Optional[str] = None
    version: Optional[str] = None
    buildProfile: Optional[str] = None
    buildId: Optional[str] = None
    activeBackend: Optional[str] = None


@dataclass
class _CompilerMeta:
    name: Optional[str] = None
    version: Optional[str] = None
    flags: Optional[str] = None
    std: Optional[str] = None
    crtMode: Optional[str] = None


@dataclass
class _ToolChainMeta:
    compiler: _CompilerMeta = field(default_factory=_CompilerMeta)
    ptrBits: int = struct.calcsize("P") * 8
    isLittleEndian: bool = sys.byteorder == "little"


@dataclass
class _PlatformMeta:
    os: Optional[str] = None
    backends: Optional[str] = None


@dataclass
class _CoresMeta:
    physical: int = 1
    logical: int = 1


@dataclass
class _HardwareMeta:
    arch: Optional[str] = None
    cpu: Optional[str] = None
    isa: Optional[str] = None
    cores: _CoresMeta = field(default_factory=_CoresMeta)
    ram: int = 0
    cacheLineBytes: int = 64
    pageSizeBytes: int = 4096


@dataclass
class _MainMeta:
    fileName: Optional[str] = None
    session: Optional[str] = None
    pid: int = 0
    minLevel: int = 0


@dataclass
class logger_metadata_obj:
    app: _AppMeta = field(default_factory=_AppMeta)
    toolChain: _ToolChainMeta = field(default_factory=_ToolChainMeta)
    platform: _PlatformMeta = field(default_factory=_PlatformMeta)
    hardware: _HardwareMeta = field(default_factory=_HardwareMeta)
    main: _MainMeta = field(default_factory=_MainMeta)


@dataclass
class _LogRecord:
    level: log_level
    timestamp: str
    message: str


def _format_pythonStyle(message: object, *args, **kwargs) -> str:
    text = str(message)
    if args or kwargs:
        return text.format(*args, **kwargs)
    return text


def _level_name(level: log_level) -> str:
    names = {
        log_level.TRACE: "TRACE",
        log_level.DEBUG: "DEBUG",
        log_level.INFO: "INFO",
        log_level.WARNING: "WARNING",
        log_level.ERROR: "ERROR",
        log_level.FATAL: "FATAL",
    }
    return names.get(level, "UNKNOWN")


def _level_color(level: log_level) -> str:
    colors = {
        log_level.TRACE: "\x1b[90m",
        log_level.DEBUG: "\x1b[38;2;50;230;180m",
        log_level.INFO: "\x1b[38;2;39;138;163m",
        log_level.WARNING: "\x1b[33m",
        log_level.ERROR: "\x1b[31m",
        log_level.FATAL: "\x1b[1;37;41m",
    }
    return colors.get(level, "\x1b[0m")


def _enable_ansi_colors() -> bool:
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if handle in (-1, 0) or not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            if not kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING):
                return False
        except Exception:
            return False

    return True


def _detect_physical_cores(logical: int) -> int:
    if sys.platform.startswith("linux"):
        try:
            pairs = set()
            cur_pkg = 0
            cur_core = -1
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("physical id"):
                        _, _, val = line.partition(":")
                        cur_pkg = int(val.strip() or "0")
                    elif line.startswith("core id"):
                        _, _, val = line.partition(":")
                        cur_core = int(val.strip() or "-1")
                    elif not line.strip():
                        if cur_core >= 0:
                            pairs.add((cur_pkg, cur_core))
                        cur_pkg = 0
                        cur_core = -1
            if pairs:
                return len(pairs)
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            buf_len = ctypes.c_uint32(0)
            kernel32.GetLogicalProcessorInformation(None, ctypes.byref(buf_len))
            if buf_len.value > 0:
                buf = ctypes.create_string_buffer(buf_len.value)
                if kernel32.GetLogicalProcessorInformation(buf, ctypes.byref(buf_len)):
                    # SYSTEM_LOGICAL_PROCESSOR_INFORMATION on x64 is 24 bytes:
                    # ULONG_PTR ProcessorMask (8), LOGICAL_PROCESSOR_RELATIONSHIP Relationship (4), union (12)
                    entry_size = 24 if struct.calcsize("P") == 8 else 12
                    count = buf_len.value // entry_size
                    phys = 0
                    for i in range(count):
                        offset = i * entry_size
                        rel = struct.unpack_from("<I", buf, offset + struct.calcsize("P"))[0]
                        if rel == 0:  # RelationProcessorCore
                            phys += 1
                    if phys > 0:
                        return phys
        except Exception:
            pass
    return logical


def _detect_ram_mb() -> int:
    if sys.platform == "win32":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_uint32),
                    ("dwMemoryLoad", ctypes.c_uint32),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys // (1024 * 1024))
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return int(parts[1]) // 1024
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            if hasattr(os, "sysconf"):
                page_size = os.sysconf("SC_PAGE_SIZE")
                phys_pages = os.sysconf("SC_PHYS_PAGES")
                if page_size > 0 and phys_pages > 0:
                    return int((page_size * phys_pages) // (1024 * 1024))
        except Exception:
            pass
    return 0


def _detect_isa() -> str:
    machine = platform.machine().lower()
    if machine not in ("x86_64", "amd64", "i386", "i686"):
        return "Baseline / Scalar"

    flags = []
    if sys.platform == "win32":
        try:
            IsProcessorFeaturePresent = ctypes.windll.kernel32.IsProcessorFeaturePresent
            features = [
                (10, "SSE2"),  # PF_XMMI64_INSTRUCTIONS_AVAILABLE
                (13, "SSE3"),  # PF_SSE3_INSTRUCTIONS_AVAILABLE
                (37, "FMA"),   # PF_FMA_INSTRUCTIONS_AVAILABLE
                (36, "AVX"),   # PF_AVX_INSTRUCTIONS_AVAILABLE
                (40, "AVX2"),  # PF_AVX2_INSTRUCTIONS_AVAILABLE
            ]
            for code, name in features:
                if IsProcessorFeaturePresent(code):
                    flags.append(name)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("flags"):
                        cpu_flags = set(line.split(":")[1].split())
                        mapping = [
                            ("sse2", "SSE2"),
                            ("pni", "SSE3"),
                            ("fma", "FMA"),
                            ("avx", "AVX"),
                            ("avx2", "AVX2"),
                            ("avx512f", "AVX-512F"),
                        ]
                        for raw, label in mapping:
                            if raw in cpu_flags:
                                flags.append(label)
                        break
        except Exception:
            pass

    return " ".join(flags) if flags else "Baseline / Scalar"


def _build_metadata(
    user_meta: Optional[logger_metadata_obj],
    resolved_path: str,
    session_stamp: str,
    min_level: log_level,
) -> logger_metadata_obj:
    logical = os.cpu_count() or 1
    physical = _detect_physical_cores(logical)
    page_size = 4096
    try:
        if hasattr(os, "sysconf"):
            ps = os.sysconf("SC_PAGESIZE")
            if ps > 0:
                page_size = int(ps)
    except Exception:
        pass

    cache_line = 64
    try:
        if hasattr(os, "sysconf"):
            cl = os.sysconf("SC_LEVEL1_DCACHE_LINESIZE")
            if cl > 0:
                cache_line = int(cl)
    except Exception:
        pass

    cpu_name = platform.processor().strip() or "Unknown CPU"
    if sys.platform.startswith("linux") and cpu_name == "Unknown CPU":
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_name = line.split(":", 1)[1].strip() or "Unknown CPU"
                        break
        except Exception:
            pass

    os_name = "Windows" if sys.platform == "win32" else (platform.system() or "POSIX")

    meta = logger_metadata_obj(
        app=_AppMeta(
            name="App-Unknown",
            version="0.0.0",
            buildProfile="Unknown",
            buildId="Dev",
            activeBackend="None",
        ),
        toolChain=_ToolChainMeta(
            compiler=_CompilerMeta(
                name="CPython",
                version=platform.python_version(),
                flags="N/A",
                std=f"Python {sys.version_info.major}.{sys.version_info.minor}",
                crtMode="Python Runtime",
            ),
            ptrBits=struct.calcsize("P") * 8,
            isLittleEndian=(sys.byteorder == "little"),
        ),
        platform=_PlatformMeta(
            os=os_name,
            backends="None",
        ),
        hardware=_HardwareMeta(
            arch=platform.machine() or "Unknown",
            cpu=cpu_name,
            isa=_detect_isa(),
            cores=_CoresMeta(physical=physical, logical=logical),
            ram=_detect_ram_mb(),
            cacheLineBytes=cache_line,
            pageSizeBytes=page_size,
        ),
        main=_MainMeta(
            fileName=resolved_path,
            session=session_stamp,
            pid=os.getpid(),
            minLevel=int(min_level),
        ),
    )

    if user_meta is not None:
        if user_meta.app.name is not None:
            meta.app.name = user_meta.app.name
        if user_meta.app.version is not None:
            meta.app.version = user_meta.app.version
        if user_meta.app.buildProfile is not None:
            meta.app.buildProfile = user_meta.app.buildProfile
        if user_meta.app.buildId is not None:
            meta.app.buildId = user_meta.app.buildId
        if user_meta.app.activeBackend is not None:
            meta.app.activeBackend = user_meta.app.activeBackend
        if user_meta.platform.backends is not None:
            meta.platform.backends = user_meta.platform.backends
        if user_meta.toolChain.compiler.flags is not None:
            meta.toolChain.compiler.flags = user_meta.toolChain.compiler.flags
        if user_meta.toolChain.compiler.crtMode is not None:
            meta.toolChain.compiler.crtMode = user_meta.toolChain.compiler.crtMode

    return meta


def _open_unique_log_file(file_path: str, session_stamp: str):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    base = file_path[:-4] if file_path.endswith(".log") else file_path

    candidate = f"{base}_{session_stamp}.log"
    if not os.path.exists(candidate):
        return open(candidate, "w", encoding="utf-8", errors="replace"), candidate

    for suffix in range(1, 1000):
        candidate = f"{base}_{session_stamp}_{suffix}.log"
        if not os.path.exists(candidate):
            return open(candidate, "w", encoding="utf-8", errors="replace"), candidate

    raise RuntimeError(f"Could not create unique log file for base '{base}'")


def _write_header(file_obj, meta: logger_metadata_obj) -> None:
    level_name = _level_name(log_level(meta.main.minLevel))
    endian_str = "Little-Endian" if meta.toolChain.isLittleEndian else "Big-Endian"

    header = (
        "================================================================================\n"
        "[App]\n"
        f"  Name           : {meta.app.name if meta.app.name is not None else 'N/A'}\n"
        f"  Version        : {meta.app.version if meta.app.version is not None else 'N/A'}\n"
        f"  Build Profile  : {meta.app.buildProfile if meta.app.buildProfile is not None else 'N/A'}\n"
        f"  Build ID       : {meta.app.buildId if meta.app.buildId is not None else 'N/A'}\n"
        f"  Active Backend : {meta.app.activeBackend if meta.app.activeBackend is not None else 'N/A'}\n"
        "\n"
        "[ToolChain]\n"
        f"  Compiler       : {meta.toolChain.compiler.name or 'Unknown'} ({meta.toolChain.compiler.version or 'Unknown'})\n"
        f"  C Standard     : {meta.toolChain.compiler.std or 'Unknown'}\n"
        f"  Flags          : {meta.toolChain.compiler.flags if meta.toolChain.compiler.flags is not None else 'N/A'}\n"
        f"  CRT Mode       : {meta.toolChain.compiler.crtMode if meta.toolChain.compiler.crtMode is not None else 'N/A'}\n"
        f"  Pointer Width  : {meta.toolChain.ptrBits}-bit\n"
        f"  Endianness     : {endian_str}\n"
        "\n"
        "[Platform]\n"
        f"  OS             : {meta.platform.os or 'Unknown'}\n"
        f"  Backends       : {meta.platform.backends if meta.platform.backends is not None else 'None'}\n"
        "\n"
        "[Hardware]\n"
        f"  Architecture   : {meta.hardware.arch or 'Unknown'}\n"
        f"  CPU            : {meta.hardware.cpu or 'Unknown'}\n"
        f"  ISA / SIMD     : {meta.hardware.isa if meta.hardware.isa is not None else 'None'}\n"
        f"  Cores          : {meta.hardware.cores.physical} Physical / {meta.hardware.cores.logical} Logical\n"
        f"  RAM            : {meta.hardware.ram} MB\n"
        f"  Cache Line     : {meta.hardware.cacheLineBytes} bytes\n"
        f"  Page Size      : {meta.hardware.pageSizeBytes} bytes\n"
        "\n"
        "[Main / Session]\n"
        f"  File Name      : {meta.main.fileName if meta.main.fileName is not None else 'N/A'}\n"
        f"  Session        : {meta.main.session if meta.main.session is not None else 'N/A'}\n"
        f"  PID            : {meta.main.pid}\n"
        f"  Min Level      : {level_name}\n"
        "================================================================================\n\n"
    )
    file_obj.write(header)
    file_obj.flush()


class Logger:
    def __init__(self):
        self._lock = threading.Lock()
        self._has_messages = threading.Condition(self._lock)
        self._has_space = threading.Condition(self._lock)
        self._flushed = threading.Condition(self._lock)
        self._output_lock = threading.Lock()

        self._queue: deque[_LogRecord] = deque()
        self._minimum_level: log_level = log_level.TRACE
        self._file = None
        self._meta: logger_metadata_obj = logger_metadata_obj()

        self._initialized: bool = False
        self._stopping: bool = False
        self._submitted: int = 0
        self._completed: int = 0
        self._color_enabled: bool = True
        self._worker: Optional[threading.Thread] = None

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
    ) -> logger_metadata_obj:
        return logger_metadata_obj(
            app=_AppMeta(
                name=name,
                version=version,
                buildProfile=buildProfile,
                buildId=buildId,
                activeBackend=activeBackend,
            ),
            toolChain=_ToolChainMeta(
                compiler=_CompilerMeta(
                    flags=flags,
                    crtMode=crtMode,
                )
            ),
            platform=_PlatformMeta(
                backends=backends,
            ),
        )

    def initialize(
        self,
        file_path: str = DEFAULT_LOG_FILE_PATH,
        minimum_level: log_level = log_level.TRACE,
        userMeta: Optional[logger_metadata_obj] = None,
    ) -> bool:
        global _isLoggerInitialized

        if _isLoggerInitialized or self._initialized:
            print("WARNING: Trying to initialize logging sub-system while it was already initialized")
            return False

        if not file_path:
            return False

        try:
            session_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file, resolved_path = _open_unique_log_file(file_path, session_stamp)
            meta = _build_metadata(userMeta, resolved_path, session_stamp, minimum_level)
            _write_header(log_file, meta)
        except OSError:
            return False

        with self._lock:
            self._queue.clear()
            self._minimum_level = log_level(minimum_level)
            self._file = log_file
            self._meta = meta
            self._submitted = 0
            self._completed = 0
            self._stopping = False
            self._color_enabled = _enable_ansi_colors()
            self._initialized = True

            worker = threading.Thread(target=self._worker_loop, name="LoggerWorker", daemon=False)
            self._worker = worker
            worker.start()

        _isLoggerInitialized = True
        print("Logging sub-system initialized.")
        return True

    def _emit(self, record: _LogRecord) -> None:
        name = _level_name(record.level)
        if self._color_enabled:
            color = _level_color(record.level)
            line = f"{color}[{record.timestamp}] [{name:<7}] > {record.message}\x1b[0m\n"
        else:
            line = f"[{record.timestamp}] [{name:<7}] > {record.message}\n"

        plain_line = f"[{record.timestamp}] [{name:<7}] > {record.message}\n"

        with self._output_lock:
            sys.stdout.write(line)
            sys.stdout.flush()

            if self._file is not None:
                self._file.write(plain_line)
                if record.level >= log_level.ERROR:
                    self._file.flush()

    def _worker_loop(self) -> None:
        while True:
            with self._lock:
                while len(self._queue) == 0 and not self._stopping:
                    self._has_messages.wait()

                if len(self._queue) == 0 and self._stopping:
                    break

                record = self._queue.popleft()
                self._has_space.notify()

            self._emit(record)

            with self._lock:
                self._completed += 1
                if self._completed == self._submitted:
                    self._flushed.notify_all()

        with self._output_lock:
            if self._file is not None:
                self._file.flush()
                self._file.close()
                self._file = None

    def setLevel(self, level: log_level) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._minimum_level = log_level(level)

    def disable(self) -> None:
        self.setLevel(log_level.NONE)

    def flush(self) -> None:
        if not self._initialized:
            return

        with self._lock:
            target = self._submitted
            while self._completed < target:
                self._flushed.wait()

        with self._output_lock:
            if self._file is not None:
                self._file.flush()

    def shutdown(self) -> None:
        global _isLoggerInitialized

        if not self._initialized:
            return

        with self._lock:
            self._stopping = True
            self._has_messages.notify_all()
            self._has_space.notify_all()
            worker = self._worker

        if worker is not None and worker.is_alive():
            worker.join()

        with self._lock:
            self._worker = None
            self._initialized = False

        _isLoggerInitialized = False

    def getMetadata(self) -> logger_metadata_obj:
        return self._meta

    def write(self, level: log_level, message: object, *args, **kwargs) -> None:
        if not self._initialized or message is None:
            return

        lvl = log_level(level)

        with self._lock:
            if lvl < self._minimum_level or self._stopping:
                return

            while len(self._queue) >= LOGGER_QUEUE_CAPACITY and not self._stopping:
                self._has_space.wait()

            if self._stopping:
                return

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rendered = _format_pythonStyle(message, *args, **kwargs)
            self._queue.append(_LogRecord(level=lvl, timestamp=timestamp, message=rendered))
            self._submitted += 1
            self._has_messages.notify()

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
