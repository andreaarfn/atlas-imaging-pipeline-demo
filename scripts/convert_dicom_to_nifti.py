from pathlib import Path
import argparse
import shutil
import subprocess
import sys


def find_dirs_with_files(input_dir: Path):
    """
    Find all folders inside input_dir that contain files.

    This handles structures like:
      dicom_files/
        patient001/
          scan1/
            IMG-0001.dcm
        patient002/
          IMG-0001.dcm

    It will run dcm2niix separately on each folder that actually contains files.
    """
    dirs = []

    for path in sorted(input_dir.rglob("*")):
        if path.is_dir():
            has_files = any(child.is_file() for child in path.iterdir())
            if has_files:
                dirs.append(path)

    # Also handle the case where dicom_files itself contains DICOMs directly
    if any(child.is_file() for child in input_dir.iterdir()):
        dirs.insert(0, input_dir)

    return dirs


def main():
    script_dir = Path(__file__).resolve().parent
    imaging_pipeline_dir = script_dir.parent

    default_input_dir = imaging_pipeline_dir / "dicom_files"
    default_output_dir = imaging_pipeline_dir / "nifti_output"

    parser = argparse.ArgumentParser(
        description="Convert DICOM folders to NIfTI using dcm2niix."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help="Folder containing DICOM files or patient subfolders."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Folder where NIfTI outputs will be saved."
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing NIfTI files."
    )

    parser.add_argument(
        "--filename-pattern",
        default="%p_%s",
        help=(
            "dcm2niix filename pattern. "
            "Default is '%%p_%%s', which names files as protocol_series. "
            "Example: t1_tse_dark-fluid_sag_1044.nii.gz"
        )
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    print("Input DICOM folder:", input_dir)
    print("Output NIfTI folder:", output_dir)
    print("Filename pattern:", args.filename_pattern)

    if shutil.which("dcm2niix") is None:
        print("ERROR: dcm2niix was not found.")
        print("Install it with:")
        print("  brew install dcm2niix")
        sys.exit(1)

    if not input_dir.exists():
        print(f"ERROR: Input folder does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    dicom_dirs = find_dirs_with_files(input_dir)

    print(f"Found {len(dicom_dirs)} folder(s) containing files.")

    if not dicom_dirs:
        print("No DICOM folders found.")
        sys.exit(0)

    for dicom_dir in dicom_dirs:
        rel_path = dicom_dir.relative_to(input_dir)

        if rel_path == Path("."):
            out_subdir = output_dir
        else:
            out_subdir = output_dir / rel_path

        out_subdir.mkdir(parents=True, exist_ok=True)

        print("\n--------------------")
        print("Converting:", dicom_dir)
        print("Saving to:", out_subdir)

        overwrite_value = "1" if args.overwrite else "0"

        cmd = [
            "dcm2niix",
            "-z", "y",                  # gzip compress: .nii.gz
            "-b", "y",                  # create BIDS-style JSON sidecar
            "-ba", "y",                 # anonymize BIDS sidecar
            "-w", overwrite_value,      # overwrite behavior
            "-f", args.filename_pattern,
            "-o", str(out_subdir),
            str(dicom_dir),
        ]

        try:
            subprocess.run(cmd, check=True)
            print("Done.")
        except subprocess.CalledProcessError:
            print(f"WARNING: dcm2niix failed for folder: {dicom_dir}")
            continue

    print("\nDICOM to NIfTI conversion complete.")


if __name__ == "__main__":
    main()