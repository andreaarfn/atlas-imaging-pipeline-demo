from pathlib import Path
import nibabel as nib

out_dir = Path("nifti_output")

for f in sorted(out_dir.glob("*.nii.gz")):
    img = nib.load(str(f))
    print("\n--------------------")
    print(f.name)
    print("Shape:", img.shape)
    print("Voxel size:", img.header.get_zooms())
    print("Affine:")
    print(img.affine)