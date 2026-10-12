"""Verify the actual wheel's Runtime provider in an isolated locked environment."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.build_paths import dist_dir
from scripts.check_distribution_v8 import main as previous_check


def main() -> None:
    previous_check()
    root = Path.cwd()
    wheel = next(dist_dir(root).glob("*.whl"))
    # Reuse the exact existing lock, including the test runner. Never resolve
    # floating test dependencies or import this checkout from the wheel proof.
    requirements = subprocess.run(
        ["uv", "export", "--frozen", "--no-emit-project", "--format", "requirements-txt"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="creator-host-wheel-") as directory:
        isolated = Path(directory)
        requirements_path = isolated / "requirements.txt"
        requirements_path.write_text(requirements)
        env_path = isolated / "venv"
        python = env_path / "bin/python"
        subprocess.run(["uv", "venv", "--python", "3.14", str(env_path)], check=True)
        subprocess.run(
            [
                "uv",
                "pip",
                "sync",
                "--python",
                str(python),
                "--require-hashes",
                str(requirements_path),
            ],
            check=True,
        )
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            check=True,
        )
        shutil.copyfile(root / "tests/test_runtime_host.py", isolated / "test_runtime_host.py")
        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        for command in (
            [
                str(python),
                "-I",
                "-c",
                "import pathlib, zeo_creator, sys; assert pathlib.Path(zeo_creator.__file__).is_relative_to(sys.prefix)",
            ],
            [str(python), "-I", "-m", "zeo_creator.cli", "doctor", "--json"],
            [str(python), "-I", "-m", "pytest", "-q", "test_runtime_host.py"],
        ):
            subprocess.run(command, check=True, cwd=isolated, env=environment)
    print("verified actual installed Creator wheel and Core host subprocess conformance")


if __name__ == "__main__":
    main()
