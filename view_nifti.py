import nibabel as nib
import matplotlib.pyplot as plt

file = "nifti_output/_t1_tse_dark-fluid_sag_20240808172452_1044.nii.gz"

img = nib.load(file)
data = img.get_fdata()

print("Shape:", data.shape)

middle_slice = data.shape[2] // 2

plt.imshow(data[:, :, middle_slice].T, cmap="gray", origin="lower")
plt.title("Middle slice")
plt.axis("off")
plt.show()