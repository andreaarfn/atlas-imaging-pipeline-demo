from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys


def nifti_base_name(path: Path) -> str:
    """Return filename without .nii or .nii.gz."""
    if path.name.endswith(".nii.gz"):
        return path.name[:-7]
    if path.name.endswith(".nii"):
        return path.name[:-4]
    return path.stem


def matching_json_path(nifti_path: Path) -> Path:
    """Find matching JSON sidecar for a .nii or .nii.gz file."""
    base = nifti_base_name(nifti_path)
    return nifti_path.parent / f"{base}.json"


def find_nifti_files(input_dir: Path):
    """Find .nii and .nii.gz files recursively."""
    files = []
    files.extend(input_dir.rglob("*.nii"))
    files.extend(input_dir.rglob("*.nii.gz"))
    return sorted(files)


def copy_and_update_json(input_json: Path, output_json: Path, source_nifti: Path, input_dir: Path):
    """Copy JSON sidecar and add defacing information."""
    if not input_json.exists():
        return

    output_json.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(input_json, "r") as f:
            metadata = json.load(f)
    except Exception:
        shutil.copy2(input_json, output_json)
        return

    metadata["DefacingSoftware"] = "pydeface"
    metadata["SourceFile"] = str(source_nifti.relative_to(input_dir))

    with open(output_json, "w") as f:
        json.dump(metadata, f, indent=2)


def main():
    script_dir = Path(__file__).resolve().parent
    imaging_pipeline_dir = script_dir.parent

    default_input_dir = imaging_pipeline_dir / "nifti_output"
    default_output_dir = imaging_pipeline_dir / "nifti_defaced_pydeface_output"

    parser = argparse.ArgumentParser(
        description="Deface NIfTI files using pydeface while preserving subfolder structure."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help="Folder containing input NIfTI files."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Folder where defaced NIfTI files will be saved."
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing defaced files."
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    print("Input folder:", input_dir)
    print("Output folder:", output_dir)

    if not input_dir.exists():
        print(f"ERROR: Input folder does not exist: {input_dir}")
        sys.exit(1)

    pydeface_path = shutil.which("pydeface")
    if pydeface_path is None:
        print("ERROR: pydeface was not found.")
        print("Try running:")
        print("  source .venv/bin/activate")
        print("  python -m pip install pydeface")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    nifti_files = find_nifti_files(input_dir)

    print(f"Found {len(nifti_files)} NIfTI file(s).")

    if not nifti_files:
        print("No .nii or .nii.gz files found.")
        sys.exit(0)

    current_folder = None

    for nifti_path in nifti_files:
        relative_path = nifti_path.relative_to(input_dir)
        relative_folder = relative_path.parent

        if relative_folder != current_folder:
            current_folder = relative_folder
            print("\n====================")
            print("Subfolder:", current_folder)
            print("====================")

        base = nifti_base_name(nifti_path)

        output_subdir = output_dir / relative_folder
        output_subdir.mkdir(parents=True, exist_ok=True)

        output_nifti = output_subdir / f"{base}_defaced.nii.gz"
        input_json = matching_json_path(nifti_path)
        output_json = output_subdir / f"{base}_defaced.json"

        print("\n--------------------")
        print("Input:", relative_path)
        print("Output:", output_nifti.relative_to(output_dir))

        if output_nifti.exists() and not args.overwrite:
            print("Skipping: output already exists. Use --overwrite to replace it.")
            continue

        if output_nifti.exists() and args.overwrite:
            output_nifti.unlink()

        if output_json.exists() and args.overwrite:
            output_json.unlink()

        cmd = [
            "pydeface",
            str(nifti_path),
            "--outfile",
            str(output_nifti),
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: pydeface failed for {relative_path}")
            print(e)
            continue

        copy_and_update_json(input_json, output_json, nifti_path, input_dir)

        print("Done.")

    print("\nDefacing complete.")


if __name__ == "__main__":
    main()