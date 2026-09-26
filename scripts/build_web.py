"""Install pinned web dependencies and build the offline frontend."""

from __future__ import annotations

import subprocess

from _run_context import ROOT, emit

emit("web", "web/dist")
subprocess.run(["npm", "install"], cwd=ROOT / "web", check=True)
subprocess.run(["npm", "run", "build"], cwd=ROOT / "web", check=True)

