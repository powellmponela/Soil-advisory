from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(r"D:\dss\SOIL ADVISORY")
SCRIPTS = ROOT / "scripts"
FRONTEND = ROOT / "frontend"

PIPELINE = [
    SCRIPTS / "5b_predict_western_n_demand_savings.py",
    SCRIPTS / "6a_map_western_ae_and_gains.py",
    SCRIPTS / "7_publish_web_gis.py",
]

REQUIRED_OUTPUTS = [
    ROOT / "outputs" / "spatial_extrapolation" / "western_n_demand_savings_pixels.csv",
    ROOT / "outputs" / "spatial_extrapolation" / "western_ae_gains_map_table.csv",
    FRONTEND / "public" / "advisory_pixels.csv",
    FRONTEND / "public" / "advisory_pixels.geojson",
    FRONTEND / "public" / "advisory_metadata.json",
]


def run(cmd, cwd=ROOT):
    print("\n>", " ".join(str(x) for x in cmd))

    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"\nCommand failed with exit code {result.returncode}"
        )


def validate_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing output:\n{path}")

    size = path.stat().st_size

    if size <= 0:
        raise ValueError(f"Output is empty:\n{path}")

    print(
        f"OK  {path.relative_to(ROOT)} "
        f"({size:,} bytes)"
    )


def main():

    print("=" * 72)
    print("SOIL ADVISORY: MODEL -> GIS -> GITHUB -> VERCEL")
    print("=" * 72)

    print("\n[1/7] Sync GitHub")

    run([
        "git",
        "pull",
        "--rebase",
        "origin",
        "main",
    ])

    print("\n[2/7] Run pixel modelling workflow")

    for script in PIPELINE:

        if not script.exists():
            raise FileNotFoundError(
                f"Missing workflow script:\n{script}"
            )

        run([
            sys.executable,
            str(script),
        ])

    print("\n[3/7] Validate analytical outputs")

    for path in REQUIRED_OUTPUTS:
        validate_file(path)

    print("\n[4/7] Install frontend dependencies")

    run(
        ["npm", "install"],
        cwd=FRONTEND,
    )

    print("\n[5/7] Build Vercel frontend")

    run(
        ["npm", "run", "build"],
        cwd=FRONTEND,
    )

    dist = FRONTEND / "dist"

    if not dist.exists():
        raise RuntimeError(
            "Frontend build finished but frontend/dist "
            "was not created."
        )

    print("Frontend build OK")

    print("\n[6/7] Publish to GitHub")

    run([
        "git",
        "add",
        "frontend/public/advisory_pixels.csv",
        "frontend/public/advisory_pixels.geojson",
        "frontend/public/advisory_metadata.json",
        "frontend/src",
        "frontend/package.json",
        "frontend/package-lock.json",
        "scripts/7_publish_web_gis.py",
        "scripts/8_publish_and_deploy.py",
        "vercel.json",
    ])

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--quiet",
        ],
        cwd=ROOT,
    )

    if diff.returncode == 0:

        print(
            "No publication changes detected. "
            "GitHub is already current."
        )

    else:

        stamp = time.strftime("%Y-%m-%d %H:%M")

        run([
            "git",
            "commit",
            "-m",
            f"Update pixel advisory {stamp}",
        ])

        run([
            "git",
            "push",
            "origin",
            "main",
        ])

    print("\n[7/7] Final status")

    run([
        "git",
        "status",
        "--short",
    ])

    print("\n" + "=" * 72)
    print("PUBLICATION COMPLETE")
    print("=" * 72)

    print(
        "\nGitHub main has been updated."
        "\nVercel should automatically redeploy:"
        "\nhttps://soiladvisory.vercel.app/"
    )


if __name__ == "__main__":
    main()