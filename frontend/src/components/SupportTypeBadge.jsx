import React from "react";

const SUPPORT_TYPE_MAP = {
  funding: { label: "Funding", className: "support-funding" },
  equipment: { label: "Equipment", className: "support-equipment" },
  mentorship: { label: "Mentorship", className: "support-mentorship" },
  pilot_support: { label: "Pilot Support", className: "support-pilot" },
};

export function SupportTypeBadge({ type }) {
  const config = SUPPORT_TYPE_MAP[type] || {
    label: type || "Support",
    className: "support-funding",
  };

  return (
    <span className={`support-type-badge ${config.className}`}>
      {config.label}
    </span>
  );
}

export const SUPPORT_TYPE_OPTIONS = Object.entries(SUPPORT_TYPE_MAP).map(
  ([value, { label }]) => ({ value, label })
);
