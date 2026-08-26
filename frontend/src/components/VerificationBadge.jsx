import React from "react";

const VERIFICATION_MAP = {
  unverified: {
    label: "Unverified",
    className: "verification-badge-unverified",
    title:
      "This profile is human-entered and awaiting review by Aikyra. Verified institutions only participate in future matching.",
  },
  verified: {
    label: "Verified",
    className: "verification-badge-verified",
    title: "Reviewed and confirmed by Aikyra.",
  },
  rejected: {
    label: "Rejected",
    className: "verification-badge-rejected",
    title: "This registration did not pass review.",
  },
  suspended: {
    label: "Suspended",
    className: "verification-badge-suspended",
    title: "This institution is temporarily suspended.",
  },
};

export function VerificationBadge({ status }) {
  const config = VERIFICATION_MAP[status] || VERIFICATION_MAP.unverified;
  return (
    <span
      className={`verification-badge ${config.className}`}
      title={config.title}
      role="status"
      aria-label={`Verification: ${config.label}`}
    >
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
      {config.label}
    </span>
  );
}
