import nibabel as nib
import matplotlib.pyplot as plt

img = nib.load(
    "nifti_mni_output/sag_mni_rigid.nii.gz"
)

data = img.get_fdata()

middle = data.shape[2] // 2

plt.imshow(
    data[:, :, middle].T,
    cmap="gray",
    origin="lower"
)

plt.title("MNI Rigid Registration")
plt.axis("off")
plt.show()
