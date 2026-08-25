import React from "react";

export function LoadingSpinner({ size = "default", message = "Loading...", center = true }) {
  const isLarge = size === "lg";

  const content = (
    <div
      role="status"
      aria-busy="true"
      aria-label={message}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "var(--space-3)",
      }}
    >
      <span className={`spinner ${isLarge ? "spinner-lg" : ""}`} aria-hidden="true" />
      {message && (
        <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", fontWeight: 500 }}>
          {message}
        </span>
      )}
    </div>
  );

  if (center) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "var(--space-12) 0",
          width: "100%",
        }}
      >
        {content}
      </div>
    );
  }

  return content;
}
