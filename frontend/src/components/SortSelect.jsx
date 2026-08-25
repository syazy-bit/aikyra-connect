import React from "react";

const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "urgency", label: "Most urgent" },
  { value: "relevance", label: "Best match", requiresSearch: true },
];

/**
 * Sort control. "Best match" (deterministic lexical relevance ranking)
 * only applies while a search query is active.
 */
export function SortSelect({ value, onChange, hasQuery }) {
  return (
    <label className="sort-select-label">
      <span className="sr-only">Sort results</span>
      <span className="sort-prefix">Sort</span>
      <select
        className="sort-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {SORT_OPTIONS.filter((o) => !o.requiresSearch || hasQuery).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
