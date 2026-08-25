import React, { useCallback, useEffect, useRef, useState } from "react";

const LOCATION_DEBOUNCE_MS = 400;

/**
 * Filter panel content shared by the desktop rail and the mobile sheet.
 * All domain options come from the taxonomy API — never hardcoded here.
 *
 * Location filtering auto-applies after a short debounce (consistent with
 * search). Enter commits immediately; blur only commits if a debounced
 * update is still pending — never duplicating a request. External URL
 * changes (back/forward, clear-all) cancel any pending debounce and resync
 * the input.
 */
export function FilterControls({ taxonomy, selected, onToggleDomain, onToggleUrgency, onLocationChange }) {
  const [locationText, setLocationText] = useState(selected.location);
  const debounceRef = useRef(null);
  const hasPendingRef = useRef(false);

  // Resync from URL-driven state and cancel stale debounced updates.
  useEffect(() => {
    clearTimeout(debounceRef.current);
    hasPendingRef.current = false;
    setLocationText(selected.location);
  }, [selected.location]);

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const commitLocation = useCallback(
    (raw) => {
      hasPendingRef.current = false;
      const next = (raw ?? "").trim();
      if (next !== selected.location) {
        onLocationChange(next);
      }
    },
    [onLocationChange, selected.location]
  );

  const handleLocationChange = (e) => {
    const next = e.target.value;
    setLocationText(next);
    clearTimeout(debounceRef.current);
    hasPendingRef.current = true;
    debounceRef.current = setTimeout(() => commitLocation(next), LOCATION_DEBOUNCE_MS);
  };

  const handleLocationKeyDown = (e) => {
    if (e.key !== "Enter") return;
    clearTimeout(debounceRef.current);
    commitLocation(e.currentTarget.value);
  };

  const handleLocationBlur = () => {
    // Only commit here when a debounced update is still in flight;
    // otherwise it already ran (no duplicate request).
    if (hasPendingRef.current) {
      clearTimeout(debounceRef.current);
      commitLocation(locationText);
    }
  };

  return (
    <div className="filter-controls">
      <fieldset className="filter-group">
        <legend>Problem area</legend>
        {taxonomy?.domains?.length ? (
          taxonomy.domains.map((domain) => (
            <label key={domain.key} className="filter-option">
              <input
                type="checkbox"
                checked={selected.domains.includes(domain.key)}
                onChange={() => onToggleDomain(domain.key)}
              />
              <span>{domain.label}</span>
            </label>
          ))
        ) : (
          <p className="filter-loading">Loading problem areas…</p>
        )}
      </fieldset>

      <fieldset className="filter-group">
        <legend>Urgency</legend>
        <div className="urgency-chip-row" role="group" aria-label="Filter by urgency">
          {(taxonomy?.urgency_levels ?? ["low", "medium", "high", "critical"]).map((level) => (
            <button
              key={level}
              type="button"
              className={`urgency-chip urgency-${selected.urgencies.includes(level) ? "active" : "idle"} chip-${level}`}
              aria-pressed={selected.urgencies.includes(level)}
              onClick={() => onToggleUrgency(level)}
            >
              {level === "critical" ? "Critical" : level.charAt(0).toUpperCase() + level.slice(1)}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Location</legend>
        <input
          type="text"
          className="filter-location-input"
          placeholder="e.g. Barpeta, Nashik…"
          aria-label="Filter by location text"
          value={locationText}
          maxLength={200}
          onChange={handleLocationChange}
          onKeyDown={handleLocationKeyDown}
          onBlur={handleLocationBlur}
        />
      </fieldset>
    </div>
  );
}
