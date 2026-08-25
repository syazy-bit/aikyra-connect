import React, { useEffect, useRef, useState } from "react";

/**
 * Debounced search input. Local state keeps typing responsive; the query
 * reaches the URL (and therefore the API) only after the user pauses.
 */
export function SearchBar({ value, onChange, disabled }) {
  const [text, setText] = useState(value ?? "");
  const debounceRef = useRef(null);
  const inputRef = useRef(null);

  // Stay in sync when the URL changes (back/forward, deep links, clear-all).
  useEffect(() => {
    setText(value ?? "");
  }, [value]);

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const commit = (next) => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onChange(next), 300);
  };

  const handleChange = (e) => {
    const next = e.target.value;
    setText(next);
    commit(next);
  };

  const handleClear = () => {
    clearTimeout(debounceRef.current);
    setText("");
    onChange("");
    inputRef.current?.focus();
  };

  return (
    <div className="search-bar" role="search">
      <svg
        className="search-icon"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        ref={inputRef}
        type="search"
        className="search-input"
        placeholder='Search problems — try "drinking water" or "street lights"'
        aria-label="Search community problems"
        value={text}
        onChange={handleChange}
        onKeyDown={(e) => {
          if (e.key === "Escape") handleClear();
        }}
        disabled={disabled}
        maxLength={200}
      />
      {text && (
        <button
          type="button"
          className="search-clear"
          onClick={handleClear}
          aria-label="Clear search"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
}
