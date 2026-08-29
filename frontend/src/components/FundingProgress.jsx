import React from "react";
import { Link } from "../context/RouterContext.jsx";

/**
 * Format an integer minor-unit amount (paise) as a currency string.
 * The conversion happens for display only — the server's integer minor units
 * are always the canonical representation.
 */
function formatMoney(minor, currency = "INR") {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(minor / 100);
  } catch {
    return `${minor} ${currency}`;
  }
}

/** Percent label (1 decimal where needed) derived from server basis points. */
function percentLabel(progressBp) {
  return (progressBp / 100).toLocaleString("en-IN", {
    maximumFractionDigits: 1,
  });
}

const STATUS_TEXT = {
  OPEN: "Funding open",
  FULLY_FUNDED: "Funding goal reached",
  CLOSED: "Funding completed",
};

/**
 * Public funding bar for one approved solution.
 *
 * Renders nothing when `funding` is null (no verified campaign): callers hide
 * the module rather than show a fabricated "₹0 raised". Every number comes
 * verbatim from the server-computed summary — this component never totals,
 * never calculates percentages from raw client data, and never exposes
 * individual contributions or supporter identities.
 */
export function FundingProgress({ funding, showSupportLink = false, compact = false }) {
  if (!funding) return null;

  const { project_id: projectId, status } = funding;
  const isOpen = status === "OPEN";
  // Screen readers get a 0-100 value; the server's basis points stay untouched.
  const ariaPercent = Math.round(funding.progress_bp / 100);
  const statusLabel = STATUS_TEXT[status] ?? status;

  return (
    <div className="funding-block" aria-label="Community funding">
      <div className="funding-head">
        <span className={`funding-status funding-status--${status.toLowerCase()}`}>
          {statusLabel}
        </span>
        <span className="funding-percent" aria-hidden="true">
          {percentLabel(funding.progress_bp)}%
        </span>
      </div>

      <div
        className="funding-bar"
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={ariaPercent}
        aria-label={`${statusLabel} for this solution`}
      >
        <span
          className="funding-fill"
          style={{ width: `${Math.min(100, ariaPercent)}%` }}
        />
      </div>

      <div className="funding-stats">
        <span className="funding-amount">
          <strong>{formatMoney(funding.raised_minor, funding.currency)}</strong>
          {" raised of "}
          {formatMoney(funding.goal_minor, funding.currency)}
        </span>
        <span className="funding-supporters">
          {funding.supporter_count === 1
            ? "1 supporter"
            : `${funding.supporter_count} supporters`}
        </span>
      </div>

      {showSupportLink && isOpen && (
        <Link
          href={`/projects/${projectId}/funding`}
          className={`btn ${
            compact ? "btn-secondary" : "btn-primary"
          } btn-sm funding-cta`}
        >
          Support this solution
        </Link>
      )}
    </div>
  );
}