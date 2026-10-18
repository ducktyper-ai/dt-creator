"""Refuse mismatched release identity, notes, tags or built distribution metadata."""

import argparse
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from scripts.build_paths import dist_dir


def metadata(root: Path, tag: str | None = None) -> tuple[str, str]:
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if project["name"] != "zeocreator":
        raise ValueError("distribution must match the zeocreator trusted publisher")
    version = project["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("release version must be final X.Y.Z")
    if tag is not None and tag != f"v{version}":
        raise ValueError("tag does not match the package version")
    floor = re.fullmatch(r">=([0-9]+\.[0-9]+)", project["requires-python"])
    if floor is None:
        raise ValueError("Python floor must be explicit >=X.Y")
    if not (root / "RELEASE_NOTES.md").read_text().startswith(f"# zeocreator {version}\n"):
        raise ValueError("release notes do not match the package version")
    if f"## {version} — " not in (root / "CHANGELOG.md").read_text():
        raise ValueError("changelog is missing the release")
    return version, floor[1]


def distributions(root: Path, version: str, floor: str) -> None:
    wheel = dist_dir(root) / f"zeocreator-{version}-py3-none-any.whl"
    sdist = dist_dir(root) / f"zeocreator-{version}.tar.gz"
    if {p for p in dist_dir(root).iterdir() if p.name != ".gitignore"} != {wheel, sdist}:
        raise ValueError("dist must contain only the exact release wheel and sdist")
    with zipfile.ZipFile(wheel) as archive:
        raw_wheel = archive.read(f"zeocreator-{version}.dist-info/METADATA")
    with tarfile.open(sdist) as archive:
        member = archive.extractfile(f"zeocreator-{version}/PKG-INFO")
        if member is None:
            raise ValueError("sdist metadata missing")
        raw_sdist = member.read()
    for raw in (raw_wheel, raw_sdist):
        info = BytesParser().parsebytes(raw)
        if (info["Name"], info["Version"], info["Requires-Python"]) != (
            "zeocreator",
            version,
            f">={floor}",
        ):
            raise ValueError("built metadata disagrees with release identity")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--dist", action="store_true")
    args = parser.parse_args()
    version, floor = metadata(Path.cwd(), args.tag)
    if args.dist:
        distributions(Path.cwd(), version, floor)
    print(f"verified zeocreator {version} on Python >= {floor}")


if __name__ == "__main__":
    main()
