import React, { useEffect, useState } from "react";
import { Modal } from "./Modal.jsx";
import { Alert } from "./Alert.jsx";
import { SUPPORT_TYPE_OPTIONS } from "./SupportTypeBadge.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { createOffer, createOrganization, getMyOrganization } from "../services/projectService.js";

export function OfferSupportModal({ project, onClose, onOffered }) {
  const { isAuthenticated } = useAuth();

  const [managerOrg, setManagerOrg] = useState(null);
  const [orgLoading, setOrgLoading] = useState(true);

  const [orgName, setOrgName] = useState("");
  const [orgDescription, setOrgDescription] = useState("");
  const [supportType, setSupportType] = useState("funding");
  const [message, setMessage] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (isAuthenticated) {
      getMyOrganization()
        .then((data) => !cancelled && setManagerOrg(data?.organization ?? null))
        .catch(() => !cancelled && setManagerOrg(null))
        .finally(() => !cancelled && setOrgLoading(false));
    } else {
      setOrgLoading(false);
    }
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const needsOrg = isAuthenticated && !orgLoading && !managerOrg;

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let org = managerOrg;
      if (needsOrg) {
        org = await createOrganization({
          name: orgName.trim(),
          description: orgDescription.trim() || null,
        });
      }
      await createOffer(project.id, {
        support_type: supportType,
        message: message.trim() || null,
      });
      onOffered();
    } catch (err) {
      setError(err.message || "Could not submit your support offer. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal open title="Offer support" onClose={onClose} wide={false}>
      <form onSubmit={submit} noValidate>
        <p className="modal-copy">
          Offer support for <strong>{project.title}</strong>.
        </p>

        {!isAuthenticated && (
          <Alert type="info" title="Sign in to offer support">
            <p style={{ margin: 0 }}>
              You must sign in to make a support offer.
            </p>
          </Alert>
        )}

        {isAuthenticated && needsOrg && (
          <>
            <h4 className="offersub-heading">Your organization</h4>
            <div className="form-group">
              <label htmlFor="org-name" className="form-label">
                Organization name <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="org-name"
                className="form-control"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                maxLength={250}
                required
                placeholder="e.g. GreenGrid Foundation"
              />
            </div>
            <div className="form-group">
              <label htmlFor="org-description" className="form-label">
                About your organization <span className="form-label-optional">(optional)</span>
              </label>
              <textarea
                id="org-description"
                className="form-control"
                value={orgDescription}
                onChange={(e) => setOrgDescription(e.target.value)}
                rows={3}
                maxLength={5000}
              />
            </div>
          </>
        )}

        <div className="form-group">
          <label htmlFor="support-type" className="form-label">
            Support type <span className="form-label-required" aria-hidden="true">*</span>
          </label>
          <select
            id="support-type"
            className="form-control"
            value={supportType}
            onChange={(e) => setSupportType(e.target.value)}
          >
            {SUPPORT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="offer-message" className="form-label">
            Message <span className="form-label-optional">(optional)</span>
          </label>
          <textarea
            id="offer-message"
            className="form-control"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            maxLength={20000}
            placeholder="A short note about what you can offer."
          />
        </div>

        {error && (
          <Alert type="danger" title="Could not offer support">
            <p style={{ margin: 0 }}>{error}</p>
          </Alert>
        )}

        <div className="form-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy || !isAuthenticated}>
            {busy ? "Offering…" : "Submit support offer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
