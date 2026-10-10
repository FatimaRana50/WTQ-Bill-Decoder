"""Build the submission ZIP (output/, source/, optional demo/), leaving out secrets and junk.
Usage: python dev/package_submission.py <output_dir> <zip_path> [demo_file]"""
import sys
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", ".cache", "__pycache__", ".pytest_cache", "dev_out", ".git"}
SKIP_FILES = {".env"}
LIMIT = 15 * 1024 * 1024


def main(out_dir: Path, zip_path: Path, demo: Path | None) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("level1.csv", "level2.csv"):
            zf.write(out_dir / name, f"output/{name}")
        for path in sorted(SOURCE.rglob("*")):
            rel = path.relative_to(SOURCE)
            if path.is_dir() or SKIP_DIRS & set(rel.parts) or path.name in SKIP_FILES or path.suffix == ".pyc":
                continue
            zf.write(path, f"source/{rel.as_posix()}")
        if demo:
            zf.write(demo, f"demo/{demo.name}")
    size = zip_path.stat().st_size
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    print("\n".join(names))
    assert not any(n.endswith("/.env") for n in names), "real .env leaked into the ZIP"
    print(f"\n{zip_path} = {size / 1e6:.2f} MB ({'OK' if size <= LIMIT else 'TOO BIG'})")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
