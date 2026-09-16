
from __future__ import annotations

import os
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np


# ============================================================
# GENERAL HELPERS
# ============================================================

def _local_name(tag: str) -> str:
    """Return XML tag name without namespace."""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _find_xml_value(root: ET.Element, names) -> Optional[str]:
    """
    Recursively search XML by local tag name.
    """
    wanted = {str(x).lower() for x in names}

    for elem in root.iter():
        if _local_name(elem.tag).lower() in wanted:
            text = _clean_text(elem.text)
            if text:
                return text

    return None


def _find_xml_int(root: ET.Element, names) -> Optional[int]:
    value = _find_xml_value(root, names)

    if value is None:
        return None

    match = re.search(r"-?\d+", value)

    if not match:
        return None

    try:
        return int(match.group(0))
    except Exception:
        return None


def _find_xml_float(root: ET.Element, names) -> Optional[float]:
    value = _find_xml_value(root, names)

    if value is None:
        return None

    match = re.search(r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group(0))
    except Exception:
        return None


# ============================================================
# PDS4 XML PARSER
# ============================================================

def _parse_pds4_xml(xml_path: Path) -> Dict[str, Any]:
    """
    Parse the detached PDS4 XML label.

    The important values are:
        lines
        samples
        bands
        sample_bits
        data_type
        byte_order
        offset
        storage organization
    """

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # --------------------------------------------------------
    # Dimensions
    # --------------------------------------------------------

    lines = _find_xml_int(
        root,
        [
            "lines",
            "line_count",
            "num_lines",
        ],
    )

    samples = _find_xml_int(
        root,
        [
            "samples",
            "sample_count",
            "num_samples",
        ],
    )

    bands = _find_xml_int(
        root,
        [
            "bands",
            "band_count",
            "num_bands",
        ],
    )

    # --------------------------------------------------------
    # Axis_Array fallback
    # --------------------------------------------------------

    if not lines or not samples:
        axis_values = {}

        for elem in root.iter():
            if _local_name(elem.tag).lower() != "axis_array":
                continue

            axis_name = None
            elements = None

            for child in elem.iter():
                lname = _local_name(child.tag).lower()

                if lname == "axis_name":
                    axis_name = _clean_text(child.text)

                elif lname == "elements":
                    try:
                        elements = int(str(child.text).strip())
                    except Exception:
                        pass

            if axis_name and elements:
                axis_values[axis_name.lower()] = elements

        for name, value in axis_values.items():
            if "line" in name:
                lines = value

            elif "sample" in name:
                samples = value

            elif "band" in name:
                bands = value

    if not bands:
        bands = 1

    if not lines or not samples:
        raise ValueError(
            f"PDS label is missing usable image dimensions. "
            f"Parsed lines={lines}, samples={samples}, bands={bands}."
        )

    # --------------------------------------------------------
    # Sample bits
    # --------------------------------------------------------

    sample_bits = _find_xml_int(
        root,
        [
            "sample_bits",
            "bits_per_sample",
            "bit_depth",
        ],
    )

    # --------------------------------------------------------
    # Data type
    # --------------------------------------------------------

    data_type = _find_xml_value(
        root,
        [
            "data_type",
            "sample_type",
            "element_type",
        ],
    )

    if data_type:
        data_type_lower = data_type.lower()
    else:
        data_type_lower = ""

    # --------------------------------------------------------
    # Byte order
    # --------------------------------------------------------

    byte_order = _find_xml_value(
        root,
        [
            "byte_order",
            "endianness",
        ],
    )

    byte_order_lower = byte_order.lower() if byte_order else ""

    # --------------------------------------------------------
    # Offset
    # --------------------------------------------------------

    offset = _find_xml_int(
        root,
        [
            "offset",
            "data_offset",
            "offset_bytes",
        ],
    )

    if offset is None:
        offset = 0

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    storage = _find_xml_value(
        root,
        [
            "storage_type",
            "interchange_format",
            "axis_index_order",
        ],
    )

    storage_lower = storage.lower() if storage else ""

    return {
        "lines": int(lines),
        "samples": int(samples),
        "bands": int(bands),
        "sample_bits": sample_bits,
        "data_type": data_type,
        "byte_order": byte_order,
        "offset": int(offset),
        "storage": storage,
        "storage_lower": storage_lower,
        "xml_path": str(xml_path),
    }


