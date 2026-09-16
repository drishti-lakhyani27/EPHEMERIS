
import React, { useEffect, useState } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";
const UPLOAD_URL = `${API_BASE}/upload`;


/* =========================================================
   FORMATTERS
========================================================= */

function formatNumber(value) {
  if (value === null || value === undefined) return "—";

  const number = Number(value);

  if (!Number.isFinite(number)) return "—";

  return Math.round(number).toLocaleString();
}


function formatDecimal(value) {
  if (value === null || value === undefined) return "—";

  const number = Number(value);

  if (!Number.isFinite(number)) return "—";

  return number.toFixed(3);
}


function formatPercent(value) {
  if (value === null || value === undefined) return "—";

  const number = Number(value);

  if (!Number.isFinite(number)) return "—";

  return `${(number * 100).toFixed(1)}%`;
}


/* =========================================================
   IMAGE PREVIEW
========================================================= */

function createPreview(file) {
  if (!file) return "";

  const extension = file.name.split(".").pop().toLowerCase();

  const previewable = [
    "png",
    "jpg",
    "jpeg",
    "webp",
    "bmp",
    "gif",
    "tif",
    "tiff"
  ];

  if (!previewable.includes(extension)) {
    return "";
  }

  return URL.createObjectURL(file);
}


/* =========================================================
   BASE64 IMAGE
========================================================= */

function toImageSrc(value) {
  if (!value) return "";

  return value.startsWith("data:")
    ? value
    : `data:image/png;base64,${value}`;
}


/* =========================================================
   METRIC
========================================================= */

function Metric({
  label,
  value,
  unit,
  emphasis = false
}) {
  return (
    <div className={`metric ${emphasis ? "emphasis" : ""}`}>

      <div className="metric-label">
        {label}
      </div>

      <div className="metric-value">

        {value}

        {unit && (
          <span className="metric-unit">
            {unit}
          </span>
        )}

      </div>

    </div>
  );
}


/* =========================================================
   UPLOAD BOX
========================================================= */

function UploadBox({
  title,
  file,
  preview,
  onSelect,
  onRemove,
  number
}) {
  return (
    <div className="upload-card">

      <div className="upload-card-header">

        <div>

          <span className="upload-number">
            {number}
          </span>

          <strong>
            {title}
          </strong>

        </div>


        {file && (

          <button
            type="button"
            className="remove-button"
            onClick={onRemove}
          >
            REMOVE
          </button>

        )}

      </div>


      <label
        className={`upload-preview ${
          preview ? "has-image" : ""
        }`}
      >

        {preview ? (

          <img
            src={preview}
            alt={title}
          />

        ) : (

          <>

            <div className="upload-plus">
              +
            </div>

            <div className="upload-main">
              SELECT LUNAR IMAGE
            </div>

            <div className="upload-sub">
              .IMG / .ZIP / PNG / JPG / TIFF
            </div>

          </>

        )}


        <input
          type="file"
          accept=".img,.zip,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff"
          onChange={onSelect}
          hidden
        />

      </label>


      {file && (

        <div className="file-name">
          {file.name}
        </div>

      )}

    </div>
  );
}


/* =========================================================
   CORRESPONDENCE VIEWER
========================================================= */

