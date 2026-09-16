
import cv2
import numpy as np
import base64
from time import perf_counter


# =========================================================
# EPHEMERIS CONFIGURATION
# =========================================================

MAX_PROCESSING_DIM = 2500
MAX_FEATURES = 5000

RATIO_TEST = 0.75

RANSAC_THRESHOLD = 3.0
RANSAC_CONFIDENCE = 0.999
RANSAC_MAX_ITERS = 10000

MAX_VISUAL_MATCHES = 5000


# =========================================================
# IMAGE PROCESSING
# =========================================================

def create_processing_image(image):

    h, w = image.shape[:2]

    largest_dimension = max(h, w)

    if largest_dimension <= MAX_PROCESSING_DIM:

        scale = 1.0
        working = image.copy()

    else:

        scale = (
            MAX_PROCESSING_DIM /
            float(largest_dimension)
        )

        new_w = max(
            1,
            int(round(w * scale))
        )

        new_h = max(
            1,
            int(round(h * scale))
        )

        working = cv2.resize(
            image,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

    return working, scale


def prepare_gray(image):

    if len(image.shape) == 3:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    else:

        gray = image.copy()

    if gray.dtype != np.uint8:

        gray = cv2.normalize(
            gray,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        ).astype(np.uint8)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(gray)

    return gray


# =========================================================
# FEATURE DETECTION
# =========================================================

def detect_features(gray):

    print(
        "EPHEMERIS FEATURE DETECTOR: SIFT"
    )

    sift = cv2.SIFT_create(
        nfeatures=MAX_FEATURES,
        contrastThreshold=0.02,
        edgeThreshold=10
    )

    keypoints, descriptors = (
        sift.detectAndCompute(
            gray,
            None
        )
    )

    return keypoints, descriptors


# =========================================================
# DESCRIPTOR MATCHING
# =========================================================

def ratio_matches(
    des1,
    des2
):

    if des1 is None or des2 is None:
        return []

    if len(des1) == 0 or len(des2) == 0:
        return []

    matcher = cv2.BFMatcher(
        cv2.NORM_L2,
        crossCheck=False
    )

    knn = matcher.knnMatch(
        des1,
        des2,
        k=2
    )

    good = []

    for pair in knn:

        if len(pair) < 2:
            continue

        m, n = pair

        if m.distance < RATIO_TEST * n.distance:

            good.append(m)

    return good


def mutual_matches(
    des1,
    des2
):

    forward = ratio_matches(
        des1,
        des2
    )

    backward = ratio_matches(
        des2,
        des1
    )

    backward_pairs = {
        (m.trainIdx, m.queryIdx)
        for m in backward
    }

    mutual = []

    for m in forward:

        pair = (
            m.queryIdx,
            m.trainIdx
        )

        if pair in backward_pairs:

            mutual.append(m)

    return mutual


# =========================================================
# HOMOGRAPHY
# =========================================================

def estimate_homography(
    points_source,
    points_reference
):

    if len(points_source) < 4:

        return None, None

    try:

        if hasattr(
            cv2,
            "USAC_MAGSAC"
        ):

            H, mask = cv2.findHomography(
                points_source,
                points_reference,
                cv2.USAC_MAGSAC,
                RANSAC_THRESHOLD,
                None,
                RANSAC_MAX_ITERS,
                RANSAC_CONFIDENCE
            )

        else:

            H, mask = cv2.findHomography(
                points_source,
                points_reference,
                cv2.RANSAC,
                RANSAC_THRESHOLD,
                None,
                RANSAC_MAX_ITERS,
                RANSAC_CONFIDENCE
            )

        return H, mask

    except Exception:

        H, mask = cv2.findHomography(
            points_source,
            points_reference,
            cv2.RANSAC,
            RANSAC_THRESHOLD
        )

        return H, mask


# =========================================================
# REPROJECTION ERROR
# =========================================================

def calculate_reprojection_errors(
    source_points,
    reference_points,
    H
):

    if (
        H is None
        or len(source_points) == 0
    ):

        return np.array(
            [],
            dtype=np.float32
        )

    projected = cv2.perspectiveTransform(
        source_points
        .reshape(-1, 1, 2)
        .astype(np.float32),
        H
    ).reshape(-1, 2)

    errors = np.linalg.norm(
        projected - reference_points,
        axis=1
    )

    return errors


# =========================================================
# SPATIAL COVERAGE
# =========================================================

def calculate_spatial_coverage(
    points,
    width,
    height
):

    if len(points) == 0:

        return 0.0

    occupied = set()

    grid_x = 4
    grid_y = 4

    for x, y in points:

        cell_x = int(
            min(
                grid_x - 1,
                max(
                    0,
                    x /
                    max(width, 1)
                    * grid_x
                )
            )
        )

        cell_y = int(
            min(
                grid_y - 1,
                max(
                    0,
                    y /
                    max(height, 1)
                    * grid_y
                )
            )
        )

        occupied.add(
            (
                cell_x,
                cell_y
            )
        )

    return (
        len(occupied) /
        float(grid_x * grid_y)
    )


# =========================================================
# IMAGE PREPARATION
# =========================================================

def ensure_color(image):

    if len(image.shape) == 2:

        return cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGR
        )

    return image.copy()


