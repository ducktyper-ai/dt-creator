"""Check the original distribution boundary plus installed email reference resources."""

import json
import zipfile

from scripts.build_paths import dist_dir
from scripts.check_distribution import main as original_check
from scripts.export_reference_artifacts_v4 import MODELS


def main() -> None:
    original_check()
    with zipfile.ZipFile(next(dist_dir().glob("*.whl"))) as archive:
        names = set(archive.namelist())
        for name, _ in MODELS:
            assert f"zeo_creator/schemas/{name}.v3.schema.json" in names
        for name in (
            "email-marketing.json",
            "email-program-suite-v3.json",
            "email-effect-family-v3.json",
            "email-digest-vectors.json",
            "docs/guides/email-marketing.md",
        ):
            assert f"zeo_creator/reference_artifacts/{name}" in names
        runs = json.loads(archive.read("zeo_creator/reference_artifacts/email-marketing.json"))
        assert len({run["publication"]["publication_id"] for run in runs}) == 3
    print(
        "verified all email schemas, vectors, three-publication artifacts and documentation in wheel"
    )


if __name__ == "__main__":
    main()
