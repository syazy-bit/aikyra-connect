import React, { useState } from "react";
import { Modal } from "./Modal.jsx";
import { Alert } from "./Alert.jsx";
import {
  createImpactMetric,
  updateImpactMetric,
} from "../services/projectService.js";

/**
 * Add / edit an impact metric on an approved project (team lead only).
 * `editing` is null for create or an existing metric for edit.
 */
export function ImpactMetricModal({ project, editing, onClose, onSaved }) {
  const isEdit = Boolean(editing);

  const [name, setName] = useState(editing?.name ?? "");
  const [value, setValue] = useState(editing?.value ?? "");
  const [unit, setUnit] = useState(editing?.unit ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        value: value.trim(),
        unit: unit.trim() || null,
        description: description.trim() || null,
      };
      if (isEdit) {
        await updateImpactMetric(project.id, editing.id, payload);
      } else {
        await createImpactMetric(project.id, payload);
      }
      onSaved();
    } catch (err) {
      setError(
        err.message || "Could not save the impact metric. Please try again."
      );
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      title={isEdit ? "Edit impact metric" : "Add impact metric"}
      onClose={onClose}
      wide={false}
    >
      <form onSubmit={submit} noValidate>
        <p className="modal-copy">
          {isEdit ? "Update" : "Add"} a measured outcome for{" "}
          <strong>{project.title}</strong>.
        </p>

        <div className="form-group">
          <label htmlFor="impact-name" className="form-label">
            Metric name <span className="form-label-required" aria-hidden="true">*</span>
          </label>
          <input
            id="impact-name"
            className="form-control"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={300}
            required
            placeholder="e.g. Households reached"
          />
        </div>

        <div className="form-group">
          <label htmlFor="impact-value" className="form-label">
            Value <span className="form-label-required" aria-hidden="true">*</span>
          </label>
          <input
            id="impact-value"
            className="form-control"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            maxLength={100}
            required
            placeholder="e.g. 120 or ~85%"
          />
        </div>

        <div className="form-group">
          <label htmlFor="impact-unit" className="form-label">
            Unit <span className="form-label-optional">(optional)</span>
          </label>
          <input
            id="impact-unit"
            className="form-control"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            maxLength={50}
            placeholder="e.g. households, people, villages"
          />
        </div>

        <div className="form-group">
          <label htmlFor="impact-description" className="form-label">
            Description <span className="form-label-optional">(optional)</span>
          </label>
          <textarea
            id="impact-description"
            className="form-control"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="A short note explaining the metric."
          />
        </div>

        {error && (
          <Alert type="danger" title="Could not save the impact metric">
            <p style={{ margin: 0 }}>{error}</p>
          </Alert>
        )}

        <div className="form-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={busy}
          >
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : isEdit ? "Save changes" : "Add metric"}
          </button>
        </div>
      </form>
    </Modal>
  );
}