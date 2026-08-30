import React, { useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { createChallenge, uploadChallengeImage } from "../services/challengeService.js";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { PhotoUpload } from "../components/PhotoUpload.jsx";

const TITLE_MAX_LENGTH = 200;
const DESC_MAX_LENGTH = 5000;
const LOCATION_MAX_LENGTH = 200;

export function ReportProblem() {
  const { navigate } = useRouter();
  const { isAuthenticated } = useAuth();

  // Form State
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    location: "",
  });

  // Optional public photo evidence. Uploaded separately AFTER the challenge
  // is created, because submissions are public but uploads are authenticated.
  const [photoFile, setPhotoFile] = useState(null);
  const [photoUploadError, setPhotoUploadError] = useState(null);

  // Validation State
  const [touched, setTouched] = useState({
    title: false,
    description: false,
    location: false,
  });

  const [errors, setErrors] = useState({});

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [submittedChallenge, setSubmittedChallenge] = useState(null);

  // Validate a single field
  const validateField = (field, value) => {
    const trimmed = (value || "").trim();

    if (field === "title") {
      if (!trimmed) return "Please tell us what the problem is.";
      if (trimmed.length > TITLE_MAX_LENGTH) {
        return `Title cannot exceed ${TITLE_MAX_LENGTH} characters.`;
      }
    }

    if (field === "description") {
      if (!trimmed) {
        return "Please describe what is happening and who is affected.";
      }
      if (trimmed.length > DESC_MAX_LENGTH) {
        return `Description cannot exceed ${DESC_MAX_LENGTH} characters.`;
      }
    }

    if (field === "location") {
      if (!trimmed) return "Please provide the location where this is occurring.";
      if (trimmed.length > LOCATION_MAX_LENGTH) {
        return `Location cannot exceed ${LOCATION_MAX_LENGTH} characters.`;
      }
    }

    return null;
  };

  // Run validation across all fields
  const validateForm = () => {
    const newErrors = {
      title: validateField("title", formData.title),
      description: validateField("description", formData.description),
      location: validateField("location", formData.location),
    };

    setErrors(newErrors);
    return !newErrors.title && !newErrors.description && !newErrors.location;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear error if touched
    if (touched[name]) {
      const errorMsg = validateField(name, value);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    const errorMsg = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: errorMsg }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError(null);

    // Mark all as touched
    setTouched({ title: true, description: true, location: true });

    if (!validateForm()) {
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        location: formData.location.trim(),
      };

      const result = await createChallenge(payload);

      if (photoFile) {
        try {
          const updated = await uploadChallengeImage(result.id, photoFile);
          setPhotoUploadError(null);
          navigate(`/challenges/${updated.id}`);
          return;
        } catch (photoErr) {
          // The problem was submitted but the photo could not be attached.
          // Never re-submit the challenge; surface the error and keep the ID.
          setPhotoUploadError(
            photoErr.message ||
              "Your problem was submitted, but your photo could not be attached."
          );
        }
      }

      setSubmittedChallenge(result);
    } catch (err) {
      setApiError(
        err.message ||
          "We could not submit your problem right now. Please verify your connection and try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleReportAnother = () => {
    setFormData({ title: "", description: "", location: "" });
    setTouched({ title: false, description: false, location: false });
    setErrors({});
    setApiError(null);
    setPhotoFile(null);
    setPhotoUploadError(null);
    setSubmittedChallenge(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // ==========================================================================
  // Success State (Meaningful Completion View)
  // ==========================================================================
  if (submittedChallenge) {
    return (
      <div className="report-page">
        <div className="container-narrow">
          <div className="card success-card" role="region" aria-labelledby="success-heading">
            <div className="success-icon-badge" aria-hidden="true">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>

            <h1 id="success-heading" className="success-title">
              Your problem has been heard.
            </h1>

            <p className="success-message">
              Thank you for bringing this to light. Your submission is now recorded in the
              Aikyra community challenge network and visible to researchers, students, and
              community problem solvers.
            </p>

            {photoUploadError && (
              <div style={{ maxWidth: "34rem", margin: "0 auto var(--space-6)" }}>
                <Alert type="warning" title="Your photo could not be attached">
                  {photoUploadError} Your written report was submitted successfully and its
                  reference has been preserved — no changes were made to your submission.
                </Alert>
              </div>
            )}

            <div className="submitted-summary">
              <div className="summary-row">
                <span className="summary-label">Problem:</span>
                <span className="summary-value">{submittedChallenge.title}</span>
              </div>
              <div className="summary-row">
                <span className="summary-label">Location:</span>
                <span className="summary-value">{submittedChallenge.location}</span>
              </div>
              <div className="summary-row">
                <span className="summary-label">Status:</span>
                <span className="summary-value" style={{ textTransform: "capitalize" }}>
                  {submittedChallenge.status || "Submitted"}
                </span>
              </div>
            </div>

            <div className="success-actions">
              <Link href={`/challenges/${submittedChallenge.id}`} className="btn btn-primary btn-lg">
                View Challenge Details
              </Link>
              <Link href="/challenges" className="btn btn-secondary">
                Explore Community Challenges
              </Link>
              <button
                type="button"
                onClick={handleReportAnother}
                className="btn btn-outline"
                style={{ marginTop: "var(--space-2)" }}
              >
                Report Another Problem
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // Form State
  // ==========================================================================
  return (
    <div className="report-page">
      <div className="container-narrow">
        <div className="form-header">
          <Link href="/challenges" className="back-link">
            ← Back to Challenges
          </Link>
          <span className="section-kicker">Citizen Problem Intake</span>
          <h1 className="form-page-title">
            What problem are you seeing in your community?
          </h1>
          <p className="form-page-subtitle">
            Tell us about a real issue affecting your area. Your submission gives university
            students, faculty researchers, and innovators a concrete challenge to solve.
          </p>
        </div>

        {apiError && (
          <Alert type="danger" title="Submission Issue">
            {apiError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate className="card report-form" aria-label="Report a Community Problem">
          {/* 1. Problem Title */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="problem-title" className="form-label">
                What is the problem? <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <span className={`char-counter ${formData.title.length > TITLE_MAX_LENGTH ? "over-limit" : formData.title.length > 180 ? "near-limit" : ""}`}>
                {formData.title.length}/{TITLE_MAX_LENGTH}
              </span>
            </div>
            <p id="title-helper" className="form-helper">
              A short, specific summary of the issue (e.g., "Contaminated drinking water in village borewells")
            </p>
            <input
              id="problem-title"
              name="title"
              type="text"
              className={`form-control ${touched.title && errors.title ? "has-error" : ""}`}
              placeholder="e.g. Broken drainage causing seasonal flooding across Ward 4"
              value={formData.title}
              onChange={handleChange}
              onBlur={handleBlur}
              disabled={submitting}
              maxLength={TITLE_MAX_LENGTH + 20}
              aria-describedby="title-helper title-error"
              aria-invalid={touched.title && !!errors.title}
              required
            />
            {touched.title && errors.title && (
              <div id="title-error" className="form-error-msg" role="alert">
                <span aria-hidden="true">⚠️</span> {errors.title}
              </div>
            )}
          </div>

          {/* 2. Problem Description */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="problem-description" className="form-label">
                What is happening, who is affected, and why does it matter? <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <span className={`char-counter ${formData.description.length > DESC_MAX_LENGTH ? "over-limit" : formData.description.length > 4800 ? "near-limit" : ""}`}>
                {formData.description.length}/{DESC_MAX_LENGTH}
              </span>
            </div>
            <p id="desc-helper" className="form-helper">
              Describe the ground reality: who is impacted (families, farmers, schoolchildren), how long this has occurred, and the daily consequences.
            </p>
            <textarea
              id="problem-description"
              name="description"
              className={`form-control ${touched.description && errors.description ? "has-error" : ""}`}
              placeholder="e.g. Over 350 farming households rely on 4 central borewells that dry up completely by February. Last season, half the standing pulse crop failed, forcing families to buy expensive water tankers..."
              rows={6}
              value={formData.description}
              onChange={handleChange}
              onBlur={handleBlur}
              disabled={submitting}
              maxLength={DESC_MAX_LENGTH + 50}
              aria-describedby="desc-helper desc-error"
              aria-invalid={touched.description && !!errors.description}
              required
            />
            {touched.description && errors.description && (
              <div id="desc-error" className="form-error-msg" role="alert">
                <span aria-hidden="true">⚠️</span> {errors.description}
              </div>
            )}
          </div>

          {/* 3. Location */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="problem-location" className="form-label">
                Where is this happening? <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <span className={`char-counter ${formData.location.length > LOCATION_MAX_LENGTH ? "over-limit" : ""}`}>
                {formData.location.length}/{LOCATION_MAX_LENGTH}
              </span>
            </div>
            <p id="loc-helper" className="form-helper">
              Village, neighborhood, district, or town name (e.g., "Anantapur District, Andhra Pradesh")
            </p>
            <input
              id="problem-location"
              name="location"
              type="text"
              className={`form-control ${touched.location && errors.location ? "has-error" : ""}`}
              placeholder="e.g. Tumakuru, Karnataka"
              value={formData.location}
              onChange={handleChange}
              onBlur={handleBlur}
              disabled={submitting}
              maxLength={LOCATION_MAX_LENGTH + 20}
              aria-describedby="loc-helper loc-error"
              aria-invalid={touched.location && !!errors.location}
              required
            />
            {touched.location && errors.location && (
              <div id="loc-error" className="form-error-msg" role="alert">
                <span aria-hidden="true">⚠️</span> {errors.location}
              </div>
            )}
          </div>

          {/* 4. Optional Photo Evidence (public, uploaded separately & authenticated) */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="photo-evidence" className="form-label">
                Photo Evidence <span className="form-label-optional">(optional)</span>
              </label>
            </div>
            <p id="photo-helper" className="form-helper">
              Attach one photo that shows the problem on the ground. Photos help
              researchers and students verify and understand your report.
            </p>
            <PhotoUpload
              id="photo-evidence"
              file={photoFile}
              onChange={(file) => {
                setPhotoFile(file);
                setPhotoUploadError(null);
              }}
              disabled={submitting}
              error={photoUploadError}
            />
            {!isAuthenticated && (
              <p className="form-helper form-helper-auth-note" id="photo-auth-helper">
                Attaching a photo requires you to be signed in. Your written report is
                published publicly either way.
              </p>
            )}
          </div>

          {/* Form Action */}
          <div style={{ marginTop: "var(--space-8)" }}>
            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Submitting your problem to Aikyra...</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                  <span>Submit Community Problem</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