# =========================================================
# VISUALIZATION CANVAS
# =========================================================

def create_correspondence_canvas(
    source_working,
    reference_working
):

    source_color = ensure_color(
        source_working
    )

    reference_color = ensure_color(
        reference_working
    )

    source_h, source_w = (
        source_color.shape[:2]
    )

    reference_h, reference_w = (
        reference_color.shape[:2]
    )

    canvas_height = max(
        source_h,
        reference_h
    )

    canvas_width = (
        source_w +
        reference_w
    )

    canvas = np.zeros(
        (
            canvas_height,
            canvas_width,
            3
        ),
        dtype=np.uint8
    )

    canvas[
        0:source_h,
        0:source_w
    ] = source_color

    canvas[
        0:reference_h,
        source_w:
        source_w + reference_w
    ] = reference_color

    cv2.line(
        canvas,
        (source_w, 0),
        (
            source_w,
            canvas_height
        ),
        (120, 120, 120),
        2
    )

    cv2.rectangle(
        canvas,
        (12, 12),
        (155, 50),
        (10, 15, 20),
        -1
    )

    cv2.putText(
        canvas,
        "SOURCE",
        (22, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (230, 240, 245),
        2,
        cv2.LINE_AA
    )

    cv2.rectangle(
        canvas,
        (
            source_w + 12,
            12
        ),
        (
            source_w + 175,
            50
        ),
        (10, 15, 20),
        -1
    )

    cv2.putText(
        canvas,
        "REFERENCE",
        (
            source_w + 22,
            38
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (230, 240, 245),
        2,
        cv2.LINE_AA
    )

    return canvas, source_w, canvas_height


# =========================================================
# VISUALIZATION INDEX SELECTION
# =========================================================

def get_visual_indices(
    total,
    max_visual=MAX_VISUAL_MATCHES
):

    if total <= 0:

        return []

    if total <= max_visual:

        return list(
            range(total)
        )

    return list(
        np.linspace(
            0,
            total - 1,
            max_visual,
            dtype=int
        )
    )


# =========================================================
# DRAW MATCHES
# =========================================================

def draw_matches_on_canvas(
    canvas,
    source_w,
    source_keypoints,
    reference_keypoints,
    matches,
    inlier_mask,
    mode="lines_points"
):

    total = len(matches)

    if total == 0:

        return canvas

    indices = get_visual_indices(
        total
    )

    for i in indices:

        match = matches[i]

        is_inlier = bool(
            inlier_mask[i]
        )

        if mode == "inliers" and not is_inlier:

            continue

        if mode == "outliers" and is_inlier:

            continue

        src_pt = source_keypoints[
            match.queryIdx
        ].pt

        ref_pt = reference_keypoints[
            match.trainIdx
        ].pt

        x1 = int(
            round(src_pt[0])
        )

        y1 = int(
            round(src_pt[1])
        )

        x2 = (
            int(
                round(ref_pt[0])
            )
            +
            source_w
        )

        y2 = int(
            round(ref_pt[1])
        )

        if is_inlier:

            point_color = (
                40,
                230,
                140
            )

        else:

            point_color = (
                60,
                70,
                255
            )

        if mode == "lines_points":

            cv2.line(
                canvas,
                (x1, y1),
                (x2, y2),
                point_color,
                1,
                cv2.LINE_AA
            )

        cv2.circle(
            canvas,
            (x1, y1),
            3,
            point_color,
            -1,
            cv2.LINE_AA
        )

        cv2.circle(
            canvas,
            (x2, y2),
            3,
            point_color,
            -1,
            cv2.LINE_AA
        )

    return canvas


# =========================================================
# LEGEND
# =========================================================

def add_visualization_legend(
    canvas,
    mode
):

    canvas_height = canvas.shape[0]

    legend_x = 12

    legend_y = (
        canvas_height -
        58
    )

    cv2.rectangle(
        canvas,
        (
            legend_x,
            legend_y
        ),
        (
            legend_x + 360,
            canvas_height - 10
        ),
        (8, 14, 18),
        -1
    )

    cv2.circle(
        canvas,
        (
            legend_x + 18,
            legend_y + 16
        ),
        5,
        (40, 230, 140),
        -1
    )

    cv2.putText(
        canvas,
        "INLIER",
        (
            legend_x + 32,
            legend_y + 21
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (210, 220, 225),
        1,
        cv2.LINE_AA
    )

    cv2.circle(
        canvas,
        (
            legend_x + 125,
            legend_y + 16
        ),
        5,
        (60, 70, 255),
        -1
    )

    cv2.putText(
        canvas,
        "OUTLIER",
        (
            legend_x + 139,
            legend_y + 21
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (210, 220, 225),
        1,
        cv2.LINE_AA
    )

    mode_labels = {

        "lines_points":
            "LINES + POINTS",

        "points":
            "POINTS ONLY",

        "inliers":
            "INLIERS ONLY",

        "outliers":
            "OUTLIERS ONLY"

    }

    label = mode_labels.get(
        mode,
        "CORRESPONDENCE"
    )

    cv2.putText(
        canvas,
        label,
        (
            legend_x + 225,
            legend_y + 21
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (180, 195, 200),
        1,
        cv2.LINE_AA
    )

    return canvas


# =========================================================
# SINGLE CORRESPONDENCE VISUALIZATION
# =========================================================

def create_correspondence_preview(
    source_working,
    reference_working,
    source_keypoints,
    reference_keypoints,
    matches,
    inlier_mask,
    mode="lines_points"
):

    try:

        canvas, source_w, _ = (
            create_correspondence_canvas(
                source_working,
                reference_working
            )
        )

        canvas = draw_matches_on_canvas(
            canvas,
            source_w,
            source_keypoints,
            reference_keypoints,
            matches,
            inlier_mask,
            mode
        )

        canvas = add_visualization_legend(
            canvas,
            mode
        )

        return canvas

    except Exception as exc:

        print(
            "EPHEMERIS: correspondence visualization failed:",
            mode,
            repr(exc)
        )

        return None


# =========================================================
# CREATE ALL CORRESPONDENCE LAYERS
# =========================================================

def create_correspondence_layers(
    source_working,
    reference_working,
    source_keypoints,
    reference_keypoints,
    matches,
    inlier_mask
):

    print(
        "EPHEMERIS: creating correspondence layers..."
    )

    layers = {}

    modes = [
        "lines_points",
        "points",
        "inliers",
        "outliers"
    ]

    for mode in modes:

        print(
            f"EPHEMERIS: creating {mode} layer..."
        )

        preview = create_correspondence_preview(
            source_working,
            reference_working,
            source_keypoints,
            reference_keypoints,
            matches,
            inlier_mask,
            mode
        )

        layers[mode] = encode_png(
            preview
        )

        print(
            f"EPHEMERIS: {mode} layer:",
            "READY"
            if layers[mode]
            else "FAILED"
        )

    return layers


# =========================================================
# REGISTERED VISUALIZATION
# =========================================================

def create_registered_preview(
    source_working,
    reference_working,
    H
):

    if H is None:

        return None

    try:

        target_h, target_w = (
            reference_working.shape[:2]
        )

        source_color = ensure_color(
            source_working
        )

        reference_color = ensure_color(
            reference_working
        )

        registered = cv2.warpPerspective(
            source_color,
            H,
            (
                target_w,
                target_h
            ),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT
        )

        overlay = cv2.addWeighted(
            reference_color,
            0.5,
            registered,
            0.5,
            0
        )

        return overlay

    except Exception as exc:

        print(
            "EPHEMERIS: registered preview failed:",
            repr(exc)
        )

        return None


# =========================================================
# PNG ENCODING
# =========================================================

def encode_png(image):

    if image is None:

        return None

    try:

        success, encoded = cv2.imencode(
            ".png",
            image,
            [
                cv2.IMWRITE_PNG_COMPRESSION,
                3
            ]
        )

        if not success:

            return None

        return base64.b64encode(
            encoded.tobytes()
        ).decode("utf-8")

    except Exception as exc:

        print(
            "EPHEMERIS: PNG encoding failed:",
            repr(exc)
        )

        return None


# =========================================================
# PARTIAL RESULT BUILDER
# =========================================================

def build_partial_result(
    source_image,
    reference_image,
    source_working,
    reference_working,
    source_scale,
    reference_scale,
    source_keypoints,
    reference_keypoints,
    ratio,
    mutual,
    start_time,
    reason
):
    """
    Returns a valid EPHEMERIS result even when
    geometric transformation cannot be estimated.

    This is intentionally NOT treated as a server error.

    The system reports what it actually observed:
        - keypoints
        - descriptor matches
        - mutual matches
        - correspondence visualization
        - no invented homography
        - no invented reprojection error
        - no invented registration
    """

    source_h, source_w = (
        source_image.shape[:2]
    )

    reference_h, reference_w = (
        reference_image.shape[:2]
    )

    # -----------------------------------------------------
    # No geometric model exists.
    #
    # Therefore every available mutual match is
    # "unverified" rather than being falsely called
    # an inlier or outlier.
    # -----------------------------------------------------

    partial_mask = np.zeros(
        len(mutual),
        dtype=bool
    )

    correspondence_layers = (
        create_correspondence_layers(
            source_working,
            reference_working,
            source_keypoints,
            reference_keypoints,
            mutual,
            partial_mask
        )
    )

    correspondence_base64 = (
        correspondence_layers.get(
            "lines_points"
        )
    )

    # -----------------------------------------------------
    # MATCH RECORDS
    # -----------------------------------------------------

    matches_output = []

    source_points_original = []

    reference_points_original = []

    for i, match in enumerate(mutual):

        src_pt = np.array(
            source_keypoints[
                match.queryIdx
            ].pt,
            dtype=np.float32
        )

        ref_pt = np.array(
            reference_keypoints[
                match.trainIdx
            ].pt,
            dtype=np.float32
        )

        src_original = (
            src_pt /
            source_scale
        )

        ref_original = (
            ref_pt /
            reference_scale
        )

        source_points_original.append(
            src_original
        )

        reference_points_original.append(
            ref_original
        )

        matches_output.append(
            {
                "id": i + 1,

                "source": {
                    "x": float(
                        src_original[0]
                    ),
                    "y": float(
                        src_original[1]
                    )
                },

                "reference": {
                    "x": float(
                        ref_original[0]
                    ),
                    "y": float(
                        ref_original[1]
                    )
                },

                "descriptor_distance": float(
                    match.distance
                ),

                "ratio": None,

                "reprojection_error": None,

                "status": "unverified"
            }
        )

    processing_time = (
        perf_counter()
        - start_time
    )

    print()
    print(
        "================================================"
    )
    print(
        "EPHEMERIS PARTIAL RESULT"
    )
    print(
        "================================================"
    )

    print(
        "Status        : INSUFFICIENT CORRESPONDENCES"
    )

    print(
        "Reason        :",
        reason
    )

    print(
        "Ratio matches :",
        len(ratio)
    )

    print(
        "Mutual matches:",
        len(mutual)
    )

    print(
        "Inliers       : NOT ESTIMATED"
    )

    print(
        "Outliers      : NOT ESTIMATED"
    )

    print(
        "RMSE          : NOT ESTIMATED"
    )

    print(
        "Registered    : NOT AVAILABLE"
    )

    print(
        "Processing    :",
        round(
            processing_time,
            3
        ),
        "seconds"
    )

    print(
        "================================================"
    )

    return {

        "success": True,

        "result_status":
            "insufficient_correspondences",

        "result_message":
            "The images could not be registered reliably "
            "because too few mutual correspondences were found.",

        "result_detail":
            reason,

        "source": {

            "width": source_w,

            "height": source_h,

            "keypoints":
                len(source_keypoints)
        },

        "reference": {

            "width": reference_w,

            "height": reference_h,

            "keypoints":
                len(reference_keypoints)
        },

        "matching": {

            "ratio_matches":
                len(ratio),

            "mutual_matches":
                len(mutual),

            "inliers":
                None,

            "outliers":
                None,

            "inlier_ratio":
                None
        },

        "reprojection_error": {

            "mean": None,

            "median": None,

            "rmse": None,

            "max": None
        },

        "spatial_coverage":
            None,

        "quality_control": {

            "accepted":
                False,

            "checks": {

                "minimum_inliers":
                    False,

                "minimum_inlier_ratio":
                    False,

                "reprojection_rmse":
                    False,

                "spatial_coverage":
                    False
            },

            "reason":
                "Geometric transformation was not estimated."
        },

        "homography":
            None,

        "correspondence_image":
            correspondence_base64,

        "correspondence_image_description":
            "Available mutual correspondences. "
            "Green/red inlier classification is not available "
            "because geometric validation was not possible.",

        "correspondence_layers": {

            "lines_points":
                correspondence_layers.get(
                    "lines_points"
                ),

            "points":
                correspondence_layers.get(
                    "points"
                ),

            "inliers":
                None,

            "outliers":
                None
        },

        "correspondence_layer_description": {

            "lines_points":
                "Available mutual correspondences. "
                "These have not passed geometric validation.",

            "points":
                "Available mutual correspondence points only.",

            "inliers":
                "Not available because no geometric transformation was estimated.",

            "outliers":
                "Not available because no geometric transformation was estimated."
        },

        "registered_image":
            None,

        "registered_image_scale":
            None,

        "processing_scale": {

            "max_dimension":
                MAX_PROCESSING_DIM,

            "source_scale":
                source_scale,

            "reference_scale":
                reference_scale,

            "source_working_width":
                int(
                    source_working.shape[1]
                ),

            "source_working_height":
                int(
                    source_working.shape[0]
                ),

            "reference_working_width":
                int(
                    reference_working.shape[1]
                ),

            "reference_working_height":
                int(
                    reference_working.shape[0]
                )
        },

        "matches":
            matches_output,

        "processing_time":
            processing_time,

        "pipeline": [

            "PDS raster decoding",

            "Memory-safe image scaling",

            "Grayscale conversion",

            "CLAHE enhancement",

            "SIFT feature detection",

            "Lowe ratio test",

            "Mutual nearest-neighbour matching",

            "Insufficient-correspondence diagnostic",

            "Partial correspondence visualization",

            "SPICE geometry and metadata"
        ]
    }


# =========================================================
# MAIN PROCESSING PIPELINE
# =========================================================

def process_images(
    source_image,
    reference_image
):

    start_time = perf_counter()

    # -----------------------------------------------------
    # ORIGINAL IMAGE INFORMATION
    # -----------------------------------------------------

    source_h, source_w = (
        source_image.shape[:2]
    )

    reference_h, reference_w = (
        reference_image.shape[:2]
    )

    print()
    print(
        "================================================"
    )
    print(
        "EPHEMERIS IMAGE CORRESPONDENCE"
    )
    print(
        "================================================"
    )

    print(
        f"SOURCE IMAGE    : "
        f"{source_w} x {source_h}"
    )

    print(
        f"REFERENCE IMAGE : "
        f"{reference_w} x {reference_h}"
    )

    # -----------------------------------------------------
    # SAFE WORKING COPIES
    # -----------------------------------------------------

    source_working, source_scale = (
        create_processing_image(
            source_image
        )
    )

    reference_working, reference_scale = (
        create_processing_image(
            reference_image
        )
    )

    print()
    print(
        "EPHEMERIS PROCESSING SCALE"
    )

    print(
        f"Source working    : "
        f"{source_working.shape[1]} x "
        f"{source_working.shape[0]}"
    )

    print(
        f"Reference working : "
        f"{reference_working.shape[1]} x "
        f"{reference_working.shape[0]}"
    )

    print(
        f"Source scale      : "
        f"{source_scale}"
    )

    print(
        f"Reference scale   : "
        f"{reference_scale}"
    )

    # -----------------------------------------------------
    # GRAYSCALE
    # -----------------------------------------------------

    source_gray = prepare_gray(
        source_working
    )

    reference_gray = prepare_gray(
        reference_working
    )

    # -----------------------------------------------------
    # FEATURE DETECTION
    # -----------------------------------------------------

    print()
    print(
        "EPHEMERIS: detecting source features..."
    )

    source_keypoints, source_descriptors = (
        detect_features(
            source_gray
        )
    )

    print(
        "EPHEMERIS: detecting reference features..."
    )

    reference_keypoints, reference_descriptors = (
        detect_features(
            reference_gray
        )
    )

    print(
        "EPHEMERIS SOURCE KEYPOINTS:",
        len(source_keypoints)
    )

    print(
        "EPHEMERIS REFERENCE KEYPOINTS:",
        len(reference_keypoints)
    )

    if (
        source_descriptors is None
        or reference_descriptors is None
    ):

        # This is a true processing failure because
        # no correspondence information can be produced.

        raise ValueError(
            "Unable to compute feature descriptors "
            "for one or both images."
        )

    # -----------------------------------------------------
    # DESCRIPTOR MATCHING
    # -----------------------------------------------------

    print(
        "EPHEMERIS: descriptor matching..."
    )

    ratio = ratio_matches(
        source_descriptors,
        reference_descriptors
    )

    print(
        "EPHEMERIS RATIO MATCHES:",
        len(ratio)
    )

    mutual = mutual_matches(
        source_descriptors,
        reference_descriptors
    )

    print(
        "EPHEMERIS MUTUAL MATCHES:",
        len(mutual)
    )

    # =====================================================
    # IMPORTANT:
    #
    # DO NOT CRASH WHEN THERE ARE FEWER THAN 4 MATCHES.
    #
    # Return a scientifically honest partial result.
    # =====================================================

    if len(mutual) < 4:

        return build_partial_result(

            source_image,

            reference_image,

            source_working,

            reference_working,

            source_scale,

            reference_scale,

            source_keypoints,

            reference_keypoints,

            ratio,

            mutual,

            start_time,

            (
                f"Only {len(mutual)} mutual correspondences "
                f"were found. At least 4 are required "
                f"to estimate a projective transformation."
            )
        )

    # -----------------------------------------------------
    # WORKING-SCALE POINTS
    # -----------------------------------------------------

    source_points_working = np.float32([

        source_keypoints[
            m.queryIdx
        ].pt

        for m in mutual

    ])

    reference_points_working = np.float32([

        reference_keypoints[
            m.trainIdx
        ].pt

        for m in mutual

    ])

    # -----------------------------------------------------
    # MAGSAC / RANSAC
    # -----------------------------------------------------

    print(
        "EPHEMERIS: running MAGSAC/RANSAC..."
    )

    H_working, mask = (
        estimate_homography(
            source_points_working,
            reference_points_working
        )
    )

    # -----------------------------------------------------
    # HOMOGRAPHY FAILURE
    # -----------------------------------------------------

    if (
        H_working is None
        or mask is None
    ):

        return build_partial_result(

            source_image,

            reference_image,

            source_working,

            reference_working,

            source_scale,

            reference_scale,

            source_keypoints,

            reference_keypoints,

            ratio,

            mutual,

            start_time,

            (
                "Sufficient mutual correspondences were found, "
                "but a stable geometric transformation could "
                "not be estimated."
            )
        )

    mask = (
        mask
        .ravel()
        .astype(bool)
    )

    # -----------------------------------------------------
    # ORIGINAL COORDINATES
    # -----------------------------------------------------

    source_points_original = (
        source_points_working /
        source_scale
    )

    reference_points_original = (
        reference_points_working /
        reference_scale
    )

    # -----------------------------------------------------
    # ORIGINAL-SCALE HOMOGRAPHY
    # -----------------------------------------------------

    S_source = np.array(
        [
            [
                source_scale,
                0,
                0
            ],
            [
                0,
                source_scale,
                0
            ],
            [
                0,
                0,
                1
            ]
        ],
        dtype=np.float64
    )

    S_reference = np.array(
        [
            [
                reference_scale,
                0,
                0
            ],
            [
                0,
                reference_scale,
                0
            ],
            [
                0,
                0,
                1
            ]
        ],
        dtype=np.float64
    )

    try:

        H_original = (
            np.linalg.inv(
                S_reference
            )
            @ H_working
            @ S_source
        )

        H_original = (
            H_original /
            H_original[2, 2]
        )

    except Exception:

        H_original = H_working.copy()

    # -----------------------------------------------------
    # REPROJECTION ERROR
    # -----------------------------------------------------

    reprojection_errors = (
        calculate_reprojection_errors(
            source_points_original,
            reference_points_original,
            H_original
        )
    )

    # -----------------------------------------------------
    # MATCH RECORDS
    # -----------------------------------------------------

    matches_output = []

    for i, match in enumerate(mutual):

        status = (
            "inlier"
            if mask[i]
            else "outlier"
        )

        error = float(
            reprojection_errors[i]
        )

        matches_output.append(
            {
                "id": i + 1,

                "source": {
                    "x": float(
                        source_points_original[
                            i
                        ][0]
                    ),
                    "y": float(
                        source_points_original[
                            i
                        ][1]
                    )
                },

                "reference": {
                    "x": float(
                        reference_points_original[
                            i
                        ][0]
                    ),
                    "y": float(
                        reference_points_original[
                            i
                        ][1]
                    )
                },

                "descriptor_distance": float(
                    match.distance
                ),

                "ratio": None,

                "reprojection_error": error,

                "status": status
            }
        )

    # -----------------------------------------------------
    # INLIERS / OUTLIERS
    # -----------------------------------------------------

    inlier_errors = (
        reprojection_errors[mask]
        if np.any(mask)
        else np.array(
            [],
            dtype=np.float32
        )
    )

    inlier_count = int(
        np.sum(mask)
    )

    outlier_count = int(
        len(mask) -
        inlier_count
    )

    total_matches = len(mask)

    inlier_ratio = (
        inlier_count /
        float(total_matches)
        if total_matches > 0
        else 0.0
    )

    # -----------------------------------------------------
    # ERROR METRICS
    # -----------------------------------------------------

    if len(inlier_errors) > 0:

        mean_error = float(
            np.mean(
                inlier_errors
            )
        )

        median_error = float(
            np.median(
                inlier_errors
            )
        )

        rmse = float(
            np.sqrt(
                np.mean(
                    np.square(
                        inlier_errors
                    )
                )
            )
        )

        max_error = float(
            np.max(
                inlier_errors
            )
        )

    else:

        mean_error = None
        median_error = None
        rmse = None
        max_error = None

    # -----------------------------------------------------
    # SPATIAL COVERAGE
    # -----------------------------------------------------

    inlier_points_reference = (
        reference_points_original[
            mask
        ]
        if np.any(mask)
        else np.empty(
            (0, 2),
            dtype=np.float32
        )
    )

    spatial_coverage = (
        calculate_spatial_coverage(
            inlier_points_reference,
            reference_w,
            reference_h
        )
    )

    # -----------------------------------------------------
    # QUALITY CONTROL
    # -----------------------------------------------------

    checks = {

        "minimum_inliers":
            inlier_count >= 8,

        "minimum_inlier_ratio":
            inlier_ratio >= 0.25,

        "reprojection_rmse":
            (
                rmse is not None
                and rmse <= 3.0
            ),

        "spatial_coverage":
            spatial_coverage >= 0.10
    }

    accepted = all(
        checks.values()
    )

    # -----------------------------------------------------
    # RESULT STATUS
    # -----------------------------------------------------

    if accepted:

        result_status = "accepted"

        result_message = (
            "Reliable geometric correspondence and "
            "registration estimated."
        )

    else:

        result_status = "weak_match"

        result_message = (
            "Correspondences were detected, but the "
            "geometric quality-control criteria were not met."
        )

    # =====================================================
    # CORRESPONDENCE VISUALIZATION
    # =====================================================

    correspondence_layers = (
        create_correspondence_layers(
            source_working,
            reference_working,
            source_keypoints,
            reference_keypoints,
            mutual,
            mask
        )
    )

    correspondence_base64 = (
        correspondence_layers.get(
            "lines_points"
        )
    )

    # =====================================================
    # REGISTERED VISUALIZATION
    # =====================================================

    print()
    print(
        "EPHEMERIS: creating registered preview..."
    )

    registered_preview = (
        create_registered_preview(
            source_working,
            reference_working,
            H_working
        )
    )

    registered_base64 = encode_png(
        registered_preview
    )

    # -----------------------------------------------------
    # PROCESSING TIME
    # -----------------------------------------------------

    processing_time = (
        perf_counter()
        - start_time
    )

    # -----------------------------------------------------
    # TERMINAL SUMMARY
    # -----------------------------------------------------

    print()
    print(
        "================================================"
    )

    print(
        "EPHEMERIS MATCHING COMPLETE"
    )

    print(
        "================================================"
    )

    print(
        "Status        :",
        result_status
    )

    print(
        "Inliers       :",
        inlier_count
    )

    print(
        "Outliers      :",
        outlier_count
    )

    print(
        "Inlier ratio  :",
        round(
            inlier_ratio,
            4
        )
    )

    print(
        "RMSE          :",
        rmse
    )

    print(
        "Mean error    :",
        mean_error
    )

    print(
        "Median error  :",
        median_error
    )

    print(
        "Max error     :",
        max_error
    )

    print(
        "Coverage      :",
        round(
            spatial_coverage,
            4
        )
    )

    print(
        "Processing    :",
        round(
            processing_time,
            3
        ),
        "seconds"
    )

    print(
        "QC ACCEPTED   :",
        accepted
    )

    print(
        "Correspondence layers:"
    )

    for layer_name, layer_data in (
        correspondence_layers.items()
    ):

        print(
            f"  {layer_name:15s}:",
            "READY"
            if layer_data
            else "FAILED"
        )

    print(
        "Registered visualization:",
        "READY"
        if registered_base64
        else "FAILED"
    )

    print(
        "================================================"
    )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "success": True,

        "result_status":
            result_status,

        "result_message":
            result_message,

        "source": {

            "width": source_w,

            "height": source_h,

            "keypoints":
                len(source_keypoints)
        },

        "reference": {

            "width": reference_w,

            "height": reference_h,

            "keypoints":
                len(reference_keypoints)
        },

        "matching": {

            "ratio_matches":
                len(ratio),

            "mutual_matches":
                len(mutual),

            "inliers":
                inlier_count,

            "outliers":
                outlier_count,

            "inlier_ratio":
                inlier_ratio
        },

        "reprojection_error": {

            "mean":
                mean_error,

            "median":
                median_error,

            "rmse":
                rmse,

            "max":
                max_error
        },

        "spatial_coverage":
            spatial_coverage,

        "quality_control": {

            "accepted":
                accepted,

            "checks":
                checks
        },

        "homography":
            H_original.tolist(),

        "correspondence_image":
            correspondence_base64,

        "correspondence_image_description":
            "Source/reference feature correspondence visualization. "
            "Green = RANSAC/MAGSAC inlier. "
            "Red = RANSAC/MAGSAC outlier.",

        "correspondence_layers": {

            "lines_points":
                correspondence_layers.get(
                    "lines_points"
                ),

            "points":
                correspondence_layers.get(
                    "points"
                ),

            "inliers":
                correspondence_layers.get(
                    "inliers"
                ),

            "outliers":
                correspondence_layers.get(
                    "outliers"
                )
        },

        "correspondence_layer_description": {

            "lines_points":
                "All mutual correspondences with "
                "green inliers and red outliers.",

            "points":
                "Correspondence points only. "
                "Lines are removed.",

            "inliers":
                "Only RANSAC/MAGSAC inlier points.",

            "outliers":
                "Only RANSAC/MAGSAC outlier points."
        },

        "registered_image":
            registered_base64,

        "registered_image_scale": {

            "source_scale":
                source_scale,

            "reference_scale":
                reference_scale,

            "description":
                "Registered visualization generated "
                "at memory-safe working resolution."
        },

        "processing_scale": {

            "max_dimension":
                MAX_PROCESSING_DIM,

            "source_scale":
                source_scale,

            "reference_scale":
                reference_scale,

            "source_working_width":
                int(
                    source_working.shape[1]
                ),

            "source_working_height":
                int(
                    source_working.shape[0]
                ),

            "reference_working_width":
                int(
                    reference_working.shape[1]
                ),

            "reference_working_height":
                int(
                    reference_working.shape[0]
                )
        },

        "matches":
            matches_output,

        "processing_time":
            processing_time,

        "pipeline": [

            "PDS raster decoding",

            "Memory-safe image scaling",

            "Grayscale conversion",

            "CLAHE enhancement",

            "SIFT feature detection",

            "Lowe ratio test",

            "Mutual nearest-neighbour matching",

            "MAGSAC/RANSAC robust estimation",

            "Original-scale homography conversion",

            "Reprojection error analysis",

            "Spatial coverage analysis",

            "Interactive correspondence visualization",

            "Inlier/outlier correspondence visualization",

            "Registered visualization",

            "Quality-control decision"
        ]
    }

