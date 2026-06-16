from pathlib import Path
import pydicom
import matplotlib.pyplot as plt
import numpy as np


script_dir = Path(__file__).resolve().parent
imaging_pipeline_dir = script_dir.parent
dicom_dir = imaging_pipeline_dir / "dicom_files"

print("Looking for DICOM files in:", dicom_dir)

if not dicom_dir.exists():
    print("ERROR: dicom_files folder does not exist.")
    raise SystemExit

dicom_paths = sorted([p for p in dicom_dir.rglob("*") if p.is_file()])

print(f"Found {len(dicom_paths)} file(s) under dicom_files.")

if not dicom_paths:
    print("No files found.")
    raise SystemExit


current_folder = None

for dcm_path in dicom_paths:
    relative_path = dcm_path.relative_to(dicom_dir)
    relative_folder = relative_path.parent

    if relative_folder != current_folder:
        current_folder = relative_folder
        print("\n====================")
        print("Subfolder:", current_folder)
        print("====================")

    print("\n--------------------")
    print("File:", relative_path)

    try:
        ds = pydicom.dcmread(dcm_path)
    except Exception as e:
        print(f"Skipping file: could not read as DICOM ({e})")
        continue

    print("Modality:", getattr(ds, "Modality", None))
    print("SeriesDescription:", getattr(ds, "SeriesDescription", None))
    print("PatientID:", getattr(ds, "PatientID", None))
    print("StudyDate:", getattr(ds, "StudyDate", None))
    print("Rows:", getattr(ds, "Rows", None))
    print("Columns:", getattr(ds, "Columns", None))
    print("NumberOfFrames:", getattr(ds, "NumberOfFrames", 1))

    try:
        image = ds.pixel_array
    except Exception as e:
        print(f"Could not load image pixels: {e}")
        continue

    # Handle common DICOM shapes:
    # 2D: rows x columns
    # 3D: frames x rows x columns, or rows x columns x RGB
    # 4D: frames x rows x columns x RGB
    if image.ndim == 2:
        image_to_show = image

    elif image.ndim == 3:
        # RGB image: rows x columns x 3
        if image.shape[-1] == 3:
            image_to_show = image
        else:
            # Multi-frame grayscale: frames x rows x columns
            image_to_show = image[image.shape[0] // 2]

    elif image.ndim == 4:
        # Multi-frame RGB: frames x rows x columns x 3
        image_to_show = image[image.shape[0] // 2]

    else:
        print(f"Skipping display: unsupported image shape {image.shape}")
        continue

    plt.figure()
    plt.imshow(image_to_show, cmap="gray" if image_to_show.ndim == 2 else None)
    plt.title(str(relative_path))
    plt.axis("off")
    plt.show()