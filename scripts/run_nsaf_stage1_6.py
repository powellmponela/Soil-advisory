from __future__ import annotations

"""
Sequential NSAF maize Stage 1-6 rerun.

Place in:
D:\dss\SOIL ADVISORY\scripts

Run from:
D:\dss\SOIL ADVISORY

Command:
python .\scripts\run_nsaf_stage1_6.py
"""

from pathlib import Path
from datetime import datetime
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
OUTPUTS = ROOT / "outputs"
LOG = OUTPUTS / "run_nsaf_stage1_6.log"

RUN_ORDER = [
    "0c_nsaf_data_legacy.py",
    "1a_nsaf_stage1_6_descriptives.py",
    "1b_nsaf_stage1_6_maps_figures.py",
]


def main():
    OUTPUTS.mkdir(
        parents=True,
        exist_ok=True,
    )

    missing = [
        name
        for name in RUN_ORDER
        if not (SCRIPTS / name).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required script(s):\n"
            + "\n".join(
                str(SCRIPTS / name)
                for name in missing
            )
        )

    started = datetime.now()

    with LOG.open(
        "w",
        encoding="utf-8",
    ) as log:

        def emit(message=""):
            print(message)
            log.write(message + "\n")
            log.flush()

        emit("=" * 88)
        emit("NSAF MAIZE SEQUENTIAL RERUN")
        emit(f"Project root: {ROOT}")
        emit(f"Started:      {started}")
        emit("=" * 88)

        for i, name in enumerate(
            RUN_ORDER,
            start=1,
        ):
            emit()
            emit("=" * 88)
            emit(
                f"STEP {i}/{len(RUN_ORDER)}: "
                f"{name}"
            )
            emit("=" * 88)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / name),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            output = result.stdout or ""

            print(
                output,
                end="",
            )
            log.write(output)
            log.flush()

            if result.returncode != 0:
                emit(
                    f"\nFAILED: {name}"
                )
                emit(
                    f"Return code: "
                    f"{result.returncode}"
                )
                emit(
                    f"Log: {LOG}"
                )
                sys.exit(
                    result.returncode
                )

            emit(
                f"COMPLETED: {name}"
            )

        finished = datetime.now()

        emit()
        emit("=" * 88)
        emit("ALL NSAF STEPS COMPLETED")
        emit(f"Finished: {finished}")
        emit(
            f"Elapsed:  "
            f"{finished - started}"
        )
        emit(f"Log:      {LOG}")
        emit("=" * 88)


if __name__ == "__main__":
    main()
