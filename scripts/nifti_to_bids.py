"""
- Extracts image geometry metadata from NIfTI headers and writes BIDS-style JSON sidecars.
- Preserves FSL registration matrices (.mat) in a subject xfm/ folder.
- Organizes existing files into a BIDS-compatible structure without modifying image data.
- Recursively reads nifti_mni_output/ and supports patient/session-style subfolders.

Limitations:
- NIfTI headers do not contain all original DICOM metadata. Information such as scanner
  details, acquisition parameters, and sequence descriptions may be unavailable unless
  preserved in a dcm2niix-generated JSON sidecar.
- Modality labels (T1w, T2w, FLAIR, etc.) and MNI template information cannot always be
  determined from the NIfTI file alone and may require pipeline configuration.
- Registered MNI-space images are organized using derivative-style naming; strict BIDS
  datasets typically store native-space images in the raw dataset and processed outputs
  under derivatives/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Set

import nibabel as nib
import numpy as np


def json_safe(value: Any) -> Any:
    """Convert numpy/nibabel values into JSON-serializable Python objects."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace").strip("\x00")
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return value


def clean_bids_label(value: str, fallback: str = "unk") -> str:
    """
    BIDS labels should be alphanumeric.
    This also strips a leading 'sub-' if present.
    """
    value = value.strip()

    if value.lower().startswith("sub-"):
        value = value[4:]

    cleaned = re.sub(r"[^A-Za-z0-9]", "", value)

    return cleaned or fallback


def nifti_base_name(path: Path) -> str:
    """Return filename without .nii or .nii.gz."""
    if path.name.endswith(".nii.gz"):
        return path.name[:-7]
    if path.name.endswith(".nii"):
        return path.name[:-4]
    return path.stem


def nifti_extension(path: Path) -> str:
    """Return .nii.gz or .nii."""
    if path.name.endswith(".nii.gz"):
        return ".nii.gz"
    if path.name.endswith(".nii"):
        return ".nii"
    return path.suffix


def infer_subject_label(nifti_path: Path, input_dir: Path, forced_subject: Optional[str], root_subject: str) -> str:
    """
    Infer subject from the first subfolder under input_dir.

    Example:
      nifti_mni_output/patient001/scanA/image.nii.gz -> sub-patient001

    If the file is directly inside nifti_mni_output, use root_subject.
    If --subject is provided, use that for every file.
    """
    if forced_subject:
        return clean_bids_label(forced_subject, fallback=root_subject)

    relative_path = nifti_path.relative_to(input_dir)

    if len(relative_path.parts) > 1:
        first_folder = relative_path.parts[0]
        return clean_bids_label(first_folder, fallback=root_subject)

    return clean_bids_label(root_subject, fallback="001")


def infer_acquisition_label(path: Path) -> str:
    """
    Infer an acquisition label from the filename.

    With protocol_series naming, this turns something like:
      t1_tse_dark-fluid_sag_1044_mni_rigid.nii.gz

    into:
      acq-t1tsedarkfluidsag1044

    This avoids collisions better than only using 'sag' or 't1'.
    """
    base = nifti_base_name(path).lower()

    for suffix in [
        "_mni_rigid",
        "_defaced",
        "_pydeface",
        "_mni",
    ]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]

    acquisition = clean_bids_label(base, fallback="unk")

    return acquisition