function CorrespondenceViewer({ result }) {

  const [viewMode, setViewMode] =
    useState("LINES_POINTS");


  const correspondence =
    result?.correspondence_image || null;


  /*
   * Future backend visualization layers.
   *
   * The backend can provide:
   *
   * correspondence_image
   * correspondence_points_image
   * correspondence_inliers_image
   * correspondence_outliers_image
   *
   * The viewer automatically uses them when available.
   */

  const layers =
    result?.correspondence_layers || {};


  const imageMap = {

    LINES_POINTS:
      layers.lines_points ||
      correspondence,

    POINTS:
      layers.points ||
      layers.points_only ||
      null,

    INLIERS:
      layers.inliers ||
      null,

    OUTLIERS:
      layers.outliers ||
      null

  };


  const selectedImage =
    imageMap[viewMode];


  const imageSrc =
    toImageSrc(selectedImage);


  if (!correspondence) {
    return null;
  }


  const matching =
    result.matching || {};


  const inliers =
    matching.inliers ??
    result.inliers ??
    0;


  const outliers =
    matching.outliers ??
    result.outliers ??
    0;


  const mutualMatches =
    matching.mutual_matches ??
    result.mutual_matches ??
    0;


  const viewLabels = {

    LINES_POINTS:
      "LINES + POINTS",

    POINTS:
      "POINTS ONLY",

    INLIERS:
      "INLIERS ONLY",

    OUTLIERS:
      "OUTLIERS ONLY"

  };


  return (

    <section className="panel">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="panel-heading">

        <div>

          <div className="section-number">
            02
          </div>

          <div>

            <h2>
              FEATURE CORRESPONDENCE
            </h2>

            <p>
              Geometric correspondence between source
              and reference observations.
            </p>

          </div>

        </div>


        <div className="result-badge">
          VISUALIZATION READY
        </div>

      </div>


      <div className="correspondence-viewer">

        {/* =================================================
            TOOLBAR
        ================================================= */}

        <div className="viewer-toolbar">

          <div className="viewer-title">

            <span className="status-dot" />

            CORRESPONDENCE MAP

          </div>


          <div className="viewer-controls">

            <button
              type="button"
              className={`control ${
                viewMode === "LINES_POINTS"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setViewMode("LINES_POINTS")
              }
            >
              LINES + POINTS
            </button>


            <button
              type="button"
              className={`control ${
                viewMode === "POINTS"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setViewMode("POINTS")
              }
            >
              POINTS
            </button>


            <button
              type="button"
              className={`control ${
                viewMode === "INLIERS"
                  ? "active inlier-control"
                  : ""
              }`}
              onClick={() =>
                setViewMode("INLIERS")
              }
            >
              INLIERS
            </button>


            <button
              type="button"
              className={`control ${
                viewMode === "OUTLIERS"
                  ? "active outlier-control"
                  : ""
              }`}
              onClick={() =>
                setViewMode("OUTLIERS")
              }
            >
              OUTLIERS
            </button>

          </div>

        </div>


        {/* =================================================
            IMAGE
        ================================================= */}

        <div className="correspondence-image-container">

          {imageSrc ? (

            <img
              src={imageSrc}
              alt={`Lunar correspondence — ${viewLabels[viewMode]}`}
              className="correspondence-image"
            />

          ) : (

            <div className="empty-image">

              {viewMode === "POINTS"
                ? "POINTS-ONLY LAYER WILL BE PROVIDED BY BACKEND"
                : viewMode === "INLIERS"
                ? "INLIER LAYER WILL BE PROVIDED BY BACKEND"
                : viewMode === "OUTLIERS"
                ? "OUTLIER LAYER WILL BE PROVIDED BY BACKEND"
                : "CORRESPONDENCE VISUALIZATION"}

            </div>

          )}

        </div>


        {/* =================================================
            CURRENT VIEW
        ================================================= */}

        <div
          className="correspondence-description"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "15px",
            flexWrap: "wrap"
          }}
        >

          <span>
            DISPLAY:{" "}

            <strong>
              {viewLabels[viewMode]}
            </strong>
          </span>


          <span>
            MUTUAL:{" "}

            <strong>
              {formatNumber(mutualMatches)}
            </strong>
          </span>


          <span>
            INLIERS:{" "}

            <strong>
              {formatNumber(inliers)}
            </strong>
          </span>


          <span>
            OUTLIERS:{" "}

            <strong>
              {formatNumber(outliers)}
            </strong>
          </span>

        </div>


        {/* =================================================
            LEGEND
        ================================================= */}

        <div className="legend">

          <span>

            <span className="legend-dot inlier" />

            INLIER

          </span>


          <span>

            <span className="legend-dot outlier" />

            OUTLIER

          </span>


          <span>

            <span className="legend-dot unknown" />

            UNCLASSIFIED

          </span>

        </div>


        {result.correspondence_image_description && (

          <div className="correspondence-description">

            {result.correspondence_image_description}

          </div>

        )}

      </div>

    </section>
  );
}


