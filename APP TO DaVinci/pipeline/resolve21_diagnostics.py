import os
import sys
from pathlib import Path


paths = [
    Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"),
    Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules"),
    Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Modules"),
]

for path in paths:
    print(f"{path}|EXISTS={path.exists()}")

for path in paths:
    if path.exists() and str(path) not in sys.path:
        sys.path.append(str(path))

print(f"PYTHONPATH={os.environ.get('PYTHONPATH','')}")

try:
    import DaVinciResolveScript as dvr_script  # type: ignore

    resolve = dvr_script.scriptapp("Resolve")
    print(f"IMPORT_OK=True|RESOLVE_CONNECTED={resolve is not None}")
except Exception as exc:
    print(f"IMPORT_OK=False|ERROR={exc}")
