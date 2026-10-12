"""Where the gate's builds go: dist/ in the checkout unless ZEOCREATOR_DIST_DIR moves it."""

import os
from pathlib import Path


def dist_dir(root: Path | None = None) -> Path:
    configured = os.environ.get("ZEOCREATOR_DIST_DIR")
    if configured:
        return Path(configured)
    return (root if root is not None else Path()) / "dist"
