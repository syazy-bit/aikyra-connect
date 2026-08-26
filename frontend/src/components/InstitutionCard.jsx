import React from "react";
import { Link } from "../context/RouterContext.jsx";
import { VerificationBadge } from "./VerificationBadge.jsx";

/** Contract enum labels — mirrors the backend institution_type enum. */
export const INSTITUTION_TYPE_LABELS = {
  university: "University",
  college: "College",
  research_institute: "Research Institute",
  innovation_hub: "Innovation Hub",
};

export function InstitutionCard({ institution }) {
  if (!institution) return null;

  return (
    <article
      className="card card-interactive"
      aria-labelledby={`institution-title-${institution.id}`}
    >
      <Link
        href={`/institutions/${institution.id}`}
        className="card-header"
        aria-label={`View profile of ${institution.name}`}
      >
        <h3 id={`institution-title-${institution.id}`} className="card-title">
          {institution.name}
        </h3>
      </Link>

      <div className="card-dna-row">
        <span className="type-chip">
          {INSTITUTION_TYPE_LABELS[institution.institution_type] ??
            institution.institution_type}
        </span>
        <VerificationBadge status={institution.verification_status} />
      </div>

      {(institution.domain_labels?.length ?? 0) > 0 && (
        <div className="card-domains">
          {institution.domain_labels.map((ref) => (
            <span key={ref.key} className="domain-chip">
              {ref.label}
            </span>
          ))}
        </div>
      )}

      <div className="card-meta">
        <div className="meta-item" title="Location">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span>{institution.location}</span>
        </div>
      </div>
    </article>
  );
}
