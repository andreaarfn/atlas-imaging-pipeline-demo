import nibabel as nib
import matplotlib.pyplot as plt

files = [
    ("Original", "nifti_output/_t1_tse_dark-fluid_tra_p4_20240808172452_1032.nii.gz"),
    ("Defaced", "nifti_defaced_output/tra_defaced.nii.gz"),
]

for title, file in files:
    img = nib.load(file)
    data = img.get_fdata()
    middle = data.shape[2] // 2

    plt.figure()
    plt.imshow(data[:, :, middle].T, cmap="gray", origin="lower")
    plt.title(title)
    plt.axis("off")

plt.show()