# ============================================================
# PDS3 LABEL PARSER
# ============================================================

def _parse_pds_label(label_path: Path) -> Dict[str, Any]:
    text = label_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    def find_int(patterns):
        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    pass

        return None

    def find_value(patterns):
        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1).strip()

        return None

    lines = find_int(
        [
            r"^\s*LINES\s*=\s*(\d+)",
            r"^\s*LINE_COUNT\s*=\s*(\d+)",
        ]
    )

    samples = find_int(
        [
            r"^\s*SAMPLES\s*=\s*(\d+)",
            r"^\s*SAMPLE_COUNT\s*=\s*(\d+)",
        ]
    )

    bands = find_int(
        [
            r"^\s*BANDS\s*=\s*(\d+)",
            r"^\s*BAND_COUNT\s*=\s*(\d+)",
        ]
    )

    sample_bits = find_int(
        [
            r"^\s*SAMPLE_BITS\s*=\s*(\d+)",
            r"^\s*BITS_PER_SAMPLE\s*=\s*(\d+)",
        ]
    )

    data_type = find_value(
        [
            r"^\s*SAMPLE_TYPE\s*=\s*([A-Za-z0-9_]+)",
            r"^\s*DATA_TYPE\s*=\s*([A-Za-z0-9_]+)",
        ]
    )

    byte_order = find_value(
        [
            r"^\s*BYTE_ORDER\s*=\s*([A-Za-z0-9_]+)",
        ]
    )

    offset = find_int(
        [
            r"^\s*IMAGE_DATA_OFFSET\s*=\s*(\d+)",
            r"^\s*^RECORD_BYTES\s*=\s*(\d+)",
        ]
    )

    return {
        "lines": lines,
        "samples": samples,
        "bands": bands or 1,
        "sample_bits": sample_bits,
        "data_type": data_type,
        "byte_order": byte_order,
        "offset": offset or 0,
        "storage": None,
        "storage_lower": "",
        "label_path": str(label_path),
    }


# ============================================================
# DTYPE SELECTION
# ============================================================

def _dtype_from_metadata(
    sample_bits: Optional[int],
    data_type: Optional[str],
    byte_order: Optional[str],
) -> np.dtype:

    data_type_lower = (data_type or "").lower()
    byte_order_lower = (byte_order or "").lower()

    # --------------------------------------------------------
    # First determine signed/unsigned/floating.
    # --------------------------------------------------------

    if "float" in data_type_lower:
        if sample_bits == 64:
            dtype = np.dtype("f8")
        else:
            dtype = np.dtype("f4")

    elif "signed" in data_type_lower or "integer" in data_type_lower:
        if sample_bits == 8:
            dtype = np.dtype("i1")
        elif sample_bits == 16:
            dtype = np.dtype("i2")
        elif sample_bits == 32:
            dtype = np.dtype("i4")
        elif sample_bits == 64:
            dtype = np.dtype("i8")
        else:
            dtype = np.dtype("u1")

    else:
        if sample_bits == 8:
            dtype = np.dtype("u1")
        elif sample_bits == 16:
            dtype = np.dtype("u2")
        elif sample_bits == 32:
            dtype = np.dtype("u4")
        elif sample_bits == 64:
            dtype = np.dtype("u8")
        else:
            dtype = np.dtype("u1")

    # --------------------------------------------------------
    # Endianness
    # --------------------------------------------------------

    if dtype.itemsize > 1:

        if (
            "little" in byte_order_lower
            or "lsb" in byte_order_lower
            or "little_endian" in byte_order_lower
        ):
            dtype = dtype.newbyteorder("<")

        elif (
            "big" in byte_order_lower
            or "msb" in byte_order_lower
            or "big_endian" in byte_order_lower
        ):
            dtype = dtype.newbyteorder(">")

    return dtype


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_scientific_image(image: np.ndarray) -> np.ndarray:

    image = np.asarray(image)

    if image.ndim > 2:
        image = np.squeeze(image)

    if image.ndim != 2:
        raise ValueError(
            f"Expected a 2D scientific image, got shape {image.shape}."
        )

    image = image.astype(np.float32)

    finite = np.isfinite(image)

    if not np.any(finite):
        raise ValueError("Scientific image contains no finite pixels.")

    values = image[finite]

    low = np.percentile(values, 1)
    high = np.percentile(values, 99)

    if high <= low:
        low = float(values.min())
        high = float(values.max())

    if high <= low:
        return np.zeros(image.shape, dtype=np.uint8)

    normalized = (image - low) / (high - low)

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    return (normalized * 255.0).astype(np.uint8)