/* =========================================================
   RESULT SECTION
========================================================= */

function ResultSection({ result }) {

  if (!result) {
    return null;
  }


  const sourceData =
    result.source || {};

  const referenceData =
    result.reference || {};

  const matching =
    result.matching || {};

  const reprojection =
    result.reprojection_error || {};

  const quality =
    result.quality_control || {};


  const matches =
    Array.isArray(result.matches)
      ? result.matches
      : Array.isArray(matching.matches)
      ? matching.matches
      : [];


  /* =======================================================
     COUNTS
  ======================================================= */

  const sourceKeypoints =
    sourceData.keypoints ??
    result.source_keypoints ??
    0;


  const referenceKeypoints =
    referenceData.keypoints ??
    result.reference_keypoints ??
    0;


  const rawCandidates =
    matching.raw_candidates ??
    result.raw_candidates ??
    0;


  const ratioMatches =
    matching.ratio_matches ??
    result.ratio_matches ??
    0;


  const mutualMatches =
    matching.mutual_matches ??
    result.mutual_matches ??
    0;


  const inliers =
    matching.inliers ??
    result.inliers ??
    0;


  const outliers =
    matching.outliers ??
    result.outliers ??
    0;


  const inlierRatio =
    matching.inlier_ratio ??
    result.inlier_ratio ??
    0;


  /* =======================================================
     REGISTERED IMAGE
  ======================================================= */

  const registered =
    result.registration?.image ||
    result.registered_image_base64 ||
    null;


  const registeredImage =
    toImageSrc(registered);


  /* =======================================================
     QC
  ======================================================= */

  const qcAccepted =
    quality.accepted === true ||
    String(quality.decision || "")
      .toLowerCase()
      .includes("accept");


  const decisionText =
    quality.decision ||
    (qcAccepted
      ? "ACCEPTED"
      : "COMPUTED");


  const coverage =
    quality.spatial_coverage ??
    result.spatial_coverage ??
    result.coverage ??
    null;


  const processingTime =
    result.processing_time ??
    result.total_processing_time ??
    null;


  /* =======================================================
     DIMENSIONS
  ======================================================= */

  const sourceWidth =
    sourceData.width ??
    result.source_width ??
    null;


  const sourceHeight =
    sourceData.height ??
    result.source_height ??
    null;


  const referenceWidth =
    referenceData.width ??
    result.reference_width ??
    null;


  const referenceHeight =
    referenceData.height ??
    result.reference_height ??
    null;


  return (

    <>

      {/* ===================================================
          02 — CORRESPONDENCE
      =================================================== */}

      <CorrespondenceViewer
        result={result}
      />


      {/* ===================================================
          03 — RESULT SUMMARY
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              03
            </div>

            <div>

              <h2>
                CORRESPONDENCE RESULT
              </h2>

              <p>
                Final geometrically verified feature
                correspondences.
              </p>

            </div>

          </div>


          <div
            className={
              qcAccepted
                ? "decision accepted"
                : "decision"
            }
          >
            {String(decisionText).toUpperCase()}
          </div>

        </div>


        <div className="metrics-grid">

          <Metric
            label="MUTUAL MATCHES"
            value={formatNumber(mutualMatches)}
          />


          <Metric
            label="RANSAC INLIERS"
            value={formatNumber(inliers)}
            emphasis
          />


          <Metric
            label="OUTLIERS"
            value={formatNumber(outliers)}
          />


          <Metric
            label="INLIER RATIO"
            value={formatPercent(inlierRatio)}
            emphasis
          />

        </div>

      </section>


      {/* ===================================================
          04 — MATCHING PIPELINE
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              04
            </div>

            <div>

              <h2>
                MATCHING PIPELINE
              </h2>

              <p>
                Feature extraction, descriptor filtering
                and robust geometric verification.
              </p>

            </div>

          </div>

        </div>


        <div className="metrics-grid">

          <Metric
            label="SOURCE KEYPOINTS"
            value={formatNumber(sourceKeypoints)}
          />


          <Metric
            label="REFERENCE KEYPOINTS"
            value={formatNumber(referenceKeypoints)}
          />


          <Metric
            label="RAW CANDIDATES"
            value={formatNumber(rawCandidates)}
          />


          <Metric
            label="RATIO-TEST MATCHES"
            value={formatNumber(ratioMatches)}
          />


          <Metric
            label="MUTUAL MATCHES"
            value={formatNumber(mutualMatches)}
          />


          <Metric
            label="RANSAC INLIERS"
            value={formatNumber(inliers)}
            emphasis
          />


          <Metric
            label="OUTLIERS"
            value={formatNumber(outliers)}
          />


          <Metric
            label="INLIER RATIO"
            value={formatPercent(inlierRatio)}
            emphasis
          />

        </div>

      </section>


      {/* ===================================================
          05 — GEOMETRIC ACCURACY
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              05
            </div>

            <div>

              <h2>
                GEOMETRIC ACCURACY
              </h2>

              <p>
                Reprojection statistics after robust
                transformation estimation.
              </p>

            </div>

          </div>


          <div
            className={
              qcAccepted
                ? "decision accepted"
                : "decision"
            }
          >
            {String(decisionText).toUpperCase()}
          </div>

        </div>


        <div className="metrics-grid">

          <Metric
            label="MEAN ERROR"
            value={formatDecimal(
              reprojection.mean
            )}
            unit="px"
          />


          <Metric
            label="MEDIAN ERROR"
            value={formatDecimal(
              reprojection.median
            )}
            unit="px"
          />


          <Metric
            label="RMSE"
            value={formatDecimal(
              reprojection.rmse
            )}
            unit="px"
            emphasis
          />


          <Metric
            label="MAX ERROR"
            value={formatDecimal(
              reprojection.max
            )}
            unit="px"
          />

        </div>


        <div className="metrics-grid">

          {coverage !== null && (

            <Metric
              label="SPATIAL COVERAGE"
              value={formatPercent(
                coverage
              )}
            />

          )}


          {processingTime !== null && (

            <Metric
              label="CV PROCESSING TIME"
              value={formatDecimal(
                processingTime
              )}
              unit="s"
            />

          )}

        </div>

      </section>


      {/* ===================================================
          06 — IMAGE GEOMETRY
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              06
            </div>

            <div>

              <h2>
                IMAGE GEOMETRY
              </h2>

              <p>
                Original observation dimensions and
                processing-scale information.
              </p>

            </div>

          </div>

        </div>


        <div className="metrics-grid">

          <Metric
            label="SOURCE WIDTH"
            value={formatNumber(sourceWidth)}
            unit="px"
          />


          <Metric
            label="SOURCE HEIGHT"
            value={formatNumber(sourceHeight)}
            unit="px"
          />


          <Metric
            label="REFERENCE WIDTH"
            value={formatNumber(referenceWidth)}
            unit="px"
          />


          <Metric
            label="REFERENCE HEIGHT"
            value={formatNumber(referenceHeight)}
            unit="px"
          />

        </div>

      </section>


      {/* ===================================================
          07 — MATCH RECORDS
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              07
            </div>

            <div>

              <h2>
                MATCH RECORDS
              </h2>

              <p>
                Individual source/reference feature
                correspondences returned by the backend.
              </p>

            </div>

          </div>

        </div>


        <div className="match-table-wrapper">

          {matches.length === 0 ? (

            <div className="empty-result">

              Individual match records are not included
              in this backend response.

            </div>

          ) : (

            <table className="match-table">

              <thead>

                <tr>

                  <th>ID</th>
                  <th>SOURCE X</th>
                  <th>SOURCE Y</th>
                  <th>REFERENCE X</th>
                  <th>REFERENCE Y</th>
                  <th>DISTANCE</th>
                  <th>RATIO</th>
                  <th>ERROR</th>
                  <th>STATUS</th>

                </tr>

              </thead>


              <tbody>

                {matches
                  .slice(0, 100)
                  .map((match, index) => {

                    const source =
                      match.source || {};

                    const reference =
                      match.reference || {};

                    const status =
                      String(
                        match.status ||
                        "unknown"
                      ).toLowerCase();


                    return (

                      <tr
                        key={
                          match.id ||
                          index
                        }
                      >

                        <td>
                          {match.id ||
                            index + 1}
                        </td>


                        <td>
                          {formatDecimal(
                            source.x
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            source.y
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            reference.x
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            reference.y
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            match.descriptor_distance
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            match.ratio
                          )}
                        </td>


                        <td>
                          {formatDecimal(
                            match.reprojection_error
                          )}
                        </td>


                        <td>

                          <span
                            className={
                              status === "inlier"
                                ? "match-inlier"
                                : status === "outlier"
                                ? "match-outlier"
                                : "match-unknown"
                            }
                          >
                            {status.toUpperCase()}
                          </span>

                        </td>

                      </tr>

                    );

                  })}

              </tbody>

            </table>

          )}

        </div>


        {matches.length > 100 && (

          <div className="table-note">

            Showing first 100 of{" "}
            {matches.length.toLocaleString()}{" "}
            matches.

          </div>

        )}

      </section>


      {/* ===================================================
          08 — REGISTERED IMAGE
      =================================================== */}

      {registeredImage && (

        <section className="panel">

          <div className="panel-heading">

            <div>

              <div className="section-number">
                08
              </div>

              <div>

                <h2>
                  REGISTERED IMAGE
                </h2>

                <p>
                  Source image transformed into the
                  reference coordinate system.
                </p>

              </div>

            </div>


            <div className="result-badge">
              REGISTRATION COMPLETE
            </div>

          </div>


          <div className="registered-container">

            <img
              src={registeredImage}
              alt="Registered lunar output"
            />

          </div>

        </section>

      )}


      {/* ===================================================
          09 — SPICE
      =================================================== */}

      {result.spice && (

        <section className="panel">

          <div className="panel-heading">

            <div>

              <div className="section-number">
                09
              </div>

              <div>

                <h2>
                  SPICE GEOMETRY
                </h2>

                <p>
                  Observation metadata derived from
                  planetary SPICE kernels.
                </p>

              </div>

            </div>


            <div className="result-badge">

              {result.spice.kernels_loaded
                ? `${result.spice.kernels_loaded} KERNELS`
                : "AVAILABLE"}

            </div>

          </div>


          <div className="spice-result">

            <pre>

              {JSON.stringify(
                result.spice,
                null,
                2
              )}

            </pre>

          </div>

        </section>

      )}


      {/* ===================================================
          10 — PROCESSING PIPELINE
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              10
            </div>

            <div>

              <h2>
                PROCESSING PIPELINE
              </h2>

              <p>
                EPHEMERIS stages executed for this
                observation pair.
              </p>

            </div>

          </div>

        </div>


        <div className="pipeline">

          <span>
            PDS / IMAGE LOAD
          </span>

          <b>→</b>

          <span>
            SIFT FEATURES
          </span>

          <b>→</b>

          <span>
            DESCRIPTOR MATCHING
          </span>

          <b>→</b>

          <span>
            RATIO + MUTUAL FILTER
          </span>

          <b>→</b>

          <span>
            MAGSAC / RANSAC
          </span>

          <b>→</b>

          <span>
            REPROJECTION QC
          </span>

          <b>→</b>

          <span>
            REGISTRATION
          </span>

        </div>

      </section>


      {/* ===================================================
          11 — OBSERVATION INFORMATION
      =================================================== */}

      <section className="panel">

        <div className="panel-heading">

          <div>

            <div className="section-number">
              11
            </div>

            <div>

              <h2>
                OBSERVATION INFORMATION
              </h2>

              <p>
                Source, reference and backend processing
                information.
              </p>

            </div>

          </div>

        </div>


        <div className="metrics-grid">

          <Metric
            label="SOURCE FORMAT"
            value={
              result.source?.format ||
              "—"
            }
          />


          <Metric
            label="REFERENCE FORMAT"
            value={
              result.reference?.format ||
              "—"
            }
          />


          <Metric
            label="PIPELINE STATUS"
            value={
              String(
                result.pipeline_status ||
                "—"
              ).toUpperCase()
            }
          />


          <Metric
            label="TOTAL PROCESSING TIME"
            value={formatDecimal(
              result.total_processing_time
            )}
            unit="s"
          />

        </div>


        {result.backend && (

          <div className="pipeline">

            <span>
              {result.backend.service ||
                "EPHEMERIS"}
            </span>

            <span>
              {result.backend.cv_engine ||
                "SIFT + MAGSAC/RANSAC"}
            </span>

            <span>
              {result.backend.processing_mode ||
                "MEMORY-SAFE"}
            </span>

            <span>
              DEEP LEARNING:{" "}
              {result.backend.deep_learning
                ? "YES"
                : "NO"}
            </span>

          </div>

        )}

      </section>

    </>
  );
}


