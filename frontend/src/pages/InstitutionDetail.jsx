import React, { useCallback, useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getInstitution, getInstitutionMembership } from "../services/institutionService.js";
import { VerificationBadge } from "../components/VerificationBadge.jsx";
import { INSTITUTION_TYPE_LABELS } from "../components/InstitutionCard.jsx";
import { CapabilitiesSection } from "../components/CapabilitiesSection.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";

export function InstitutionDetail() {
  const { route } = useRouter();
  const { isAuthenticated } = useAuth();
  const institutionId = route.params.id;

  const [institution, setInstitution] = useState(null);
  const [membership, setMembership] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetails = useCallback(async () => {
    if (!institutionId) return;
    try {
      setLoading(true);
      setError(null);
      const [inst, mem] = await Promise.all([
        getInstitution(institutionId),
        isAuthenticated ? getInstitutionMembership(institutionId) : Promise.resolve({ is_member: false }),
      ]);
      setInstitution(inst);
      setMembership(mem);
    } catch (err) {
      setError(
        err.message ||
          "Could not retrieve this institution. It may not exist or the server is unavailable."
      );
      setInstitution(null);
    } finally {
      setLoading(false);
    }
  }, [institutionId, isAuthenticated]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const canEdit = membership?.is_member === true &&
    (membership?.role === "institution_admin" || membership?.role === "representative") &&
    membership?.membership_status === "active";

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading institution profile..." />
        </div>
      </div>
    );
  }

  if (error || !institution) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/institutions" className="back-link">
            ← Back to All Institutions
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Institution Not Found">
              <p style={{ marginBottom: "var(--space-3)" }}>
                {error || "We could not find the institution with the requested identifier."}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchDetails}>
                  Retry
                </button>
                <Link href="/institutions" className="btn btn-primary btn-sm">
                  Return to Institutions
                </Link>
              </div>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href="/institutions" className="back-link">
          ← Back to All Institutions
        </Link>

        <article className="card detail-card" aria-labelledby="institution-title">
          <div className="detail-header">
            <div className="detail-status-row">
              <span className="type-chip">
                {INSTITUTION_TYPE_LABELS[institution.institution_type] ??
                  institution.institution_type}
              </span>
              <VerificationBadge status={institution.verification_status} />
              <span className="detail-id" title="Institution UUID">
                ID: {institution.id}
              </span>
            </div>

            <h1 id="institution-title" className="detail-title">
              {institution.name}
            </h1>

            <div className="detail-meta-bar">
              <div className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <span><strong>Location:</strong> {institution.location}</span>
              </div>

              {institution.website && (
                <div className="detail-meta-item">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                  <a
                    href={institution.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--text-brand)" }}
                  >
                    {institution.website.replace(/^https?:\/\//, "")}
                  </a>
                </div>
              )}

              <div className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <span><strong>Registered:</strong> {formatDate(institution.created_at)}</span>
              </div>
            </div>
          </div>

          {institution.description && (
            <div className="detail-body">
              <h2 className="detail-section-heading">About</h2>
              <div className="detail-description-content">
                {institution.description.split("\n\n").map((para, idx) => (
                  <p key={idx}>{para}</p>
                ))}
              </div>
            </div>
          )}
        </article>

        {/* Domains */}
        {(institution.domain_labels?.length ?? 0) > 0 && (
          <section className="card" style={{ marginTop: "var(--space-6)", padding: "var(--space-6)" }} aria-labelledby="inst-domains-heading">
            <h2 id="inst-domains-heading" className="detail-section-heading" style={{ marginTop: 0 }}>
              Societal Domains of Work
            </h2>
            <p className="form-helper" style={{ marginBottom: "var(--space-4)" }}>
              Areas this institution can credibly contribute to, aligned with the
              Aikyra challenge taxonomy.
            </p>
            <div className="capability-items">
              {institution.domain_labels.map((ref) => (
                <span key={ref.key} className="domain-chip domain-chip-strong">
                  {ref.label}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Capabilities */}
        <section className="card" style={{ marginTop: "var(--space-6)", padding: "var(--space-6)" }} aria-labelledby="inst-capabilities-heading">
          <h2 id="inst-capabilities-heading" className="detail-section-heading" style={{ marginTop: 0 }}>
            Capabilities & Expertise
          </h2>
          <p className="form-helper" style={{ marginBottom: "var(--space-4)" }}>
            Self-declared by the institution — reviewed during verification before
            this profile participates in challenge matching.
          </p>
          <CapabilitiesSection capabilities={institution.capabilities} />
        </section>

        {/* Contact */}
        {(institution.contact_email || institution.website) && (
          <section className="card" style={{ marginTop: "var(--space-6)", padding: "var(--space-6)" }} aria-labelledby="inst-contact-heading">
            <h2 id="inst-contact-heading" className="detail-section-heading" style={{ marginTop: 0 }}>
              Contact
            </h2>
            <div className="capability-items">
              {institution.contact_email && (
                <a className="domain-chip" href={`mailto:${institution.contact_email}`}>
                  {institution.contact_email}
                </a>
              )}
            </div>
          </section>
        )}

        {/* Edit CTA - only shown for active institution_admin/representative */}
        {canEdit && (
          <div style={{ marginTop: "var(--space-6)", display: "flex", gap: "var(--space-3)" }}>
            <Link
              href={`/institutions/register?edit=${institution.id}`}
              className="btn btn-secondary"
            >
              Edit Profile & Capabilities
            </Link>
            <Link href="/challenges" className="btn btn-outline">
              Browse Community Challenges
            </Link>
          </div>
        )}
        {!canEdit && (
          <div style={{ marginTop: "var(--space-6)", display: "flex", gap: "var(--space-3)" }}>
            <Link href="/challenges" className="btn btn-outline">
              Browse Community Challenges
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}