"""Verify the shared receipt schema and behavioral corpus in the built wheel."""

import json
import zipfile

from scripts.build_paths import dist_dir
from scripts.check_distribution_v5 import main as previous_check
from zeo_creator.reference.email_receipt_conformance import (
    creator_validators,
    result_schema,
    verify_cases,
)


def main() -> None:
    previous_check()
    with zipfile.ZipFile(next(dist_dir().glob("*.whl"))) as archive:
        schema = json.loads(archive.read("zeo_creator/schemas/email-remote-result.v4.schema.json"))
        assert schema == result_schema()
        corpus = json.loads(
            archive.read("zeo_creator/reference_artifacts/email-receipt-conformance-v1.json")
        )
        assert not verify_cases(corpus, creator_validators())
        assert (
            "zeo_creator/reference_artifacts/docs/guides/email-receipt-conformance.md"
            in archive.namelist()
        )
    print(f"verified installed receipt union and {len(corpus['cases'])} portable behavioral cases")


if __name__ == "__main__":
    main()
