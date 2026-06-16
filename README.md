# MRI DICOM → NIfTI → Defacing Workflow  → MNI Coordinates →  BIDS Format

Examples

<img width="1460" height="544" alt="image" src="https://github.com/user-attachments/assets/c98d63d0-e460-4c8c-a757-2de847130a2f" />

<img width="1598" height="544" alt="image" src="https://github.com/user-attachments/assets/39c9e3ac-bda1-4c75-a948-f746724b710a" />

## Setup

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python packages:

```bash
python -m pip install pydicom nibabel matplotlib numpy pillow pydeface
```

Install command-line tools:

```bash
brew install dcm2niix
```

Install FSL once, which is required for PyDeface and MNI registration:

```bash
curl -Ls https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/getfsl.sh | sh -s
```

## Step 1: Inspect DICOM Files

Inspect DICOM metadata and preview images from `dicom_files/`. This script is subfolder-aware.

```bash
python scripts/inspect_dicom.py
```

## Step 2: Convert DICOM to NIfTI

Convert DICOM files from `dicom_files/` into NIfTI format. Patient or scan subfolders are preserved in `nifti_output/`.

```bash
python scripts/convert_dicom_to_nifti.py
```

## Step 3: Inspect NIfTI Files

Inspect NIfTI geometry, voxel size, affine, and data type.

```bash
python scripts/inspect_nifti.py
```

## Step 4: Deface NIfTI Files

Deface the NIfTI files using PyDeface.

```bash
python scripts/deface_nifti_pydeface.py
```

The defaced files will be written to `nifti_defaced_pydeface_output/`.

## Step 5: Compare Original and Defaced Images

Visually compare the original and defaced NIfTI files.

```bash
python scripts/compare_defacing_and_raw_nifti.py
```

## Step 6: Rigid Transform to MNI Space

Rigidly register the defaced NIfTI files to MNI space using FSL FLIRT.

```bash
python scripts/rigid_transform_mni.py
```

The MNI-registered files and transform matrices will be written to `nifti_mni_output/`.

## Step 7: Inspect MNI Transform

Preview the MNI-registered outputs.

```bash
python scripts/inspect_mni_transform.py
```

MNI Template Selection Guidelines

1. Match the imaging modality
   - T1 MRI → T1 template
   - T2 MRI → T2 template
   - CT → CT template

2. Match the study population when possible
   - Adult subjects → Adult template (e.g., MNI152)
   - Pediatric subjects → Pediatric template
   - Special populations may require specialized templates

3. Use the least transformed template that supports the study goals
   - Rigid registration (DOF=6) preferred for preserving original geometry
   - Avoid scaling or nonlinear warping unless scientifically justified

4. Prioritize consistency across sites
   - All centers should register to the same template
   - Record template name and version in metadata

5. Match resolution when practical
   - Higher-resolution images → 1 mm templates
   - Lower-resolution images → 2 mm templates
   - Registration does not create new information

Read more here: https://fsl.fmrib.ox.ac.uk/fsl/docs/other/datasets.html


## Step 8: Convert NIfTI Outputs to BIDS

Organize the MNI-registered NIfTI files into a BIDS-compatible structure.

```bash
python scripts/nifti_to_bids.py
```

This creates a `bids_output/` folder.


