# I still have issues trying to get this to run. Will come back to it Monday.

#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="T1TSEFlairDicomImages/nifti_output"
OUTPUT_DIR="nifti_defaced_afni_output"

mkdir -p "$OUTPUT_DIR"

echo "Looking for NIfTI files in: $INPUT_DIR"
find "$INPUT_DIR" -type f \( -name "*.nii" -o -name "*.nii.gz" \)

while IFS= read -r nii; do
    base=$(basename "$nii")
    base=${base%.nii.gz}
    base=${base%.nii}

    echo "Defacing: $nii"

    @afni_refacer_run \
        -input "$nii" \
        -mode_deface \
        -prefix "$OUTPUT_DIR/${base}_defaced.nii.gz"

    echo "Saved: $OUTPUT_DIR/${base}_defaced.nii.gz"

done < <(find "$INPUT_DIR" -type f \( -name "*.nii" -o -name "*.nii.gz" \))