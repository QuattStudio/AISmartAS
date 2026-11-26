from pathlib import Path
import sys


def project_root() -> Path:
    """Return the project folder for both source runs and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        executable_folder = Path(sys.executable).resolve().parent
        for candidate in (executable_folder, executable_folder.parent):
            if (candidate / "resources").is_dir():
                return candidate
        if executable_folder.name.lower() == "app":
            return executable_folder.parent
        return executable_folder

    return Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)
