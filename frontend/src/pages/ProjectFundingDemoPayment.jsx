import React, { useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getProject, getProjectFunding, createDemoContribution } from "../services/projectService.js";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { FundingProgress } from "../components/FundingProgress.jsx";
import { formatMoney, rupeesToMinor } from "../utils/money.js";

/**
 * DEMO / HACKATHON PRESENTATION ONLY — simulated payment confirmation page.
 *
 * This page is intentionally a simulation: there are no card number, CVV, bank
 * or UPI fields, no Razorpay/Stripe, no transaction ids and no real payment
 * buttons. Clicking "Simulate successful payment" calls the demo contribution
 * API, which stores a COMPLETED contribution on the project's OPEN verified
 * funding goal and returns the server-derived summary. The public funding bar
 * then reflects the new amount because it reads the same DB-authoritative
 * aggregate.
 */
export function ProjectFundingDemoPayment() {
  const { route, navigate } = useRouter();
  const projectId = route.params.id;
  const rawAmount = route.query?.amount ?? "";

  const [project, setProject] = useState(null);
  const [fundingSummary, setFundingSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [recorded, setRecorded] = useState(null);

  const amountMinor = useMemo(() => rupeesToMinor(rawAmount), [rawAmount]);
  const amountIsValid = amountMinor !== null;

  const load = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(projectId), getProjectFunding(projectId)])
      .then(([projectData, fundingBody]) => {
        setProject(projectData);
        setFundingSummary(fundingBody?.funding ?? null);
      })
      .catch((err) => {
        setError(
          err.message ||
            "This project could not be loaded. It may not exist."
        );
        setProject(null);
      })
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => load(), [projectId]);

  const simulatePayment = () => {
    if (amountMinor === null) return;
    setBusy(true);
    setActionError(null);
    setRecorded(null);
    createDemoContribution(projectId, { amount_minor: amountMinor })
      .then((summary) => {
        setRecorded(summary);
        setFundingSummary(summary);
      })
      .catch((err) => {
        setActionError(
          err.message ||
            "The demo support could not be recorded. Please try again."
        );
      })
      .finally(() => setBusy(false));
  };

  const backToFunding = () => navigate(`/projects/${projectId}/funding`);

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading demo payment..." />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/projects" className="back-link">
            ← Back to Projects
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Project Unavailable">
              <p style={{ margin: 0 }}>
                {error || "We could not find the project you were looking for."}
              </p>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href={`/projects/${projectId}/funding`} className="back-link">
          ← Back to funding
        </Link>

        <section className="card detail-card">
          <div className="detail-status-row">
            <span className="section-kicker">Demo payment</span>
            <span className="badge-demo">Demo</span>
          </div>
          <h1 className="detail-title">{project.title}</h1>

          <div className="demo-payment-summary">
            <div className="demo-payment-amount">
              <span className="demo-payment-label">Amount</span>
              <span className="demo-payment-value">
                {amountIsValid ? formatMoney(amountMinor, "INR") : "—"}
              </span>
            </div>
            {amountIsValid && (
              <p className="funding-note">
                This equals ₹
                {amountMinor / 100} in a simulated support contribution.
              </p>
            )}
          </div>
        </section>

        <div className="demo-payment-honesty card">
          <Alert type="info" title="Presentation demo only">
            <p style={{ margin: 0 }}>
              No real money will be charged. This is a simulated support flow
              for the hackathon presentation — it does not process any payment.
            </p>
          </Alert>
        </div>

        {!amountIsValid && (
          <div className="card" style={{ padding: "var(--space-5)" }}>
            <Alert type="danger" title="No valid amount">
              <p style={{ marginBottom: "var(--space-3)" }}>
                A valid amount (at least ₹0.01, up to two decimals) is required
                to continue. Please choose an amount on the funding page.
              </p>
              <button type="button" className="btn btn-secondary btn-sm" onClick={backToFunding}>
                Choose an amount
              </button>
            </Alert>
          </div>
        )}

        {actionError && (
          <Alert type="danger" title="Could not record demo support">
            <p style={{ margin: 0 }}>{actionError}</p>
          </Alert>
        )}

        {recorded && (
          <div className="card" style={{ padding: "var(--space-5)" }}>
            <Alert type="success" title="Demo support recorded">
              <p style={{ margin: 0 }}>
                Your simulated support has been recorded against this verified
                funding goal. The public funding bar below now reflects the
                updated amount — computed from the database, not this page.
              </p>
            </Alert>
          </div>
        )}

        {recorded && fundingSummary && (
          <section className="card" style={{ padding: "var(--space-6)" }}>
            <span className="section-kicker">Updated funding</span>
            <FundingProgress funding={fundingSummary} />
          </section>
        )}

        <div className="card" style={{ padding: "var(--space-6)" }}>
          <div className="demo-payment-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={backToFunding}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={simulatePayment}
              disabled={busy || !amountIsValid || Boolean(recorded)}
            >
              {busy ? "Recording…" : "Simulate successful payment"}
            </button>
          </div>
          <p className="demo-support-note" style={{ marginTop: "var(--space-4)" }}>
            ℹ Demo only — no real money is charged and no payment is processed.
          </p>
        </div>
      </div>
    </div>
  );
}
