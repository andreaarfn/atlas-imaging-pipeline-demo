from pathlib import Path
import nibabel as nib


script_dir = Path(__file__).resolve().parent
imaging_pipeline_dir = script_dir.parent
out_dir = imaging_pipeline_dir / "nifti_output"

print("Looking for NIfTI files in:", out_dir)

if not out_dir.exists():
    print("ERROR: nifti_output folder does not exist.")
    raise SystemExit

nifti_files = sorted(
    list(out_dir.rglob("*.nii")) +
    list(out_dir.rglob("*.nii.gz"))
)

print(f"Found {len(nifti_files)} NIfTI file(s).")

if not nifti_files:
    print("No .nii or .nii.gz files found.")
    raise SystemExit


current_folder = None

for f in nifti_files:
    relative_path = f.relative_to(out_dir)
    relative_folder = relative_path.parent

    if relative_folder != current_folder:
        current_folder = relative_folder
        print("\n====================")
        print("Subfolder:", current_folder)
        print("====================")

    try:
        img = nib.load(str(f))
    except Exception as e:
        print(f"\nSkipping file: {relative_path}")
        print(f"Could not read as NIfTI: {e}")
        continue

    print("\n--------------------")
    print("File:", relative_path)
    print("Shape:", img.shape)
    print("Voxel size:", img.header.get_zooms())
    print("Data type:", img.get_data_dtype())
    print("Affine:")
    print(img.affine)