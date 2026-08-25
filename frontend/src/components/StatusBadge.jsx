import React from "react";

const STATUS_MAP = {
  submitted: {
    label: "Submitted",
    className: "status-submitted",
  },
  under_review: {
    label: "Under Review",
    className: "status-under_review",
  },
  validated: {
    label: "Validated",
    className: "status-validated",
  },
  rejected: {
    label: "Rejected",
    className: "status-rejected",
  },
};

export function StatusBadge({ status }) {
  const config = STATUS_MAP[status] || {
    label: status || "Unknown",
    className: "status-submitted",
  };

  return (
    <span
      className={`status-badge ${config.className}`}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      <span className="status-dot" aria-hidden="true" />
      {config.label}
    </span>
  );
}
