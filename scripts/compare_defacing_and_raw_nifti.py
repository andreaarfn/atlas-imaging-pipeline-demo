from pathlib import Path
import nibabel as nib
import matplotlib.pyplot as plt


def nifti_base_name(path: Path) -> str:
    """Return filename without .nii or .nii.gz."""
    if path.name.endswith(".nii.gz"):
        return path.name[:-7]
    if path.name.endswith(".nii"):
        return path.name[:-4]
    return path.stem


script_dir = Path(__file__).resolve().parent
imaging_pipeline_dir = script_dir.parent

original_dir = imaging_pipeline_dir / "nifti_output"
defaced_dir = imaging_pipeline_dir / "nifti_defaced_pydeface_output"

print("Looking for original files in:", original_dir)
print("Looking for defaced files in:", defaced_dir)

if not original_dir.exists():
    print("ERROR: Original NIfTI folder does not exist.")
    raise SystemExit

if not defaced_dir.exists():
    print("ERROR: Defaced NIfTI folder does not exist.")
    raise SystemExit

original_files = sorted(
    list(original_dir.rglob("*.nii")) +
    list(original_dir.rglob("*.nii.gz"))
)

print(f"Found {len(original_files)} original NIfTI file(s).")

if not original_files:
    print("No original NIfTI files found.")
    raise SystemExit


current_folder = None

for original_file in original_files:
    relative_path = original_file.relative_to(original_dir)
    relative_folder = relative_path.parent
    base = nifti_base_name(original_file)

    if relative_folder != current_folder:
        current_folder = relative_folder
        print("\n====================")
        print("Subfolder:", current_folder)
        print("====================")

    defaced_subdir = defaced_dir / relative_folder

    possible_defaced_files = [
        defaced_subdir / f"{base}_defaced.nii.gz",
        defaced_subdir / f"{base}_pydeface.nii.gz",
        defaced_subdir / f"{base}.nii.gz",
        defaced_subdir / f"{base}.nii",
    ]

    defaced_file = None
    for candidate in possible_defaced_files:
        if candidate.exists():
            defaced_file = candidate
            break

    print("\n--------------------")
    print("Original:", relative_path)

    if defaced_file is None:
        print("No matching defaced file found in:", defaced_subdir)
        print("Expected one of:")
        for candidate in possible_defaced_files:
            print(" ", candidate.relative_to(defaced_dir))
        continue

    print("Defaced:", defaced_file.relative_to(defaced_dir))

    original_img = nib.load(str(original_file))
    defaced_img = nib.load(str(defaced_file))

    original_data = original_img.get_fdata()
    defaced_data = defaced_img.get_fdata()

    if original_data.ndim < 3 or defaced_data.ndim < 3:
        print("Skipping display: one of the images is not 3D.")
        continue

    original_middle = original_data.shape[2] // 2
    defaced_middle = defaced_data.shape[2] // 2

    plt.figure(figsize=(10, 5))

    plt.subplot(1, 2, 1)
    plt.imshow(original_data[:, :, original_middle].T, cmap="gray", origin="lower")
    plt.title(f"Original\n{relative_path}")
    plt.axis("off")

    plt.subplot(1, 2, 2)
    plt.imshow(defaced_data[:, :, defaced_middle].T, cmap="gray", origin="lower")
    plt.title(f"Defaced\n{defaced_file.relative_to(defaced_dir)}")
    plt.axis("off")

    plt.tight_layout()
    plt.show()