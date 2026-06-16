from pathlib import Path
import nibabel as nib
import matplotlib.pyplot as plt


script_dir = Path(__file__).resolve().parent
imaging_pipeline_dir = script_dir.parent
mni_dir = imaging_pipeline_dir / "nifti_mni_output"

print("Looking for MNI-transformed NIfTI files in:", mni_dir)

if not mni_dir.exists():
    print("ERROR: nifti_mni_output folder does not exist.")
    raise SystemExit

mni_files = sorted(
    list(mni_dir.rglob("*.nii")) +
    list(mni_dir.rglob("*.nii.gz"))
)

print(f"Found {len(mni_files)} MNI-transformed NIfTI file(s).")

if not mni_files:
    print("No .nii or .nii.gz files found.")
    raise SystemExit


current_folder = None

for mni_file in mni_files:
    relative_path = mni_file.relative_to(mni_dir)
    relative_folder = relative_path.parent

    if relative_folder != current_folder:
        current_folder = relative_folder
        print("\n====================")
        print("Subfolder:", current_folder)
        print("====================")

    print("\n--------------------")
    print("File:", relative_path)

    try:
        img = nib.load(str(mni_file))
    except Exception as e:
        print(f"Could not read as NIfTI: {e}")
        continue

    data = img.get_fdata()

    if data.ndim < 3:
        print("Skipping display: image is not 3D.")
        continue

    middle = data.shape[2] // 2

    print("Shape:", img.shape)
    print("Voxel size:", img.header.get_zooms())
    print("Affine:")
    print(img.affine)

    plt.figure()
    plt.imshow(
        data[:, :, middle].T,
        cmap="gray",
        origin="lower"
    )
    plt.title(f"MNI Rigid Registration\n{relative_path}")
    plt.axis("off")
    plt.show()