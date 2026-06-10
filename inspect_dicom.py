import pydicom

for fname in [
    "IMG-0003-00001.dcm",
    "IMG-0004-00001.dcm"
]:
    print("\n--------------------")
    print(fname)

    ds = pydicom.dcmread(fname)

    print("Modality:", getattr(ds, "Modality", None))
    print("SeriesDescription:", getattr(ds, "SeriesDescription", None))
    print("Rows:", getattr(ds, "Rows", None))
    print("Columns:", getattr(ds, "Columns", None))
    print("NumberOfFrames:", getattr(ds, "NumberOfFrames", 1))