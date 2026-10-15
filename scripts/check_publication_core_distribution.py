"""Keep the JavaScript packages out of the actual Python wheel and sdist."""

import tarfile
import zipfile
from pathlib import Path, PurePosixPath


def check_members(names: list[str]) -> None:
    for name in names:
        parts = PurePosixPath(name).parts
        if (
            "packages" in parts
            or "publication-core" in parts
            or PurePosixPath(name).name in {".node-version", "package.json"}
        ):
            raise ValueError("JavaScript packages must not enter Python distributions")


def check_distributions(directory: Path) -> None:
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("expected one actual wheel and one actual sdist")
    with zipfile.ZipFile(wheels[0]) as wheel:
        check_members(wheel.namelist())
    with tarfile.open(sdists[0]) as sdist:
        check_members(sdist.getnames())


def main() -> None:
    check_distributions(Path("dist"))
    print("verified JavaScript packages absent from actual Python wheel and sdist")


if __name__ == "__main__":
    main()
