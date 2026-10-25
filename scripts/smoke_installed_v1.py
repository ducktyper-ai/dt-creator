"""Exercise the exact installed release outside a checkout, with no provider access."""

import importlib.metadata
import pkgutil
import runpy
import sys

import zeo_creator
import zeo_creator.examples
from zeo_creator.registry import capability_manifests


def main() -> None:
    expected = sys.argv[1]
    if zeo_creator.__version__ != expected or importlib.metadata.version("zeocreator") != expected:
        raise ValueError("installed distribution does not match the published version")
    assert len(capability_manifests()) == 30
    names = sorted(row.name for row in pkgutil.iter_modules(zeo_creator.examples.__path__))
    assert names == [
        "assess_performance",
        "complete_content_portfolio",
        "create_content_brief",
        "email_marketing",
        "inspect_capabilities",
        "research_connector",
        "validate_and_prepare",
    ]
    for name in names:
        print(f"Running installed example: {name}", flush=True)
        runpy.run_module(f"zeo_creator.examples.{name}", run_name="__main__")
    runpy.run_module("zeo_creator.reference.email_receipt_conformance", run_name="__main__")
    print(f"Verified zeocreator=={expected}, seven installed examples and 135 receipt cases")


if __name__ == "__main__":
    main()
