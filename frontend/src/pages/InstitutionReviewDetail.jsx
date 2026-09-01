import React, { useCallback, useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getAdminInstitution, updateInstitutionVerification } from "../services/adminService.js";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

const INSTITUTION_TYPE_LABELS = {
  university: "University",
  college: "College",
  research_institute: "Research Institute",
  innovation_hub: "Innovation Hub",
};

const VERIFICATION_STATUS_META = {
  unverified: {
    label: "Unverified",
    className: "badge-status-draft",
    description: "Registered but not yet submitted for review by institution admin.",
  },
  pending_review: {
    label: "Pending Review",
    className: "badge-status-pending",
    description: "Submitted for platform review and awaiting decision.",
  },
  verified: {
    label: "Verified",
    className: "badge-status-open",
    description: "Verified platform institution in good standing.",
  },
  rejected: {
    label: "Rejected",
    className: "badge-status-closed",
    description: "Verification request was rejected by a reviewer.",
  },
  suspended: {
    label: "Suspended",
    className: "badge-status-cancelled",
    description: "Institution privileges are temporarily suspended.",
  },
};

const CAPABILITY_SECTION_LABELS = {
  departments: "Departments",
  disciplines: "Disciplines",
  expertise: "Expertise",
  research_areas: "Research Areas",
  technologies: "Technologies",
  facilities: "Facilities & Equipment",
  innovation_support: "Innovation Support",
  prototyping: "Prototyping",
  project_experience: "Project Experience",
  collaboration_modes: "Collaboration Modes",
};