# ============================================================
# LABEL SEARCH
# ============================================================

def _find_label(
    image_path: Path,
    search_root: Optional[Path] = None,
) -> Optional[Path]:

    stem = image_path.stem

    candidates = []

    # Exact same directory.
    candidates.extend(
        [
            image_path.with_suffix(".xml"),
            image_path.with_suffix(".XML"),
            image_path.with_suffix(".lbl"),
            image_path.with_suffix(".LBL"),
        ]
    )

    # Recursive search around the image.
    roots = [image_path.parent]

    if search_root and search_root.exists():
        roots.append(search_root)

    for root in roots:

        try:
            for path in root.rglob("*"):

                if not path.is_file():
                    continue

                if path.suffix.lower() not in {
                    ".xml",
                    ".lbl",
                }:
                    continue

                if path.stem.lower() == stem.lower():
                    candidates.append(path)

        except Exception:
            pass

    # Return first existing exact match.
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# ============================================================
# LOAD SCIENTIFIC IMG
# ============================================================

def _load_pds_img(
    img_path: Path,
    label_path: Path,
) -> Tuple[np.ndarray, Dict[str, Any]]:

    # --------------------------------------------------------
    # Parse label.
    # --------------------------------------------------------

    if label_path.suffix.lower() == ".xml":
        metadata = _parse_pds4_xml(label_path)
    else:
        metadata = _parse_pds_label(label_path)

    lines = int(metadata["lines"])
    samples = int(metadata["samples"])
    bands = int(metadata.get("bands", 1) or 1)
    offset = int(metadata.get("offset", 0) or 0)

    sample_bits = metadata.get("sample_bits")
    data_type = metadata.get("data_type")
    byte_order = metadata.get("byte_order")

    file_size = img_path.stat().st_size

    available_bytes = file_size - offset

    if available_bytes < 0:
        raise ValueError(
            f"Invalid data offset {offset} for file size {file_size}."
        )

    pixel_count = lines * samples * bands

    # ========================================================
    # CRITICAL REAL-WORLD PDS FIX
    # ========================================================
    #
    # Some Chandrayaan-2 products have metadata fields that
    # can be interpreted incorrectly by a generic XML parser.
    #
    # Therefore, if the actual file size exactly matches:
    #
    #     number of pixels
    #
    # then the file is unquestionably one byte per pixel.
    #
    # If it exactly matches 2 * pixels, it is 16-bit.
    #
    # This prevents the parser from interpreting a valid
    # 8-bit Chandrayaan image as uint16.
    # ========================================================

    inferred_dtype = None

    if available_bytes == pixel_count:
        inferred_dtype = np.dtype("u1")

    elif available_bytes == pixel_count * 2:
        inferred_dtype = _dtype_from_metadata(
            16,
            data_type,
            byte_order,
        )

    elif available_bytes == pixel_count * 4:
        inferred_dtype = _dtype_from_metadata(
            32,
            data_type,
            byte_order,
        )

    elif available_bytes == pixel_count * 8:
        inferred_dtype = _dtype_from_metadata(
            64,
            data_type,
            byte_order,
        )

    # --------------------------------------------------------
    # If file-size inference succeeded, trust the physical
    # file layout.
    # --------------------------------------------------------

    if inferred_dtype is not None:
        dtype = inferred_dtype

    else:
        dtype = _dtype_from_metadata(
            sample_bits,
            data_type,
            byte_order,
        )

    expected_bytes = pixel_count * dtype.itemsize

    print("")
    print("EPHEMERIS PDS IMAGE")
    print(f"File       : {img_path}")
    print(f"Label      : {label_path}")
    print(f"Dimensions : {samples} x {lines}")
    print(f"Bands      : {bands}")
    print(f"XML dtype  : {data_type}")
    print(f"XML bits   : {sample_bits}")
    print(f"Actual dtype: {dtype}")
    print(f"Offset     : {offset} bytes")
    print(f"Available  : {available_bytes} bytes")
    print(f"Expected   : {expected_bytes} bytes")
    print("")

    # --------------------------------------------------------
    # Validate.
    # --------------------------------------------------------

    if available_bytes < expected_bytes:

        raise ValueError(
            f"Scientific image file is smaller than expected "
            f"from its PDS label. "
            f"Expected {expected_bytes:,} bytes after offset "
            f"{offset}, but only {available_bytes:,} bytes are available."
        )

    # --------------------------------------------------------
    # Read raw data.
    # --------------------------------------------------------

    with open(img_path, "rb") as f:

        if offset:
            f.seek(offset)

        raw = np.fromfile(
            f,
            dtype=dtype,
            count=pixel_count,
        )

    if raw.size != pixel_count:

        raise ValueError(
            f"Could not read expected number of pixels. "
            f"Expected {pixel_count:,}, got {raw.size:,}."
        )

    # --------------------------------------------------------
    # Handle image organization.
    # --------------------------------------------------------

    storage_lower = str(
        metadata.get("storage_lower", "")
    ).lower()

    if "bil" in storage_lower:

        # Band-interleaved-by-line.
        image = raw.reshape(
            lines,
            bands,
            samples,
        )

        if bands == 1:
            image = image[:, 0, :]
        else:
            image = image[:, 0, :]

    elif "bip" in storage_lower:

        # Band-interleaved-by-pixel.
        image = raw.reshape(
            lines,
            samples,
            bands,
        )

        if bands == 1:
            image = image[:, :, 0]
        else:
            image = image[:, :, 0]

    else:

        # Default PDS scientific image organization:
        # BSQ.
        image = raw.reshape(
            bands,
            lines,
            samples,
        )

        if bands == 1:
            image = image[0]
        else:
            image = image[0]

    image = _normalize_scientific_image(image)

    info = {
        "format": "PDS scientific image",
        "source_path": str(img_path),
        "label_path": str(label_path),
        "width": int(samples),
        "height": int(lines),
        "bands": int(bands),
        "dtype": str(dtype),
        "sample_bits": int(dtype.itemsize * 8),
        "xml_sample_bits": sample_bits,
        "offset": int(offset),
        "file_size": int(file_size),
        "available_bytes": int(available_bytes),
        "expected_bytes": int(expected_bytes),
    }

    return image, info


