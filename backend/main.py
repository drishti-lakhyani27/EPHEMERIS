
import os
import time

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from backend.cv_engine import process_images
from backend.spice_engine import load_kernels, process_image_metadata
from backend.image_loader import (
    save_upload_to_temp,
    load_image_from_path,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="EPHEMERIS",
    description="AI-Assisted Lunar Image Registration & Correspondence Prototype",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# SPICE
# =========================================================

try:
    KERNELS = load_kernels()

    print()
    print("EPHEMERIS SPICE STATUS")
    print("----------------------")
    print("Kernels loaded:", len(KERNELS))

except Exception as exc:

    KERNELS = []

    print()
    print("EPHEMERIS SPICE WARNING")
    print("-----------------------")
    print(repr(exc))


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root():

    return {
        "project": "EPHEMERIS",
        "status": "online",
        "service": "Lunar Image Correspondence Backend",
    }


@app.get("/health")
def health():

    return {
        "status": "online",
        "spice_kernels": len(KERNELS),
    }


# =========================================================
# IMAGE UPLOAD
# =========================================================

@app.post("/upload")
async def upload_images(
    source: UploadFile = File(...),
    reference: UploadFile = File(...),
):

    start_time = time.perf_counter()

    source_temp = None
    reference_temp = None

    try:

        print()
        print("================================================")
        print("EPHEMERIS NEW PROCESSING REQUEST")
        print("================================================")

        print(
            "SOURCE FILE    :",
            source.filename
        )

        print(
            "REFERENCE FILE :",
            reference.filename
        )

        # -------------------------------------------------
        # SAVE SOURCE UPLOAD
        # -------------------------------------------------

        source_temp = save_upload_to_temp(
            source
        )

        # -------------------------------------------------
        # SAVE REFERENCE UPLOAD
        # -------------------------------------------------

        reference_temp = save_upload_to_temp(
            reference
        )

        print()
        print(
            "SOURCE TEMP    :",
            source_temp
        )

        print(
            "REFERENCE TEMP :",
            reference_temp
        )

        # -------------------------------------------------
        # LOAD SOURCE IMAGE
        # -------------------------------------------------

        print()
        print("EPHEMERIS: decoding source image...")

        source_image, source_info = load_image_from_path(
            source_temp
        )

        # -------------------------------------------------
        # LOAD REFERENCE IMAGE
        # -------------------------------------------------

        print(
            "EPHEMERIS: decoding reference image..."
        )

        reference_image, reference_info = load_image_from_path(
            reference_temp
        )

        # -------------------------------------------------
        # VERIFY NUMPY IMAGES
        # -------------------------------------------------

        if source_image is None:
            raise ValueError(
                "Source image could not be decoded."
            )

        if reference_image is None:
            raise ValueError(
                "Reference image could not be decoded."
            )

        print()
        print(
            "SOURCE IMAGE    :",
            source_image.shape[1],
            "x",
            source_image.shape[0]
        )

        print(
            "REFERENCE IMAGE :",
            reference_image.shape[1],
            "x",
            reference_image.shape[0]
        )

        print(
            "SOURCE DTYPE    :",
            source_image.dtype
        )

        print(
            "REFERENCE DTYPE :",
            reference_image.dtype
        )

        # -------------------------------------------------
        # START COMPUTER VISION
        # -------------------------------------------------

        print()
        print(
            "EPHEMERIS: starting computer-vision pipeline..."
        )

        result = process_images(
            source_image,
            reference_image
        )

        # -------------------------------------------------
        # SPICE METADATA
        # -------------------------------------------------

        print()
        print(
            "EPHEMERIS: processing SPICE metadata..."
        )

        # IMPORTANT:
        # process_image_metadata() accepts ONE argument:
        # the image filename.
        #
        # The previous version incorrectly passed KERNELS
        # as a second argument.

        try:

            spice_source = process_image_metadata(
                source.filename
            )

        except Exception as exc:

            spice_source = {
                "status": "error",
                "error": repr(exc)
            }

        try:

            spice_reference = process_image_metadata(
                reference.filename
            )

        except Exception as exc:

            spice_reference = {
                "status": "error",
                "error": repr(exc)
            }

        # -------------------------------------------------
        # SOURCE INFORMATION
        # -------------------------------------------------

        result["source"]["file"] = (
            source.filename
        )

        result["source"]["format"] = (
            source_info.get(
                "format",
                "unknown"
            )
        )

        result["source"]["loader_info"] = (
            source_info
        )

        # -------------------------------------------------
        # REFERENCE INFORMATION
        # -------------------------------------------------

        result["reference"]["file"] = (
            reference.filename
        )

        result["reference"]["format"] = (
            reference_info.get(
                "format",
                "unknown"
            )
        )

        result["reference"]["loader_info"] = (
            reference_info
        )

        # -------------------------------------------------
        # SPICE
        # -------------------------------------------------

        result["spice"] = {

            "source": spice_source,

            "reference": spice_reference,

            "kernels_loaded": len(
                KERNELS
            )
        }

        # -------------------------------------------------
        # FILE INFORMATION
        # -------------------------------------------------

        result["files"] = {

            "source": {
                "filename": source.filename,
                "content_type": source.content_type,
                "size_bytes": os.path.getsize(
                    source_temp
                )
            },

            "reference": {
                "filename": reference.filename,
                "content_type": reference.content_type,
                "size_bytes": os.path.getsize(
                    reference_temp
                )
            }
        }

        # -------------------------------------------------
        # PIPELINE INFORMATION
        # -------------------------------------------------

        result["pipeline_status"] = "completed"

        result["backend"] = {
            "service": "EPHEMERIS",
            "version": "1.0.0",
            "cv_engine": "SIFT + MAGSAC/RANSAC",
            "deep_learning": False,
            "processing_mode": "memory-safe"
        }

        # -------------------------------------------------
        # TOTAL PROCESSING TIME
        # -------------------------------------------------

        total_time = (
            time.perf_counter()
            - start_time
        )

        result["total_processing_time"] = (
            total_time
        )

        print()
        print("================================================")
        print("EPHEMERIS REQUEST COMPLETE")
        print("================================================")

        print(
            "Total processing time:",
            round(total_time, 3),
            "seconds"
        )

        print(
            "Result:",
            "SUCCESS"
        )

        print("================================================")
        print()

        return result

    except Exception as exc:

        print()
        print("================================================")
        print("EPHEMERIS ERROR")
        print("================================================")

        print(
            repr(exc)
        )

        print("================================================")
        print()

        return {
            "success": False,

            "error": repr(exc),

            "message":
                "EPHEMERIS processing failed.",

            "pipeline_status":
                "failed"
        }

    finally:

        # -------------------------------------------------
        # CLEAN TEMP FILES
        # -------------------------------------------------

        for path in [
            source_temp,
            reference_temp
        ]:

            if path:

                try:

                    if os.path.exists(path):
                        os.remove(path)

                except Exception:
                    pass

