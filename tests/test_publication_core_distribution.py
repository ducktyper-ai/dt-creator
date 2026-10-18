"""The distribution gate must inspect both real archive formats and fail closed."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_publication_core_distribution import check_distributions


def write_archives(root: Path, wheel_extra: str = "", sdist_extra: str = "") -> None:
    with zipfile.ZipFile(root / "zeocreator-test.whl", "w") as archive:
        archive.writestr("zeo_creator/__init__.py", "")
        if wheel_extra:
            archive.writestr(wheel_extra, "export const accidental = true;")
    with tarfile.open(root / "zeocreator-test.tar.gz", "w:gz") as archive:
        for name in ("zeocreator-test/src/zeo_creator/__init__.py", sdist_extra):
            if name:
                raw = b"placeholder"
                entry = tarfile.TarInfo(name)
                entry.size = len(raw)
                archive.addfile(entry, io.BytesIO(raw))


def test_python_only_distributions_pass(tmp_path: Path) -> None:
    write_archives(tmp_path)
    check_distributions(tmp_path)


@pytest.mark.parametrize("archive", ["wheel", "sdist"])
@pytest.mark.parametrize(
    "path",
    [
        "packages/publication-core/index.mjs",
        "zeocreator-test/packages/publication-core/index.mjs",
        "zeocreator-test/publication-core/package.json",
        "zeocreator-test/packages/other-package/",
        "zeocreator-test/.node-version",
        "zeocreator-test/package.json",
    ],
)
def test_either_archive_with_javascript_package_refuses(
    tmp_path: Path, archive: str, path: str
) -> None:
    write_archives(
        tmp_path,
        wheel_extra=path if archive == "wheel" else "",
        sdist_extra=path if archive == "sdist" else "",
    )
    with pytest.raises(ValueError, match="must not enter"):
        check_distributions(tmp_path)


@pytest.mark.parametrize("missing", ["*.whl", "*.tar.gz"])
def test_missing_distribution_refuses(tmp_path: Path, missing: str) -> None:
    write_archives(tmp_path)
    next(tmp_path.glob(missing)).unlink()
    with pytest.raises(ValueError, match="one actual"):
        check_distributions(tmp_path)
