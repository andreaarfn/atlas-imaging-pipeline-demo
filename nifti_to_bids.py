#!/usr/bin/env python3
"""
- Extracts image geometry metadata (dimensions, voxel sizes, affine transforms, data type)
  from NIfTI headers and writes BIDS-style JSON sidecars.
- Preserves FSL registration matrices (.mat) in a subject xfm/ folder.
- Organizes existing files into a BIDS-compatible structure without modifying image data.

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
import gzip
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

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


def infer_acquisition_label(path: Path) -> str:
    """Infer an acquisition label from filename prefixes of input."""
    name = path.name.lower()
    if name.startswith("sag") or "_sag" in name:
        return "sag"
    if name.startswith("tra") or name.startswith("ax") or "_tra" in name or "_ax" in name:
        return "tra"
    if name.startswith("cor") or "_cor" in name:
        return "cor"
    return path.name.split("_")[0].replace(".", "").replace("-", "") or "unk"


def copy_nii_gz(src: Path, dst: Path) -> None:
    """Copy NIfTI file without modifying image data."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def read_nifti_metadata(nifti_path: Path) -> Dict[str, Any]:
    """Extract useful metadata from a NIfTI image header and affine"""
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
        "SourceFile": str(nifti_path),
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

    # Optional TR for 4D data; for structural scans this often is absent or not meaningful.
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


def write_participants_tsv(bids_root: Path, subject: str) -> None:
    path = bids_root / "participants.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("participant_id\n")
        f.write(f"sub-{subject}\n")


def find_nifti_files(input_dir: Path) -> Iterable[Path]:
    return sorted(input_dir.glob("*.nii.gz")) + sorted(input_dir.glob("*.nii"))


def bids_stem(subject: str, acquisition: str, suffix: str, space: str, desc: str) -> str:
    # For files already in MNI space, this is closer to BIDS Derivatives naming.
    # It is still very useful for prototype organization and downstream handoff.
    return f"sub-{subject}_acq-{acquisition}_space-{space}_desc-{desc}_{suffix}"


def convert_one(
    nifti_path: Path,
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
    out_nii = anat_dir / f"{stem}.nii.gz"
    out_json = anat_dir / f"{stem}.json"

    copy_nii_gz(nifti_path, out_nii)
    meta = read_nifti_metadata(nifti_path)
    meta["SpatialReference"] = template
    meta["BIDSIntendedFor"] = str(out_nii.relative_to(bids_root))
    write_json(out_json, meta)

    mat_path = nifti_path.with_suffix("")
    if mat_path.name.endswith(".nii"):
        mat_path = mat_path.with_suffix("")
    mat_path = nifti_path.parent / nifti_path.name.replace(".nii.gz", ".mat").replace(".nii", ".mat")

    out_mat = None
    if mat_path.exists():
        out_mat = xfm_dir / f"sub-{subject}_acq-{acquisition}_from-{suffix}_to-{space}_mode-image_xfm.mat"
        out_mat.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mat_path, out_mat)

    return out_nii, out_json, out_mat


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize defaced, MNI-registered NIfTI files into a BIDS-compatible structure and write JSON sidecars."
    )
    parser.add_argument("--input-dir", default="nifti_mni_output", help="Folder containing MNI-space NIfTI files and optional FLIRT .mat files.")
    parser.add_argument("--output-dir", default="bids_output", help="Output BIDS root folder.")
    parser.add_argument("--subject", default="001", help="BIDS subject label without 'sub-'. Example: 001 or P043.")
    parser.add_argument("--suffix", default="T1w", help="BIDS imaging suffix. Common values: T1w, T2w, FLAIR, CT.")
    parser.add_argument("--space", default="MNI152", help="BIDS space label used in filenames.")
    parser.add_argument("--template", default="MNI152_T1_2mm", help="Template/reference recorded in JSON metadata.")
    parser.add_argument("--desc", default="defaced", help="BIDS desc label used in filenames.")
    parser.add_argument("--dataset-name", default="ATLAS Imaging Prototype", help="Name written to dataset_description.json.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    bids_root = Path(args.output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    nifti_files = list(find_nifti_files(input_dir))
    if not nifti_files:
        raise FileNotFoundError(f"No .nii or .nii.gz files found in: {input_dir}")

    write_dataset_description(bids_root, args.dataset_name)
    write_participants_tsv(bids_root, args.subject)

    print(f"Found {len(nifti_files)} NIfTI file(s) in {input_dir}")
    for nifti_path in nifti_files:
        out_nii, out_json, out_mat = convert_one(
            nifti_path=nifti_path,
            bids_root=bids_root,
            subject=args.subject,
            suffix=args.suffix,
            space=args.space,
            desc=args.desc,
            template=args.template,
        )
        print(f"Wrote image:    {out_nii}")
        print(f"Wrote sidecar:  {out_json}")
        if out_mat:
            print(f"Copied xfm mat: {out_mat}")
        else:
            print(f"No matching .mat found for {nifti_path.name}")

    print("\nDone. Suggested validation:")
    print(f"  bids-validator {bids_root}")
    print("\nNote: files with space-/desc- entities are often treated as derivative-style BIDS names.")
    print("For a strict raw BIDS dataset, store native-space defaced images as sub-*/anat/sub-*_T1w.nii.gz")
    print("and place MNI-registered outputs under derivatives/.")


if __name__ == "__main__":
    main()