/* =========================================================
   MAIN APP
========================================================= */

export default function App() {

  const [sourceFile, setSourceFile] =
    useState(null);

  const [referenceFile, setReferenceFile] =
    useState(null);


  const [sourcePreview, setSourcePreview] =
    useState("");

  const [referencePreview, setReferencePreview] =
    useState("");


  const [result, setResult] =
    useState(null);


  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  const [elapsed, setElapsed] =
    useState(0);


  /* =======================================================
     CLEANUP PREVIEW URLS
  ======================================================= */

  useEffect(() => {

    return () => {

      if (sourcePreview) {
        URL.revokeObjectURL(
          sourcePreview
        );
      }

      if (referencePreview) {
        URL.revokeObjectURL(
          referencePreview
        );
      }

    };

  }, [
    sourcePreview,
    referencePreview
  ]);


  /* =======================================================
     SOURCE
  ======================================================= */

  function handleSource(event) {

    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }


    if (sourcePreview) {

      URL.revokeObjectURL(
        sourcePreview
      );

    }


    setSourceFile(file);

    setSourcePreview(
      createPreview(file)
    );

    setResult(null);
    setError("");

  }


  /* =======================================================
     REFERENCE
  ======================================================= */

  function handleReference(event) {

    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }


    if (referencePreview) {

      URL.revokeObjectURL(
        referencePreview
      );

    }


    setReferenceFile(file);

    setReferencePreview(
      createPreview(file)
    );

    setResult(null);
    setError("");

  }


  /* =======================================================
     REMOVE SOURCE
  ======================================================= */

  function removeSource() {

    if (sourcePreview) {

      URL.revokeObjectURL(
        sourcePreview
      );

    }

    setSourceFile(null);
    setSourcePreview("");

    setResult(null);
    setError("");

  }


  /* =======================================================
     REMOVE REFERENCE
  ======================================================= */

  function removeReference() {

    if (referencePreview) {

      URL.revokeObjectURL(
        referencePreview
      );

    }

    setReferenceFile(null);
    setReferencePreview("");

    setResult(null);
    setError("");

  }


  /* =======================================================
     FIND CORRESPONDENCES
  ======================================================= */

  async function findCorrespondences() {

    if (
      !sourceFile ||
      !referenceFile
    ) {

      setError(
        "Please select both source and reference files."
      );

      return;

    }


    setLoading(true);
    setError("");
    setResult(null);
    setElapsed(0);


    const start =
      performance.now();


    const timer =
      window.setInterval(() => {

        setElapsed(
          (performance.now() - start) /
          1000
        );

      }, 100);


    try {

      const formData =
        new FormData();


      formData.append(
        "source",
        sourceFile,
        sourceFile.name
      );


      formData.append(
        "reference",
        referenceFile,
        referenceFile.name
      );


      const response =
        await fetch(
          UPLOAD_URL,
          {
            method: "POST",
            body: formData
          }
        );


      const text =
        await response.text();


      let data;


      try {

        data =
          JSON.parse(text);

      } catch {

        throw new Error(
          `Backend returned invalid JSON. HTTP ${response.status}`
        );

      }


      if (!response.ok) {

        throw new Error(
          data.detail ||
          data.error ||
          `Backend returned HTTP ${response.status}`
        );

      }


      if (
        data.success === false ||
        data.pipeline_status === "failed"
      ) {

        throw new Error(
          data.error ||
          data.message ||
          "EPHEMERIS processing failed."
        );

      }


      setResult(data);

    } catch (err) {

      console.error(
        "EPHEMERIS ERROR:",
        err
      );


      setError(
        err?.message ||
        "Could not connect to the backend."
      );

    } finally {

      window.clearInterval(
        timer
      );


      setElapsed(
        (performance.now() - start) /
        1000
      );


      setLoading(false);

    }

  }


  /* =======================================================
     UI
  ======================================================= */

  return (

    <div className="app">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="header">

        <div className="brand">

          <div className="brand-name">
            EPHEMERIS
          </div>

          <div className="brand-subtitle">
            LUNAR IMAGE CORRESPONDENCE ANALYSIS
          </div>

        </div>


        <div className="astrum">

          MADE BY{" "}

          <strong>
            ASTRUM
          </strong>

        </div>

      </header>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="main">

        {/* ===============================================
            TITLE
        =============================================== */}

        <section className="title-section">

          <div className="eyebrow">
            CHANDRAYAAN-2 · PS 26166 · SPACE TECHNOLOGY
          </div>


          <h1>

            Multi-Modal Lunar Image

            <br />

            <span>
              Correspondence
            </span>

          </h1>


          <p>
            Real lunar imagery, geometric matching
            and registration analysis.
          </p>

        </section>


        {/* ===============================================
            INPUT OBSERVATIONS
        =============================================== */}

        <section className="panel">

          <div className="panel-heading">

            <div>

              <div className="section-number">
                01
              </div>

              <div>

                <h2>
                  INPUT OBSERVATIONS
                </h2>

                <p>
                  Upload the source and reference observations.
                </p>

              </div>

            </div>

          </div>


          <div className="upload-grid">

            <UploadBox
              number="01"
              title="SOURCE IMAGE"
              file={sourceFile}
              preview={sourcePreview}
              onSelect={handleSource}
              onRemove={removeSource}
            />


            <div className="upload-arrow">
              →
            </div>


            <UploadBox
              number="02"
              title="REFERENCE IMAGE"
              file={referenceFile}
              preview={referencePreview}
              onSelect={handleReference}
              onRemove={removeReference}
            />

          </div>


          <button
            type="button"
            className="process-button"
            disabled={
              loading ||
              !sourceFile ||
              !referenceFile
            }
            onClick={
              findCorrespondences
            }
          >

            {loading
              ? `PROCESSING... ${elapsed.toFixed(1)} s`
              : "FIND CORRESPONDENCES →"}

          </button>


          {error && (

            <div className="error-box">

              <strong>
                PROCESSING ERROR
              </strong>

              <span>
                {error}
              </span>

              <small>
                Open the browser console with F12
                for detailed logs.
              </small>

            </div>

          )}

        </section>


        {/* ===============================================
            RESULTS
        =============================================== */}

        <ResultSection
          result={result}
        />

      </main>


      {/* =================================================
          FOOTER
      ================================================= */}

      <footer className="footer">

        <div>
          EPHEMERIS · ASTRUM
        </div>

        <div>
          REAL LUNAR IMAGE ANALYSIS
        </div>

      </footer>

    </div>

  );
}

