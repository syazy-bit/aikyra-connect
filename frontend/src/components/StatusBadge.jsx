import React from "react";

const STATUS_MAP = {
  draft: {
    label: "Draft",
    className: "status-draft",
  },
  withdrawn: {
    label: "Withdrawn",
    className: "status-withdrawn",
  },
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
  forming: {
    label: "Forming",
    className: "status-forming",
  },
  active: {
    label: "Active",
    className: "status-active",
  },
  archived: {
    label: "Archived",
    className: "status-archived",
  },
  invited: {
    label: "Invited",
    className: "status-invited",
  },
  removed: {
    label: "Removed",
    className: "status-removed",
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