def copy_nifti(src: Path, dst: Path) -> None:
    """Copy NIfTI file without modifying image data."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def read_nifti_metadata(nifti_path: Path, input_dir: Path) -> Dict[str, Any]:
    """Extract useful metadata from a NIfTI image header and affine."""
    img = nib.load(str(nifti_path))
    hdr = img.header

    zooms = hdr.get_zooms()
    qform, qform_code = img.get_qform(coded=True)
    sform, sform_code = img.get_sform(coded=True)

    meta: Dict[str, Any] = {
        "GeneratedBy": [
            {
                "Name": "ATLAS prototype nifti_to_bids.py",
                "Description": "Copied defaced, MNI-registered NIfTI images into a BIDS-compatible structure and extracted NIfTI geometry metadata.",
                "GeneratedAt": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "SourceFile": str(nifti_path.relative_to(input_dir)),
        "ImageType": "DERIVED\\SECONDARY",
        "Modality": "MR",
        "SkullStripped": False,
        "Defaced": True,
        "SpatialReference": "MNI152_T1_2mm",
        "RegistrationSoftware": "FSL FLIRT",
        "RegistrationDegreesOfFreedom": 6,
        "RegistrationDescription": "Rigid-body registration to MNI152_T1_2mm template after defacing.",
        "NIfTIShape": list(img.shape),
        "VoxelSize": list(zooms[: len(img.shape)]),
        "Affine": img.affine.tolist(),
        "QFormCode": int(qform_code),
        "SFormCode": int(sform_code),
        "QFormAffine": None if qform is None else qform.tolist(),
        "SFormAffine": None if sform is None else sform.tolist(),
        "Datatype": str(hdr.get_data_dtype()),
        "Bitpix": int(hdr["bitpix"]),
        "IntentCode": int(hdr["intent_code"]),
        "CalMin": float(hdr["cal_min"]),
        "CalMax": float(hdr["cal_max"]),
        "Descrip": json_safe(hdr["descrip"]),
    }

    if len(zooms) >= 4:
        meta["RepetitionTime"] = float(zooms[3])

    return json_safe(meta)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
        f.write("\n")


def write_dataset_description(bids_root: Path, dataset_name: str) -> None:
    payload = {
        "Name": dataset_name,
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "GeneratedBy": [
            {
                "Name": "ATLAS imaging pipeline prototype",
                "Description": "DICOM to NIfTI, defacing, rigid FLIRT registration to MNI space, and BIDS organization.",
            }
        ],
    }
    write_json(bids_root / "dataset_description.json", payload)


def write_participants_tsv(bids_root: Path, subjects: Set[str]) -> None:
    path = bids_root / "participants.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        f.write("participant_id\n")
        for subject in sorted(subjects):
            f.write(f"sub-{subject}\n")


def find_nifti_files(input_dir: Path) -> Iterable[Path]:
    """Find NIfTI files recursively."""
    return sorted(
        list(input_dir.rglob("*.nii.gz")) +
        list(input_dir.rglob("*.nii"))
    )


def bids_stem(subject: str, acquisition: str, suffix: str, space: str, desc: str) -> str:
    return f"sub-{subject}_acq-{acquisition}_space-{space}_desc-{desc}_{suffix}"


def matching_mat_path(nifti_path: Path) -> Path:
    """Find the matching FLIRT .mat file next to a .nii or .nii.gz file."""
    base = nifti_base_name(nifti_path)
    return nifti_path.parent / f"{base}.mat"


def convert_one(
    nifti_path: Path,
    input_dir: Path,
    bids_root: Path,
    subject: str,
    suffix: str,
    space: str,
    desc: str,
    template: str,
) -> Tuple[Path, Path, Optional[Path]]:
    acquisition = infer_acquisition_label(nifti_path)

    anat_dir = bids_root / f"sub-{subject}" / "anat"
    xfm_dir = bids_root / f"sub-{subject}" / "xfm"

    stem = bids_stem(subject, acquisition, suffix, space, desc)

    out_nii = anat_dir / f"{stem}{nifti_extension(nifti_path)}"
    out_json = anat_dir / f"{stem}.json"

    copy_nifti(nifti_path, out_nii)

    meta = read_nifti_metadata(nifti_path, input_dir)
    meta["SpatialReference"] = template
    meta["BIDSIntendedFor"] = str(out_nii.relative_to(bids_root))

    write_json(out_json, meta)

    mat_path = matching_mat_path(nifti_path)

    out_mat = None
    if mat_path.exists():
        out_mat = xfm_dir / f"sub-{subject}_acq-{acquisition}_from-{suffix}_to-{space}_mode-image_xfm.mat"
        out_mat.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mat_path, out_mat)

    return out_nii, out_json, out_mat


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    imaging_pipeline_dir = script_dir.parent

    default_input_dir = imaging_pipeline_dir / "nifti_mni_output"
    default_output_dir = imaging_pipeline_dir / "bids_output"

    parser = argparse.ArgumentParser(
        description="Organize defaced, MNI-registered NIfTI files into a BIDS-compatible structure and write JSON sidecars."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help="Folder containing MNI-space NIfTI files and optional FLIRT .mat files."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help="Output BIDS root folder."
    )

    parser.add_argument(
        "--subject",
        default=None,
        help=(
            "Optional forced BIDS subject label without 'sub-'. "
            "If omitted, the first subfolder under input-dir is used as the subject."
        )
    )

    parser.add_argument(
        "--root-subject",
        default="001",
        help="Subject label to use for files directly inside input-dir with no patient subfolder."
    )

    parser.add_argument(
        "--suffix",
        default="T1w",
        help="BIDS imaging suffix. Common values: T1w, T2w, FLAIR, CT."
    )

    parser.add_argument(
        "--space",
        default="MNI152",
        help="BIDS space label used in filenames."
    )

    parser.add_argument(
        "--template",
        default="MNI152_T1_2mm",
        help="Template/reference recorded in JSON metadata."
    )

    parser.add_argument(
        "--desc",
        default="defaced",
        help="BIDS desc label used in filenames."
    )

    parser.add_argument(
        "--dataset-name",
        default="ATLAS Imaging Prototype",
        help="Name written to dataset_description.json."
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    bids_root = args.output_dir

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    nifti_files = list(find_nifti_files(input_dir))

    if not nifti_files:
        raise FileNotFoundError(f"No .nii or .nii.gz files found in: {input_dir}")

    print("Input folder:", input_dir)
    print("BIDS output folder:", bids_root)
    print(f"Found {len(nifti_files)} NIfTI file(s).")

    subjects: Set[str] = set()

    write_dataset_description(bids_root, args.dataset_name)

    current_folder = None

    for nifti_path in nifti_files:
        relative_path = nifti_path.relative_to(input_dir)
        relative_folder = relative_path.parent

        if relative_folder != current_folder:
            current_folder = relative_folder
            print("\n====================")
            print("Subfolder:", current_folder)
            print("====================")

        subject = infer_subject_label(
            nifti_path=nifti_path,
            input_dir=input_dir,
            forced_subject=args.subject,
            root_subject=args.root_subject,
        )

        subjects.add(subject)

        out_nii, out_json, out_mat = convert_one(
            nifti_path=nifti_path,
            input_dir=input_dir,
            bids_root=bids_root,
            subject=subject,
            suffix=args.suffix,
            space=args.space,
            desc=args.desc,
            template=args.template,
        )

        print("\n--------------------")
        print(f"Input:         {relative_path}")
        print(f"Subject:       sub-{subject}")
        print(f"Wrote image:   {out_nii.relative_to(bids_root)}")
        print(f"Wrote sidecar: {out_json.relative_to(bids_root)}")

        if out_mat:
            print(f"Copied xfm:    {out_mat.relative_to(bids_root)}")
        else:
            print(f"No matching .mat found for {relative_path}")

    write_participants_tsv(bids_root, subjects)

    print("\nDone. Suggested validation:")
    print(f"  bids-validator {bids_root}")
    print("\nNote: files with space-/desc- entities are often treated as derivative-style BIDS names.")
    print("For a strict raw BIDS dataset, store native-space defaced images as sub-*/anat/sub-*_T1w.nii.gz")
    print("and place MNI-registered outputs under derivatives/.")


if __name__ == "__main__":
    main()