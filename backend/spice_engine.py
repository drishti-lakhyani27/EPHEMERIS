import re
from pathlib import Path

import spiceypy as spice


# EPHEMERIS/spice
SPICE_DIR = Path(__file__).resolve().parent.parent / "spice"

SPACECRAFT_ID = "-152"
REFERENCE_BODY = "MOON"
FRAME = "J2000"


def load_kernels():
    """
    Load all supported SPICE kernels found inside EPHEMERIS/spice.
    """
    kernel_extensions = {
        ".bsp",
        ".bc",
        ".tf",
        ".ti",
        ".tls",
        ".tpc",
        ".tsc",
        ".tm",
    }

    loaded = []

    if not SPICE_DIR.exists():
        print("SPICE directory not found.")
        return loaded

    for kernel in sorted(SPICE_DIR.rglob("*")):
        if kernel.suffix.lower() not in kernel_extensions:
            continue

        try:
            spice.furnsh(str(kernel))
            loaded.append(str(kernel))
            print(f"Loaded SPICE kernel: {kernel.name}")

        except Exception as e:
            print(f"Could not load {kernel.name}: {e}")

    return loaded


def clear_kernels():
    """
    Clear all loaded SPICE kernels.
    """
    spice.kclear()


def extract_observation_time(filename):
    """
    Extract Chandrayaan-style observation timestamp from filename.

    Example:
    ch2_ohr_ncp_20211228T2209123959_d_img_d18

    becomes:
    2021-12-28T22:09:12.3959
    """

    if not filename:
        return None

    match = re.search(
        r"(\d{8})T(\d{10,})",
        filename
    )

    if not match:
        return None

    date_part = match.group(1)
    time_part = match.group(2)

    year = date_part[0:4]
    month = date_part[4:6]
    day = date_part[6:8]

    hour = time_part[0:2]
    minute = time_part[2:4]
    second = time_part[4:6]

    fraction = time_part[6:]

    if fraction:
        fraction = "." + fraction

    return (
        f"{year}-{month}-{day}"
        f"T{hour}:{minute}:{second}{fraction}"
    )


def utc_to_et(utc_time):
    """
    Convert UTC timestamp to SPICE ephemeris time.
    """
    if not utc_time:
        return None

    return spice.str2et(utc_time)


def get_spacecraft_position(et):
    """
    Get Chandrayaan-2 spacecraft position relative to the Moon.
    """

    position, light_time = spice.spkpos(
        SPACECRAFT_ID,
        et,
        FRAME,
        "NONE",
        REFERENCE_BODY,
    )

    return {
        "x": float(position[0]),
        "y": float(position[1]),
        "z": float(position[2]),
        "light_time_seconds": float(light_time),
    }


def get_sun_position(et):
    """
    Get Sun position relative to the Moon.
    """

    position, light_time = spice.spkpos(
        "SUN",
        et,
        FRAME,
        "NONE",
        REFERENCE_BODY,
    )

    distance = spice.vnorm(position)

    return {
        "x": float(position[0]),
        "y": float(position[1]),
        "z": float(position[2]),
        "distance_km": float(distance),
        "light_time_seconds": float(light_time),
    }


def calculate_spice_geometry(observation_time_utc):
    """
    Calculate real SPICE geometry for a given observation timestamp.

    Returns None geometry instead of fake values if the required
    SPICE coverage is unavailable.
    """

    if not observation_time_utc:
        return {
            "status": "NO_OBSERVATION_TIME",
            "geometry_available": False,
            "message": (
                "Observation timestamp could not be extracted "
                "from the uploaded filename."
            ),
        }

    try:
        et = utc_to_et(observation_time_utc)

        spacecraft = get_spacecraft_position(et)
        sun = get_sun_position(et)

        return {
            "status": "READY",
            "geometry_available": True,

            "observation_time_utc": observation_time_utc,
            "ephemeris_time": float(et),

            "reference_body": REFERENCE_BODY,
            "frame": FRAME,

            "spacecraft": {
                "id": SPACECRAFT_ID,
                "position_km": spacecraft,
            },

            "sun": sun,
        }

    except Exception as e:

        return {
            "status": "COVERAGE_UNAVAILABLE",
            "geometry_available": False,
            "observation_time_utc": observation_time_utc,
            "message": str(e),
        }


def process_image_metadata(filename):
    """
    Process uploaded image metadata and calculate SPICE geometry
    when the original Chandrayaan observation timestamp is available.
    """

    observation_time = extract_observation_time(filename)

    result = {
        "filename": filename,
        "observation_time_utc": observation_time,
    }

    if observation_time:
        geometry = calculate_spice_geometry(observation_time)
        result.update(geometry)

    else:
        result.update({
            "status": "NO_OBSERVATION_TIME",
            "geometry_available": False,
            "message": (
                "Original Chandrayaan observation timestamp "
                "was not found in the filename."
            ),
        })

    return result


def get_spice_status():
    """
    Return basic information about currently loaded SPICE kernels.
    """

    count = spice.ktotal("ALL")

    kernels = []

    for i in range(count):
        try:
            file_name, kernel_type, source, handle, found = spice.kdata(
                i,
                "ALL",
                256,
                256,
                256,
                256,
                256,
            )

            kernels.append({
                "file": file_name,
                "type": kernel_type,
            })

        except Exception:
            pass

    return {
        "loaded_kernel_count": count,
        "kernels": kernels,
    }