const ACTION_CONFIG = {
  verify: {
    label: "Verify Institution",
    modalTitle: "Verify Institution?",
    modalDesc: "You are about to verify this institution. This will approve its institutional profile and grant verified status platform-wide.",
    confirmButtonText: "Confirm Verification",
    buttonClass: "btn-primary",
    isDestructive: false,
  },
  reject: {
    label: "Reject Institution",
    modalTitle: "Reject Verification Request?",
    modalDesc: "You are about to reject this institution's verification request. The institution administrator will need to update details and resubmit for review.",
    confirmButtonText: "Reject Institution",
    buttonClass: "btn-danger",
    isDestructive: true,
  },
  suspend: {
    label: "Suspend Institution",
    modalTitle: "Suspend Institution?",
    modalDesc: "You are about to suspend this verified institution. Its verified status and associated capabilities will be temporarily deactivated.",
    confirmButtonText: "Suspend Institution",
    buttonClass: "btn-danger",
    isDestructive: true,
  },
  reinstate: {
    label: "Reinstate Institution",
    modalTitle: "Reinstate Institution?",
    modalDesc: "You are about to reinstate this suspended institution. This will restore its verified status on the platform.",
    confirmButtonText: "Confirm Reinstatement",
    buttonClass: "btn-primary",
    isDestructive: false,
  },
};

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function InstitutionReviewDetail() {
  const { route } = useRouter();
  const { canReviewInstitutions } = useAuth();
  const institutionId = route.params.id;

  const [institution, setInstitution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Modal State
  const [modalAction, setModalAction] = useState(null); // "verify" | "reject" | "suspend" | "reinstate" | null
  const [modalNote, setModalNote] = useState("");
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState(null);

  const fetchInstitution = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAdminInstitution(institutionId);
      setInstitution(data);
    } catch (err) {
      setError(err.message || "Failed to load institution details.");
    } finally {
      setLoading(false);
    }
  }, [institutionId]);

  useEffect(() => {
    fetchInstitution();
  }, [fetchInstitution]);

  const openModal = (actionKey) => {
    setModalAction(actionKey);
    setModalNote("");
    setActionError(null);
  };

  const closeModal = () => {
    if (submittingAction) return;
    setModalAction(null);
    setModalNote("");
    setActionError(null);
  };

  const handleConfirmAction = async (e) => {
    e.preventDefault();
    if (!modalAction) return;

    try {
      setSubmittingAction(true);
      setActionError(null);
      await updateInstitutionVerification(institutionId, modalAction, modalNote);
      setSuccessMessage(
        `Institution status successfully updated via "${ACTION_CONFIG[modalAction]?.label}".`
      );
      closeModal();
      // Refresh institution data
      await fetchInstitution();
    } catch (err) {
      setActionError(err.message || "Failed to update institution verification status.");
    } finally {
      setSubmittingAction(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-page-loading" role="status" aria-live="polite">
        <LoadingSpinner />
        <p>Loading institution review...</p>
      </div>
    );
  }

  if (error || !institution) {
    return (
      <div className="admin-page-error" role="alert">
        <div className="admin-detail-header">
          <Link href="/admin/institutions" className="admin-back-link">
            ← Back to Institution Review
          </Link>
        </div>
        <Alert variant="danger">
          <strong>Error loading institution:</strong> {error || "Institution not found."}
        </Alert>
        <div style={{ marginTop: "var(--space-4)" }}>
          <Link href="/admin/institutions" className="btn btn-secondary">
            Return to Review Queue
          </Link>
        </div>
      </div>
    );
  }

  const statusMeta = VERIFICATION_STATUS_META[institution.verification_status] || {
    label: institution.verification_status,
    className: "badge-status-draft",
    description: "",
  };

  // Determine available actions based on backend state machine
  // UNVERIFIED -> SUBMIT_FOR_REVIEW (institution admin) -> PENDING_REVIEW
  // PENDING_REVIEW -> VERIFY/REJECT (platform reviewer) -> VERIFIED/REJECTED
  // REJECTED -> RESUBMIT (institution admin) -> PENDING_REVIEW
  // VERIFIED -> SUSPEND (platform reviewer) -> SUSPENDED
  // SUSPENDED -> REINSTATE (platform reviewer) -> VERIFIED
  const currentStatus = institution.verification_status;
  const canVerify = currentStatus === "pending_review";
  const canReject = currentStatus === "pending_review";
  const canSuspend = currentStatus === "verified";
  const canReinstate = currentStatus === "suspended";

  // Check if capability sections exist
  const capabilities = institution.capabilities || {};
  const hasCapabilities = Object.keys(capabilities).some(
    (key) => Array.isArray(capabilities[key]) && capabilities[key].length > 0
  );

  const activeModalConfig = modalAction ? ACTION_CONFIG[modalAction] : null;

  return (
    <div className="admin-detail-container">
      {/* Header with Navigation */}
      <div className="admin-detail-header">
        <div className="admin-detail-breadcrumbs">
          <Link href="/admin/institutions" className="admin-back-link">
            ← Back to Institution Review
          </Link>
        </div>
        <div className="admin-detail-title-row">
          <div>
            <div className="admin-detail-status-bar">
              <span className={`badge ${statusMeta.className}`}>
                {statusMeta.label}
              </span>
              <span className="type-chip">
                {INSTITUTION_TYPE_LABELS[institution.institution_type] ?? institution.institution_type}
              </span>
              <span className="admin-id-pill" title="Institution UUID">
                ID: {institution.id}
              </span>
            </div>
            <h1 className="admin-detail-title">{institution.name}</h1>
          </div>
        </div>
      </div>

      {successMessage && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          <Alert variant="success" onClose={() => setSuccessMessage(null)}>
            {successMessage}
          </Alert>
        </div>
      )}

      <div className="admin-detail-grid">
        {/* Administrative Action Panel */}
        <section className="admin-detail-section admin-decision-section" aria-labelledby="decision-heading">
          <div className="admin-decision-header">
            <div>
              <h2 id="decision-heading" className="admin-detail-section-title" style={{ marginBottom: "4px" }}>
                Review Decision
              </h2>
              <p className="admin-section-subtitle">
                Take administrative action on this institution according to the platform verification workflow.
              </p>
            </div>
            <div className="admin-decision-status-pill">
              <span className="admin-field-label">Current Status:</span>
              <span className={`badge ${statusMeta.className}`}>
                ● {statusMeta.label}
              </span>
            </div>
          </div>

          <div className="admin-decision-content">
            <div className="admin-decision-actions">
              {canVerify && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => openModal("verify")}
                  disabled={!canReviewInstitutions}
                >
                  Verify Institution
                </button>
              )}

              {canReject && (
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => openModal("reject")}
                  disabled={!canReviewInstitutions}
                >
                  Reject Institution
                </button>
              )}

              {canSuspend && (
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => openModal("suspend")}
                  disabled={!canReviewInstitutions}
                >
                  Suspend Institution
                </button>
              )}

              {canReinstate && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => openModal("reinstate")}
                  disabled={!canReviewInstitutions}
                >
                  Reinstate Institution
                </button>
              )}

              {currentStatus === "rejected" && !canVerify && (
                <div className="admin-note-box">
                  <p>
                    <strong>Institution Rejected:</strong> This institution's verification request was rejected. To review again, the institution administrator must update details and resubmit for review.
                  </p>
                </div>
              )}

              {currentStatus === "unverified" && (
                <div className="admin-note-box">
                  <p>
                    <strong>Awaiting Submission:</strong> This institution has not been submitted for review. The institution administrator must submit it for review before platform reviewers can take action.
                  </p>
                </div>
              )}
            </div>

            {statusMeta.description && (
              <p className="admin-decision-help-text">
                {statusMeta.description}
              </p>
            )}
          </div>
        </section>

        {/* Institution Information Card */}
        <section className="admin-detail-section" aria-labelledby="info-heading">
          <h2 id="info-heading" className="admin-detail-section-title">
            Institution Information
          </h2>

          <div className="admin-field-grid">
            <div className="admin-field-group">
              <span className="admin-field-label">Location</span>
              <div className="admin-field-value">{institution.location || "—"}</div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Institution Type</span>
              <div className="admin-field-value">
                {INSTITUTION_TYPE_LABELS[institution.institution_type] ?? institution.institution_type}
              </div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Registered On</span>
              <div className="admin-field-value">{formatDate(institution.created_at)}</div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Last Updated</span>
              <div className="admin-field-value">{formatDate(institution.updated_at)}</div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Website</span>
              <div className="admin-field-value">
                {institution.website ? (
                  <a
                    href={institution.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="admin-external-link"
                  >
                    {institution.website} ↗
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Contact Email</span>
              <div className="admin-field-value">
                {institution.contact_email ? (
                  <a href={`mailto:${institution.contact_email}`} className="admin-mail-link">
                    {institution.contact_email}
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>

          <div className="admin-field-group" style={{ marginTop: "var(--space-4)" }}>
            <span className="admin-field-label">Description</span>
            <div className="admin-field-value admin-description-box">
              {institution.description || "No description provided."}
            </div>
          </div>

          {/* Domains */}
          <div className="admin-field-group" style={{ marginTop: "var(--space-4)" }}>
            <span className="admin-field-label">Domains & Focus Areas</span>
            <div className="admin-tags-wrap">
              {institution.domain_labels && institution.domain_labels.length > 0 ? (
                institution.domain_labels.map((d) => (
                  <span key={d.key} className="tag-chip">
                    {d.label}
                  </span>
                ))
              ) : institution.domains && institution.domains.length > 0 ? (
                institution.domains.map((d) => (
                  <span key={d} className="tag-chip">
                    {d}
                  </span>
                ))
              ) : (
                <span className="text-muted">No domains specified</span>
              )}
            </div>
          </div>
        </section>

        {/* Capabilities & Profile Card (if available) */}
        {hasCapabilities && (
          <section className="admin-detail-section" aria-labelledby="capabilities-heading">
            <h2 id="capabilities-heading" className="admin-detail-section-title">
              Institutional Capabilities & Profile
            </h2>
            <div className="admin-capabilities-grid">
              {Object.entries(CAPABILITY_SECTION_LABELS).map(([key, label]) => {
                const items = capabilities[key];
                if (!Array.isArray(items) || items.length === 0) return null;
                return (
                  <div key={key} className="admin-capability-group">
                    <h3 className="admin-capability-label">{label}</h3>
                    <div className="admin-tags-wrap">
                      {items.map((item, idx) => (
                        <span key={idx} className="admin-capability-chip">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Verification History / Audit Metadata */}
        <section className="admin-detail-section" aria-labelledby="audit-heading">
          <h2 id="audit-heading" className="admin-detail-section-title">
            Verification Metadata
          </h2>
          <div className="admin-field-grid">
            <div className="admin-field-group">
              <span className="admin-field-label">Verification Status</span>
              <div className="admin-field-value">
                <span className={`badge ${statusMeta.className}`}>
                  {statusMeta.label}
                </span>
              </div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Verified At</span>
              <div className="admin-field-value">{formatDate(institution.verified_at)}</div>
            </div>

            <div className="admin-field-group">
              <span className="admin-field-label">Verified By (Reviewer ID)</span>
              <div className="admin-field-value monospace-value">
                {institution.verified_by || "—"}
              </div>
            </div>
          </div>

          {institution.verification_note && (
            <div className="admin-field-group" style={{ marginTop: "var(--space-4)" }}>
              <span className="admin-field-label">Reviewer Note</span>
              <div className="admin-note-display">
                {institution.verification_note}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Confirmation Modal */}
      {modalAction && activeModalConfig && (
        <div
          className="admin-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div className="admin-modal">
            <div className="admin-modal-header">
              <h3 id="modal-title" className="admin-modal-title">
                {activeModalConfig.modalTitle}
              </h3>
              <button
                type="button"
                className="admin-modal-close"
                onClick={closeModal}
                disabled={submittingAction}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleConfirmAction}>
              <div className="admin-modal-body">
                <p className="admin-modal-desc">
                  {activeModalConfig.modalDesc}
                </p>

                <div className="admin-modal-target-box">
                  <span className="admin-modal-target-label">Target Institution:</span>
                  <span className="admin-modal-target-name">{institution.name}</span>
                </div>

                {activeModalConfig.isDestructive && (
                  <div className="admin-modal-warning-box">
                    <strong>Warning:</strong> This is a moderating action. Please confirm that you want to proceed.
                  </div>
                )}

                {actionError && (
                  <div style={{ marginBottom: "var(--space-3)" }}>
                    <Alert variant="danger">{actionError}</Alert>
                  </div>
                )}

                <div className="form-group" style={{ marginTop: "var(--space-4)" }}>
                  <label htmlFor="modal-note-input" className="form-label">
                    Reviewer Note <span className="text-muted">(optional)</span>
                  </label>
                  <textarea
                    id="modal-note-input"
                    className="form-control"
                    rows={3}
                    placeholder="Provide context or reasons for this administrative action..."
                    value={modalNote}
                    onChange={(e) => setModalNote(e.target.value)}
                    disabled={submittingAction}
                  />
                  <span className="form-hint">
                    This note will be recorded alongside the verification decision.
                  </span>
                </div>
              </div>

              <div className="admin-modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeModal}
                  disabled={submittingAction}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`btn ${activeModalConfig.buttonClass}`}
                  disabled={submittingAction}
                >
                  {submittingAction ? (
                    <>
                      <LoadingSpinner size="sm" /> Processing...
                    </>
                  ) : (
                    activeModalConfig.confirmButtonText
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
