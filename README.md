# MRI DICOM → NIfTI → Defacing Workflow  → MNI Coordinates

## Inspect DICOM Metadata

```bash
python3 inspect_dicom.py
```

---

## Convert DICOM to NIfTI

```bash
brew install dcm2niix

mkdir -p nifti_output

dcm2niix -z y -b y -o nifti_output .
```

#### `-z y`

Compress output files. Without compression you get `image.nii` which is a very large file instead of `image.nii.gz`

#### `-b y`

Generate a metadata sidecar JSON file (`image.json`)

## NIfTI Metadata
Inspect NIfTI dimensions, voxel sizes, and affine matrices:

```bash
python3 -m pip install nibabel
python3 inspect_nifti.py
```

Outputs shape, voxel size, and affine matrix, useful for understanding image geometry and coordinate systems.

## Visualize NIfTI Images

View the middle slice of the NIfTI volume:

```bash
python3 view_nifti.py
```

In the bottom right corner you will see:
```text
(x,y) = pixel position
[231] = brightness/intensity at that pixel
```

---

## Defacing

```bash
python3 -m pip install pydeface
curl -Ls https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/getfsl.sh | sh -s
```

Deface NIfTI Image

```bash
mkdir -p nifti_defaced_output
pydeface \
  nifti_input_folder/original_nifti_file_name.nii.gz \
  --outfile nifti_defaced_output_folder/defaced_nifti_file_name.nii.gz
```

Compare defaced versus original image

```bash
python3 compare_defacing.py
```

---

## Rigid Transform to MNI Space

mkdir -p nifti_mni_output

```bash
flirt \
  -in nifti_defaced_output/sag_defaced.nii.gz \
  -ref $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz \
  -out nifti_mni_output/sag_mni_rigid.nii.gz \
  -omat nifti_mni_output/sag_mni_rigid.mat \
  -dof 6
python3 view_mni.py
``` 

Template Selection Guidelines

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

