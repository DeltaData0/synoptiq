"""Install pinned web dependencies and build the offline frontend."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from _run_context import ROOT, emit

# Ensure newly installed Node.js on Windows is picked up even before terminal restart
if platform.system() == "Windows":
    node_dir = Path("C:/Program Files/nodejs")
    if node_dir.is_dir() and str(node_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{node_dir};{os.environ.get('PATH', '')}"

emit("web", "web/dist")
use_shell = platform.system() == "Windows"
subprocess.run(["npm", "install"], cwd=ROOT / "web", check=True, shell=use_shell)
subprocess.run(["npm", "run", "build"], cwd=ROOT / "web", check=True, shell=use_shell)