# ============================================================
# ZIP HANDLING
# ============================================================

def _extract_zip(zip_path: Path) -> Path:

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="ephemeris_"
        )
    )

    print(
        f"EPHEMERIS ZIP EXTRACT: {zip_path}"
    )

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)

    print(
        f"EPHEMERIS EXTRACTED TO: {temp_dir}"
    )

    return temp_dir


def _find_img_inside_directory(
    directory: Path,
    preferred_stem: Optional[str] = None,
) -> Optional[Path]:

    imgs = []

    for path in directory.rglob("*"):

        if path.is_file() and path.suffix.lower() == ".img":
            imgs.append(path)

    if not imgs:
        return None

    # Prefer exact stem.
    if preferred_stem:

        for path in imgs:

            if path.stem.lower() == preferred_stem.lower():
                return path

    # Prefer calibrated imagery.
    calibrated = [
        path
        for path in imgs
        if "calibrated" in str(path).lower()
    ]

    if calibrated:
        return calibrated[0]

    return imgs[0]


def _load_zip(
    zip_path: Path,
) -> Tuple[np.ndarray, Dict[str, Any]]:

    extract_dir = _extract_zip(zip_path)

    preferred_stem = zip_path.stem

    img_path = _find_img_inside_directory(
        extract_dir,
        preferred_stem=preferred_stem,
    )

    if img_path is None:
        raise ValueError(
            f"No .img scientific image was found inside ZIP: "
            f"{zip_path.name}"
        )

    label_path = _find_label(
        img_path,
        search_root=extract_dir,
    )

    if label_path is None:
        raise ValueError(
            f"No matching PDS XML/LBL label found for: "
            f"{img_path.name}"
        )

    image, info = _load_pds_img(
        img_path,
        label_path,
    )

    info["archive_path"] = str(zip_path)
    info["extracted_directory"] = str(extract_dir)

    return image, info


