import React, { useState } from "react";
import { Modal } from "./Modal.jsx";
import { Alert } from "./Alert.jsx";
import {
  createOutcomeReport,
  updateOutcomeReport,
} from "../services/projectService.js";

const MAX_TEXT = 20000;

/**
 * Write / edit the outcome report for an implemented project (team lead
 * only). `report` is null for create or an existing report for edit.
 *
 * A report is a project-scoped singleton: only one can exist, only once the
 * project is at the 'implemented' stage, and the server enforces both.
 */
export function OutcomeReportModal({ project, report, onClose, onSaved }) {
  const isEdit = Boolean(report);

  const [summary, setSummary] = useState(report?.summary ?? "");
  const [results, setResults] = useState(report?.results ?? "");
  const [lessonsLearned, setLessonsLearned] = useState(
    report?.lessons_learned ?? ""
  );
  const [nextSteps, setNextSteps] = useState(report?.next_steps ?? "");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        summary: summary.trim(),
        results: results.trim() || null,
        lessons_learned: lessonsLearned.trim() || null,
        next_steps: nextSteps.trim() || null,
      };
      if (isEdit) {
        await updateOutcomeReport(project.id, payload);
      } else {
        await createOutcomeReport(project.id, payload);
      }
      onSaved();
    } catch (err) {
      setError(
        err.message || "The outcome report could not be saved. Please try again."
      );
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      title={isEdit ? "Edit outcome report" : "Add outcome report"}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} noValidate>
        <p className="modal-copy">
          {isEdit ? "Update" : "Write"} the conclusive outcome story for{" "}
          <strong>{project.title}</strong>. Reports are written once a solution
          is implemented and are publicly visible.
        </p>

        <div className="form-group">
          <label htmlFor="report-summary" className="form-label">
            Summary{" "}
            <span className="form-label-required" aria-hidden="true">*</span>
          </label>
          <textarea
            id="report-summary"
            className="form-control"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={4}
            maxLength={MAX_TEXT}
            required
            placeholder="What was delivered, and why it matters."
          />
        </div>

        <div className="form-group">
          <label htmlFor="report-results" className="form-label">
            Results <span className="form-label-optional">(optional)</span>
          </label>
          <textarea
            id="report-results"
            className="form-control"
            value={results}
            onChange={(e) => setResults(e.target.value)}
            rows={3}
            maxLength={MAX_TEXT}
            placeholder="Measured outcomes, quotes, evidence."
          />
        </div>

        <div className="form-group">
          <label htmlFor="report-lessons" className="form-label">
            Lessons learned <span className="form-label-optional">(optional)</span>
          </label>
          <textarea
            id="report-lessons"
            className="form-control"
            value={lessonsLearned}
            onChange={(e) => setLessonsLearned(e.target.value)}
            rows={3}
            maxLength={MAX_TEXT}
            placeholder="What the team learned along the way."
          />
        </div>

        <div className="form-group">
          <label htmlFor="report-next" className="form-label">
            Next steps <span className="form-label-optional">(optional)</span>
          </label>
          <textarea
            id="report-next"
            className="form-control"
            value={nextSteps}
            onChange={(e) => setNextSteps(e.target.value)}
            rows={3}
            maxLength={MAX_TEXT}
            placeholder="Scaling, follow-up work, handover."
          />
        </div>

        {error && (
          <Alert type="danger" title="Could not save the outcome report">
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
            {busy ? "Saving…" : isEdit ? "Save changes" : "Publish report"}
          </button>
        </div>
      </form>
    </Modal>
  );
}