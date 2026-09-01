import React, { useCallback, useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getAdminChallenge, transitionChallengeStatus, validateChallengeDna, getChallengeAudit } from "../services/adminService.js";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";

const STATUS_TRANSITIONS = {
  submitted: ["under_review"],
  under_review: ["validated", "rejected"],
};

const URGENCY_LABELS = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function ProblemReviewDetail() {
  const { route, navigate } = useRouter();
  const { canReviewProblems } = useAuth();
  const challengeId = route.params.id;

  const [challenge, setChallenge] = useState(null);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transitionLoading, setTransitionLoading] = useState(false);
  const [validateLoading, setValidateLoading] = useState(false);
  const [transitionError, setTransitionError] = useState(null);
  const [validateError, setValidateError] = useState(null);
  const [validateForm, setValidateForm] = useState({
    primary_domain: "",
    urgency: "medium",
    validation_status: "validated",
    note: "",
  });

  useEffect(() => {
    let mounted = true;

    async function loadChallenge() {
      try {
        setLoading(true);
        setError(null);
        const [challengeData, auditData] = await Promise.all([
          getAdminChallenge(challengeId),
          getChallengeAudit(challengeId),
        ]);
        if (mounted) {
          setChallenge(challengeData);
          setAudit(auditData);
          // Pre-fill validation form
          if (challengeData.dna) {
            setValidateForm({
              primary_domain: challengeData.dna.primary_domain ?? "",
              urgency: challengeData.dna.urgency ?? "medium",
              validation_status: challengeData.dna.validation_status ?? "validated",
              note: "",
            });
          }
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load challenge.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadChallenge();

    return () => {
      mounted = false;
    };
  }, [challengeId]);

  const allowedNextStatuses = challenge ? STATUS_TRANSITIONS[challenge.status] ?? [] : [];

  const handleStatusTransition = async (newStatus) => {
    if (!allowedNextStatuses.includes(newStatus)) return;
    setTransitionLoading(true);
    setTransitionError(null);
    try {
      await transitionChallengeStatus(challengeId, {
        status: newStatus,
        note: `Transitioned to ${newStatus} via admin review`,
      });
      // Reload challenge
      const updated = await getAdminChallenge(challengeId);
      setChallenge(updated);
    } catch (err) {
      setTransitionError(err.message || "Failed to transition status.");
    } finally {
      setTransitionLoading(false);
    }
  };

  const handleValidateDna = async () => {
    setValidateLoading(true);
    setValidateError(null);
    try {
      await validateChallengeDna(challengeId, validateForm);
      // Reload challenge
      const updated = await getAdminChallenge(challengeId);
      setChallenge(updated);
      const auditData = await getChallengeAudit(challengeId);
      setAudit(auditData);
    } catch (err) {
      setValidateError(err.message || "Failed to validate DNA.");
    } finally {
      setValidateLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!canReviewProblems) {
    return (
      <div className="admin-page">
        <Alert type="warning" title="Access Denied">
          <p>You do not have the required platform capability to access Problem Review.</p>
        </Alert>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading-container">
          <LoadingSpinner size="lg" message="Loading challenge details..." />
        </div>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="admin-page">
        <Link href="/admin/problems" className="back-link">← Back to Problem Review</Link>
        <div className="card" style={{ marginTop: "var(--space-4)" }}>
          <Alert type="danger" title="Challenge Not Found">
            <p>{error || "We could not find the challenge with the requested identifier."}</p>
            <Link href="/admin/problems" className="btn btn-primary">Return to Problem Review</Link>
          </Alert>
        </div>
      </div>
    );
  }

  const dna = challenge.dna;

  return (
    <div className="admin-page">
      <Link href="/admin/problems" className="back-link">← Back to Problem Review</Link>

      <div className="admin-detail-header">
        <div>
          <h1 className="admin-detail-title">{challenge.title}</h1>
          <div className="admin-detail-meta">
            <span className={`status-badge ${challenge.status}`}>{challenge.status.replace("_", " ")}</span>
            <span className="admin-detail-id">ID: {challenge.id}</span>
            <span>Submitted: {formatDate(challenge.created_at)}</span>
          </div>
        </div>
        <div className="admin-detail-actions">
          {allowedNextStatuses.map((status) => (
            <button
              key={status}
              type="button"
              className={`btn btn-${status === "validated" ? "primary" : "outline"}`}
              onClick={() => handleStatusTransition(status)}
              disabled={transitionLoading}
            >
              {transitionLoading ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Transitioning...</span>
                </>
              ) : (
                `Mark as ${status.replace("_", " ")}`
              )}
            </button>
          ))}
        </div>
      </div>

      {transitionError && (
        <Alert type="danger" title="Transition Failed">
          <p>{transitionError}</p>
        </Alert>
      )}

      <div className="admin-detail-grid">
        <section className="admin-detail-section card">
          <h2 className="admin-detail-section-title">Original Problem</h2>
          <div className="admin-detail-field">
            <label>Description</label>
            <p>{challenge.description}</p>
          </div>
          <div className="admin-detail-field">
            <label>Location</label>
            <p>{challenge.location}</p>
          </div>
          {challenge.image_path && (
            <div className="admin-detail-field">
              <label>Evidence Image</label>
              <img src={`/api/challenges/${challenge.id}/image`} alt="Problem evidence" style={{ maxWidth: "100%", maxHeight: "300px", borderRadius: "var(--radius-md)" }} />
            </div>
          )}
          {(challenge.latitude && challenge.longitude) && (
            <div className="admin-detail-field">
              <label>Coordinates</label>
              <p>({challenge.latitude.toFixed(4)}, {challenge.longitude.toFixed(4)})</p>
            </div>
          )}
        </section>

        {dna && (
          <section className="admin-detail-section card">
            <h2 className="admin-detail-section-title">Problem DNA Analysis</h2>
            <div className="admin-dna-summary">
              <div className="dna-field">
                <label>Primary Domain</label>
                <span>{dna.primary_domain ?? "Not determined"}</span>
              </div>
              <div className="dna-field">
                <label>Secondary Domains</label>
                <span>{dna.secondary_domains?.length ? dna.secondary_domains.join(", ") : "—"}</span>
              </div>
              <div className="dna-field">
                <label>Urgency</label>
                <StatusBadge status={dna.urgency} />
              </div>
              <div className="dna-field">
                <label>Confidence</label>
                <span>{dna.confidence_score !== null ? (dna.confidence_score * 100).toFixed(0) + "%" : "—"}</span>
              </div>
              <div className="dna-field">
                <label>Validation Status</label>
                <span className={`dna-status-badge ${dna.validation_status}`}>
                  {dna.validation_status.replace("_", " ")}
                </span>
              </div>
              <div className="dna-field">
                <label>Validated By</label>
                <span>{dna.validated_by ? `User ${dna.validated_by}` : "Not validated"}</span>
              </div>
              <div className="dna-field">
                <label>Validated At</label>
                <span>{formatDate(dna.validated_at)}</span>
              </div>
            </div>

            <div className="dna-detail-full">
              <h3 className="dna-subsection-title">Full Analysis</h3>
              <div className="dna-full-fields">
                {dna.subdomain && (
                  <div className="dna-full-field">
                    <label>Subdomain</label>
                    <span>{dna.subdomain}</span>
                  </div>
                )}
                {dna.problem_type && (
                  <div className="dna-full-field">
                    <label>Problem Type</label>
                    <span>{dna.problem_type}</span>
                  </div>
                )}
                {dna.geographic_context && (
                  <div className="dna-full-field">
                    <label>Geographic Context</label>
                    <span>{dna.geographic_context}</span>
                  </div>
                )}
                <div className="dna-full-field">
                  <label>Affected Stakeholders</label>
                  <span>{dna.affected_stakeholders?.length ? dna.affected_stakeholders.join(", ") : "—"}</span>
                </div>
                <div className="dna-full-field">
                  <label>Keywords</label>
                  <span>{dna.keywords?.length ? dna.keywords.join(", ") : "—"}</span>
                </div>
                <div className="dna-full-field">
                  <label>Required Expertise</label>
                  <span>{dna.required_expertise?.length ? dna.required_expertise.join(", ") : "—"}</span>
                </div>
                <div className="dna-full-field">
                  <label>Potential Solution Areas</label>
                  <span>{dna.potential_solution_areas?.length ? dna.potential_solution_areas.join(", ") : "—"}</span>
                </div>
              </div>

              <div className="admin-dna-validation card" style={{ marginTop: "var(--space-6)" }}>
                <h3 className="dna-subsection-title">Human Validation</h3>
                <div className="dna-validation-form">
                  <div className="form-group">
                    <label htmlFor="primary_domain">Primary Domain</label>
                    <input
                      id="primary_domain"
                      type="text"
                      className="form-control"
                      value={validateForm.primary_domain}
                      onChange={(e) => setValidateForm({ ...validateForm, primary_domain: e.target.value })}
                      placeholder="e.g., water_sanitation"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="urgency">Urgency</label>
                    <select
                      id="urgency"
                      className="form-control"
                      value={validateForm.urgency}
                      onChange={(e) => setValidateForm({ ...validateForm, urgency: e.target.value })}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="validation_status">Validation Status</label>
                    <select
                      id="validation_status"
                      className="form-control"
                      value={validateForm.validation_status}
                      onChange={(e) => setValidateForm({ ...validateForm, validation_status: e.target.value })}
                    >
                      <option value="pending_validation">Pending Validation</option>
                      <option value="validated">Validated</option>
                      <option value="needs_review">Needs Review</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="note">Reviewer Note</label>
                    <textarea
                      id="note"
                      className="form-control"
                      rows={3}
                      value={validateForm.note}
                      onChange={(e) => setValidateForm({ ...validateForm, note: e.target.value })}
                      placeholder="Optional note about your validation decision..."
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleValidateDna}
                    disabled={validateLoading}
                  >
                    {validateLoading ? (
                      <>
                        <LoadingSpinner size="sm" message="" center={false} />
                        <span>Validating...</span>
                      </>
                    ) : (
                      "Validate DNA"
                    )}
                  </button>
                </div>
                {validateError && (
                  <Alert type="danger" title="Validation Failed" style={{ marginTop: "var(--space-4)" }}>
                    <p>{validateError}</p>
                  </Alert>
                )}
              </div>
            </div>
          </section>
        )}

        <section className="admin-detail-section card">
          <h2 className="admin-detail-section-title">Review History</h2>
          {audit.length === 0 ? (
            <p className="text-muted">No review actions recorded yet.</p>
          ) : (
            <div className="admin-audit-log">
              {audit.map((record) => (
                <div key={record.id} className="audit-entry">
                  <div className="audit-entry-header">
                    <span className="audit-action">{record.action.replace("_", " ")}</span>
                    <span className="audit-time">{formatDate(record.created_at)}</span>
                  </div>
                  <div className="audit-changes">
                    {record.previous_status && record.new_status && (
                      <span className="audit-change">
                        Status: <span className="audit-old">{record.previous_status}</span> → <span className="audit-new">{record.new_status}</span>
                      </span>
                    )}
                    {record.previous_dna_validation_status && record.new_dna_validation_status && (
                      <span className="audit-change">
                        DNA Validation: <span className="audit-old">{record.previous_dna_validation_status}</span> → <span className="audit-new">{record.new_dna_validation_status}</span>
                      </span>
                    )}
                    {record.note && (
                      <span className="audit-note">{record.note}</span>
                    )}
                  </div>
                  <div className="audit-reviewer">By: {record.reviewer_id}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}