# ============================================================
# NORMAL IMAGE LOADER
# ============================================================

def _load_standard_image(
    image_path: Path,
) -> Tuple[np.ndarray, Dict[str, Any]]:

    image = cv2.imread(
        str(image_path),
        cv2.IMREAD_UNCHANGED,
    )

    if image is None:
        raise ValueError(
            f"Could not decode image: {image_path.name}"
        )

    if image.ndim == 3:

        image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    if image.dtype != np.uint8:
        image = _normalize_scientific_image(image)

    return image, {
        "format": image_path.suffix.lower(),
        "source_path": str(image_path),
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "bands": 1,
        "dtype": str(image.dtype),
    }


# ============================================================
# PUBLIC IMAGE LOADER
# ============================================================

def load_image_from_path(
    image_path: str | Path,
) -> Tuple[np.ndarray, Dict[str, Any]]:

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image file not found: {path}"
        )

    suffix = path.suffix.lower()

    # --------------------------------------------------------
    # ZIP
    # --------------------------------------------------------

    if suffix == ".zip":

        return _load_zip(path)

    # --------------------------------------------------------
    # Scientific PDS image
    # --------------------------------------------------------

    if suffix == ".img":

        label_path = _find_label(path)

        if label_path is None:

            raise ValueError(
                f"No matching PDS XML/LBL label found for "
                f"{path.name}. "
                f"An ISRO PDS .img normally requires its label."
            )

        return _load_pds_img(
            path,
            label_path,
        )

    # --------------------------------------------------------
    # Normal image formats
    # --------------------------------------------------------

    if suffix in {
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".bmp",
        ".webp",
    }:

        return _load_standard_image(path)

    raise ValueError(
        f"Unsupported image format: {suffix}"
    )


# ============================================================
# UPLOAD TEMP FILE
# ============================================================

def save_upload_to_temp(
    upload_file,
) -> str:

    suffix = Path(
        upload_file.filename or ""
    ).suffix

    fd, temp_path = tempfile.mkstemp(
        suffix=suffix
    )

    os.close(fd)

    with open(temp_path, "wb") as f:

        while True:

            chunk = upload_file.file.read(
                1024 * 1024
            )

            if not chunk:
                break

            f.write(chunk)

    print(
        f"EPHEMERIS TEMP FILE: {temp_path}"
    )

    return temp_path

