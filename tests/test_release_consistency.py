"""Publication must reject mismatched names, versions, tags and built metadata."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release_v1 import distributions, metadata


def prepare(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "zeocreator"\nversion = "0.5.3"\nrequires-python = ">=3.14"\n'
    )
    (root / "RELEASE_NOTES.md").write_text("# zeocreator 0.5.3\n")
    (root / "CHANGELOG.md").write_text("## 0.5.3 — 2026-09-09\n")


def test_current_release_and_matching_tag() -> None:
    assert metadata(Path.cwd(), "v0.6.1") == ("0.6.1", "3.14")


@pytest.mark.parametrize("tag", ["v0.5.2", "main", "0.5.3", "v0.5.3.dev0"])
def test_wrong_tag_refuses(tmp_path: Path, tag: str) -> None:
    prepare(tmp_path)
    with pytest.raises(ValueError, match="tag"):
        metadata(tmp_path, tag)


@pytest.mark.parametrize(
    "old,new",
    [
        ('name = "zeocreator"', 'name = "zeo-creator"'),
        ('version = "0.5.3"', 'version = "0.5.3.dev0"'),
        ('requires-python = ">=3.14"', 'requires-python = ">=3.14,<4"'),
    ],
)
def test_incompatible_publisher_metadata_refuses(tmp_path: Path, old: str, new: str) -> None:
    prepare(tmp_path)
    p = tmp_path / "pyproject.toml"
    p.write_text(p.read_text().replace(old, new))
    with pytest.raises(ValueError):
        metadata(tmp_path)


@pytest.mark.parametrize("path", ["RELEASE_NOTES.md", "CHANGELOG.md"])
def test_stale_release_document_refuses(tmp_path: Path, path: str) -> None:
    prepare(tmp_path)
    p = tmp_path / path
    p.write_text(p.read_text().replace("0.5.3", "0.5.2"))
    with pytest.raises(ValueError):
        metadata(tmp_path)


@pytest.mark.parametrize("wrong", [False, True])
def test_checks_built_metadata_not_only_filename(tmp_path: Path, wrong: bool) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / ".gitignore").write_text("*")  # uv build adds this non-distribution marker.
    raw = f"Name: zeocreator\nVersion: {'0.5.2' if wrong else '0.5.3'}\nRequires-Python: >=3.14\n".encode()
    with zipfile.ZipFile(dist / "zeocreator-0.5.3-py3-none-any.whl", "w") as wheel:
        wheel.writestr("zeocreator-0.5.3.dist-info/METADATA", raw)
    with tarfile.open(dist / "zeocreator-0.5.3.tar.gz", "w:gz") as sdist:
        info = tarfile.TarInfo("zeocreator-0.5.3/PKG-INFO")
        info.size = len(raw)
        sdist.addfile(info, io.BytesIO(raw))
    if wrong:
        with pytest.raises(ValueError, match="built metadata"):
            distributions(tmp_path, "0.5.3", "3.14")
    else:
        distributions(tmp_path, "0.5.3", "3.14")
        (dist / "unexpected.whl").touch()
        with pytest.raises(ValueError, match="only the exact"):
            distributions(tmp_path, "0.5.3", "3.14")


def test_documented_capability_ids_match_the_installed_registry() -> None:
    import re

    from zeo_creator.registry import capability_manifests

    live = {manifest.id.canonical() for manifest in capability_manifests()}
    catalog = Path("docs/reference/capabilities.md").read_text()
    assert set(re.findall(r"creator\.[a-z_]+@[0-9.]+", catalog)) == live
    for path in Path("docs").rglob("*.md"):
        mentioned = set(re.findall(r"creator\.[a-z_]+@[0-9.]+", path.read_text()))
        assert mentioned <= live, (path, mentioned - live)
