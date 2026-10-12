"""Verify release metadata, legacy contracts, corpus and runnable wheel examples."""

import zipfile
from pathlib import Path

from scripts.build_paths import dist_dir
from scripts.check_distribution_v7 import main as previous_check
from scripts.check_release_v1 import distributions, metadata


def main() -> None:
    previous_check()
    version, floor = metadata(Path.cwd())
    distributions(Path.cwd(), version, floor)
    with zipfile.ZipFile(next(dist_dir().glob("*.whl"))) as archive:
        for source in Path("examples").glob("*.py"):
            assert archive.read(f"zeo_creator/examples/{source.name}") == source.read_bytes()
        for source in Path("reference/examples").glob("*.json"):
            assert (
                archive.read(f"zeo_creator/reference_artifacts/{source.name}")
                == source.read_bytes()
            )
    print("verified release identity and all runnable example sources and fixtures")


if __name__ == "__main__":
    main()
