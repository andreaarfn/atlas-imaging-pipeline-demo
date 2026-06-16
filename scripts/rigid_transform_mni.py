from pathlib import Path
import argparse
import os
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


def find_nifti_files(input_dir: Path):
    """Find .nii and .nii.gz files recursively."""
    files = []
    files.extend(input_dir.rglob("*.nii"))
    files.extend(input_dir.rglob("*.nii.gz"))
    return sorted(files)


def main():
    script_dir = Path(__file__).resolve().parent
    imaging_pipeline_dir = script_dir.parent

    default_input_dir = imaging_pipeline_dir / "nifti_defaced_pydeface_output"
    default_output_dir = imaging_pipeline_dir / "nifti_mni_output"

    fsldir = os.environ.get("FSLDIR")
    if fsldir:
        default_ref = Path(fsldir) / "data" / "standard" / "MNI152_T1_2mm.nii.gz"
    else:
        default_ref = None

    parser = argparse.ArgumentParser(
        description="Rigidly transform defaced NIfTI files to MNI space using FSL FLIRT."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help="Folder containing defaced NIfTI files."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Folder where MNI-registered outputs will be saved."
    )

    parser.add_argument(
        "--ref",
        type=Path,
        default=default_ref,
        help="Reference MNI image. Defaults to $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing MNI output files."
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    ref_file = args.ref

    print("Input folder:", input_dir)
    print("Output folder:", output_dir)
    print("Reference image:", ref_file)

    if shutil.which("flirt") is None:
        print("ERROR: FSL flirt was not found.")
        print("Make sure FSL is installed and available in your terminal.")
        sys.exit(1)

    if not input_dir.exists():
        print(f"ERROR: Input folder does not exist: {input_dir}")
        sys.exit(1)

    if ref_file is None or not ref_file.exists():
        print("ERROR: MNI reference image not found.")
        print("Expected something like:")
        print("  $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    nifti_files = find_nifti_files(input_dir)

    print(f"Found {len(nifti_files)} defaced NIfTI file(s).")

    if not nifti_files:
        print("No .nii or .nii.gz files found.")
        sys.exit(0)

    current_folder = None

    for input_file in nifti_files:
        relative_path = input_file.relative_to(input_dir)
        relative_folder = relative_path.parent

        if relative_folder != current_folder:
            current_folder = relative_folder
            print("\n====================")
            print("Subfolder:", current_folder)
            print("====================")

        base = nifti_base_name(input_file)

        if base.endswith("_defaced"):
            output_base = base.replace("_defaced", "_mni_rigid")
        elif base.endswith("_pydeface"):
            output_base = base.replace("_pydeface", "_mni_rigid")
        else:
            output_base = f"{base}_mni_rigid"

        output_subdir = output_dir / relative_folder
        output_subdir.mkdir(parents=True, exist_ok=True)

        output_nifti = output_subdir / f"{output_base}.nii.gz"
        output_mat = output_subdir / f"{output_base}.mat"

        print("\n--------------------")
        print("Input:", relative_path)
        print("Output NIfTI:", output_nifti.relative_to(output_dir))
        print("Output matrix:", output_mat.relative_to(output_dir))

        if output_nifti.exists() and not args.overwrite:
            print("Skipping: output already exists. Use --overwrite to replace it.")
            continue

        if output_nifti.exists() and args.overwrite:
            output_nifti.unlink()

        if output_mat.exists() and args.overwrite:
            output_mat.unlink()

        cmd = [
            "flirt",
            "-in", str(input_file),
            "-ref", str(ref_file),
            "-out", str(output_nifti),
            "-omat", str(output_mat),
            "-dof", "6",
        ]

        try:
            subprocess.run(cmd, check=True)
            print("Done.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: FLIRT failed for {relative_path}")
            print(e)

    print("\nRigid MNI transformation complete.")


if __name__ == "__main__":
    main()