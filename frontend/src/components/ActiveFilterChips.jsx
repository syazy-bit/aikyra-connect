import React from "react";

const URGENCY_LABELS = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };

/**
 * Active filter chips — every applied filter is visible and individually
 * removable so users always understand why results changed.
 */
export function ActiveFilterChips({ selected, onRemoveDomain, onRemoveUrgency, onClearLocation, onRemoveSearch, onClearAll, taxonomy }) {
  const domainLabel = (key) =>
    taxonomy?.domains?.find((d) => d.key === key)?.label ?? key;

  const chips = [
    ...selected.domains.map((key) => ({
      key: `domain-${key}`,
      label: domainLabel(key),
      group: "Problem area",
      onRemove: () => onRemoveDomain(key),
    })),
    ...selected.urgencies.map((level) => ({
      key: `urgency-${level}`,
      label: `${URGENCY_LABELS[level] ?? level} urgency`,
      group: "Urgency",
      onRemove: () => onRemoveUrgency(level),
    })),
    ...(selected.location
      ? [{ key: "location", label: `Near "${selected.location}"`, group: "Location", onRemove: onClearLocation }]
      : []),
    ...(selected.q ? [{ key: "q", label: `"${selected.q}"`, group: "Search", onRemove: onRemoveSearch }] : []),
  ];

  if (!chips.length) return null;

  return (
    <div className="active-chips" aria-label="Active filters">
      <span className="active-chips-label">Filters:</span>
      {chips.map((chip) => (
        <span key={chip.key} className="filter-chip">
          <span className="filter-chip-group">{chip.group}:</span> {chip.label}
          <button type="button" onClick={chip.onRemove} aria-label={`Remove filter ${chip.label}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </span>
      ))}
      <button type="button" className="clear-all-btn" onClick={onClearAll}>
        Clear all
      </button>
    </div>
  );
}
