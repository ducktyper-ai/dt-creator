"""Assert that built distributions expose only the intentional package surface."""

import tarfile
import zipfile
from pathlib import Path

from scripts.build_paths import dist_dir


def main() -> None:
    wheels = tuple(dist_dir().glob("*.whl"))
    sdists = tuple(dist_dir().glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, "dist must contain one wheel and one sdist"
    wheel = wheels[0]
    sdist = sdists[0]

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
    assert "zeo_creator/py.typed" in wheel_names
    assert "zeo_creator/schemas/catalog.json" in wheel_names
    assert "zeo_creator/schemas/content-brief.v1.schema.json" in wheel_names
    assert "zeo_creator/schemas/artifact-manifest.v1.schema.json" in wheel_names
    assert not any("tests/" in name or ".claude/" in name for name in wheel_names)

    with tarfile.open(sdist) as archive:
        names = [Path(name).parts[1:] for name in archive.getnames() if len(Path(name).parts) > 1]
    forbidden = {
        ".claude",
        ".github",
        "tests",
        "examples",
        "docs",
        "reference",
        "uv.lock",
        "Makefile",
        "AGENTS.md",
        "CLAUDE.md",
    }
    assert not any(parts and parts[0] in forbidden for parts in names)

    print(f"verified {wheel.name} and {sdist.name}")


if __name__ == "__main__":
    main()
