import React, { useEffect, useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB — enforced server-side too
const ACCEPT = ACCEPTED_TYPES.join(",");

/**
 * Optional photo evidence picker for the public problem report form.
 *
 * The photo is uploaded separately, AFTER the challenge is created, via the
 * authenticated POST /api/challenges/{id}/image endpoint. The server decides
 * the real format and stored filename — these client-side checks are just a
 * courtesy to fail fast on obvious mistakes.
 *
 * The object-URL preview is revoked whenever the file changes or the picker
 * unmounts, so the browser never leaks blob URLs.
 */
export function PhotoUpload({
  file,
  onChange,
  disabled = false,
  error = null,
  id = "photo-evidence",
}) {
  const [rejectReason, setRejectReason] = useState(null);
  const inputRef = useRef(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleSelect = (event) => {
    const selected = event.target.files && event.target.files[0];
    // Reset so picking the same file again re-triggers `change`.
    event.target.value = "";
    setRejectReason(null);

    if (!selected) {
      onChange(null);
      return;
    }
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setRejectReason("Only JPG, PNG, or WebP photos are supported.");
      onChange(null);
      return;
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setRejectReason("The photo must be 5 MB or smaller.");
      onChange(null);
      return;
    }
    onChange(selected);
  };

  const handleRemove = () => {
    setRejectReason(null);
    if (inputRef.current) inputRef.current.value = "";
    onChange(null);
  };

  const message = error || rejectReason;

  return (
    <div className="photo-upload">
      <input
        ref={inputRef}
        id={id}
        type="file"
        className="photo-upload-input"
        accept={ACCEPT}
        onChange={handleSelect}
        disabled={disabled}
        data-testid="photo-evidence-input"
      />

      {file && previewUrl ? (
        <div className="photo-preview-row">
          <img
            src={previewUrl}
            alt="Preview of the photo evidence for your problem report"
            className="photo-preview-thumb"
          />
          <div className="photo-preview-meta">
            <div className="photo-preview-name" title={file.name}>
              {file.name}
            </div>
            <div className="photo-preview-size">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </div>
            <div className="photo-preview-actions">
              <label htmlFor={id} className="btn btn-outline btn-sm">
                Change photo
              </label>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleRemove}
                disabled={disabled}
              >
                Remove photo
              </button>
            </div>
          </div>
        </div>
      ) : (
        <label htmlFor={id} className="photo-dropzone">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          <span className="photo-dropzone-title">Add a photo (optional)</span>
          <span className="photo-dropzone-hint">JPG, PNG or WebP · up to 5 MB</span>
        </label>
      )}

      {message && (
        <div className="form-error-msg" role="alert">
          <span aria-hidden="true">⚠️</span> {message}
        </div>
      )}
    </div>
  );
}