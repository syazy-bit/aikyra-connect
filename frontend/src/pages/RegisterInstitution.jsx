import React, { useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getTaxonomy } from "../services/challengeService.js";
import {
  getInstitution,
  registerInstitution,
  updateInstitution,
} from "../services/institutionService.js";
import { INSTITUTION_TYPE_LABELS } from "../components/InstitutionCard.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

const NAME_MAX = 250;
const DESC_MAX = 5000;
const LOCATION_MAX = 200;

/** Additive capability sections exposed in the form (Phase 4A). */
const CAPABILITY_INPUTS = [
  { key: "departments", label: "Departments", placeholder: "Civil Engineering, Computer Science" },
  { key: "expertise", label: "Expertise", placeholder: "Soil-moisture sensing, GIS, IoT" },
  { key: "research_areas", label: "Research Areas", placeholder: "Low-cost water quality monitoring" },
  { key: "technologies", label: "Technologies", placeholder: "IoT, Drone imaging, Solar" },
  { key: "facilities", label: "Facilities & Labs", placeholder: "Water Testing Lab, Fab Lab" },
  { key: "prototyping", label: "Prototyping Capabilities", placeholder: "3D printing, Electronics bench" },
  { key: "innovation_support", label: "Innovation & Incubation", placeholder: "Incubation, Mentorship" },
  { key: "project_experience", label: "Community / Project Experience", placeholder: "Village water audits (2024)" },
  { key: "collaboration_modes", label: "Collaboration Modes", placeholder: "Student projects, Field pilots" },
];

const splitList = (value) =>
  value.split(",").map((v) => v.trim()).filter(Boolean);

const EMPTY_FORM = {
  name: "",
  institution_type: "",
  location: "",
  description: "",
  website: "",
  contact_email: "",
};

export function RegisterInstitution() {
  const { route, navigate } = useRouter();
  const editId = route.query.edit || null;
  const isEdit = Boolean(editId);

  const [formData, setFormData] = useState(EMPTY_FORM);
  const [domains, setDomains] = useState([]);
  const [capabilities, setCapabilities] = useState({});
  const [taxonomy, setTaxonomy] = useState(null);
  const [loadingEdit, setLoadingEdit] = useState(isEdit);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [conflictId, setConflictId] = useState(null);
  const [errors, setErrors] = useState({});

  // Taxonomy is the single source of truth for domain options.
  useEffect(() => {
    let cancelled = false;
    getTaxonomy()
      .then((data) => !cancelled && setTaxonomy(data))
      .catch(() => !cancelled && setTaxonomy(null));
    return () => {
      cancelled = true;
    };
  }, []);

  // Edit mode: pre-fill from the existing profile.
  useEffect(() => {
    if (!editId) {
      setLoadingEdit(false);
      return;
    }
    let cancelled = false;
    setLoadingEdit(true);
    getInstitution(editId)
      .then((data) => {
        if (cancelled) return;
        setFormData({
          name: data.name ?? "",
          institution_type: data.institution_type ?? "",
          location: data.location ?? "",
          description: data.description ?? "",
          website: data.website ?? "",
          contact_email: data.contact_email ?? "",
        });
        setDomains(data.domains ?? []);
        setCapabilities(data.capabilities ?? {});
      })
      .catch((err) => !cancelled && setApiError(
        err.message || "Could not load this institution profile for editing."
      ))
      .finally(() => !cancelled && setLoadingEdit(false));
    return () => {
      cancelled = true;
    };
  }, [editId]);

  const capabilityText = useMemo(() => {
    const map = {};
    CAPABILITY_INPUTS.forEach(({ key }) => {
      map[key] = (capabilities[key] ?? []).join(", ");
    });
    return map;
  }, [capabilities]);

  const validateForm = () => {
    const nextErrors = {};
    if (!formData.name.trim()) nextErrors.name = "Please enter the institution name.";
    if (!formData.institution_type) nextErrors.institution_type = "Please select the type of institution.";
    if (!formData.location.trim()) nextErrors.location = "Please enter the primary location.";
    if (formData.website.trim() && !/^https?:\/\/.+\..+/.test(formData.website.trim())) {
      nextErrors.website = "Website must be a full URL starting with http:// or https://";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCapabilityChange = (key) => (e) => {
    const value = e.target.value;
    setCapabilities((prev) => ({ ...prev, [key]: splitList(value) }));
  };

  const toggleDomain = (key) => {
    setDomains((prev) =>
      prev.includes(key) ? prev.filter((d) => d !== key) : [...prev, key]
    );
  };

  const buildPayload = () => ({
    name: formData.name.trim(),
    institution_type: formData.institution_type,
    location: formData.location.trim(),
    ...(formData.description.trim() ? { description: formData.description.trim() } : {}),
    ...(formData.website.trim() ? { website: formData.website.trim() } : {}),
    ...(formData.contact_email.trim() ? { contact_email: formData.contact_email.trim() } : {}),
    domains,
    capabilities,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError(null);
    setConflictId(null);
    if (!validateForm()) return;

    try {
      setSubmitting(true);
      const payload = buildPayload();
      const result = isEdit
        ? await updateInstitution(editId, payload)
        : await registerInstitution(payload);
      navigate(`/institutions/${result.id}`);
    } catch (err) {
      const match = err.message?.match(/id:\s*([0-9a-f-]{36})/i);
      if (err.status === 409 && match) {
        setConflictId(match[1]);
      }
      setApiError(err.message || "We could not save this institution right now.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingEdit) {
    return (
      <div className="report-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading institution profile..." />
        </div>
      </div>
    );
  }

  return (
    <div className="report-page">
      <div className="container-narrow">
        <div className="form-header">
          <Link href="/institutions" className="back-link">
            ← Back to Institutions
          </Link>
          <span className="section-kicker">Institutional Participation</span>
          <h1 className="form-page-title">
            {isEdit
              ? "Update your institution profile"
              : "Register your institution on Aikyra"}
          </h1>
          <p className="form-page-subtitle">
            {isEdit
              ? "Keep your capability profile accurate — verified institutions are considered by challenge matching."
              : "Universities, colleges, research institutes and innovation hubs: declare your capabilities so real community challenges can find you."}
          </p>
        </div>

        {apiError && (
          <Alert type="danger" title={conflictId ? "Institution Already Registered" : "Submission Issue"}>
            <p style={{ marginBottom: conflictId ? "var(--space-3)" : 0 }}>{apiError}</p>
            {conflictId && (
              <Link href={`/institutions/${conflictId}`} className="btn btn-secondary btn-sm">
                View the Existing Profile Instead
              </Link>
            )}
          </Alert>
        )}

        {!isEdit && (
          <Alert type="info" title="How verification works" className="inst-info-alert">
            New registrations appear publicly with an <strong>Unverified</strong> badge.
            Aikyra reviews institutional profiles before they participate in
            challenge matching. All capability information you provide here is
            human-entered and attributed to your institution.
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate className="card report-form inst-form" aria-label="Institution details">
          {/* Name */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="inst-name" className="form-label">
                Institution name <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <span className="char-counter">{formData.name.length}/{NAME_MAX}</span>
            </div>
            <input
              id="inst-name"
              name="name"
              type="text"
              className={`form-control ${errors.name ? "has-error" : ""}`}
              placeholder="e.g. Regional Institute of Technology"
              value={formData.name}
              onChange={handleChange}
              disabled={submitting}
              maxLength={NAME_MAX + 10}
              required
            />
            {errors.name && <div className="form-error-msg" role="alert">⚠️ {errors.name}</div>}
          </div>

          {/* Type */}
          <div className="form-group">
            <label htmlFor="inst-type" className="form-label">
              Institution type <span className="form-label-required" aria-hidden="true">*</span>
            </label>
            <select
              id="inst-type"
              name="institution_type"
              className={`form-control ${errors.institution_type ? "has-error" : ""}`}
              value={formData.institution_type}
              onChange={handleChange}
              disabled={submitting}
              required
            >
              <option value="" disabled>Select type…</option>
              {Object.entries(INSTITUTION_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            {errors.institution_type && (
              <div className="form-error-msg" role="alert">⚠️ {errors.institution_type}</div>
            )}
          </div>

          {/* Location */}
          <div className="form-group">
            <label htmlFor="inst-location" className="form-label">
              Primary location <span className="form-label-required" aria-hidden="true">*</span>
            </label>
            <input
              id="inst-location"
              name="location"
              type="text"
              className={`form-control ${errors.location ? "has-error" : ""}`}
              placeholder="e.g. Anantapur, Andhra Pradesh"
              value={formData.location}
              onChange={handleChange}
              disabled={submitting}
              maxLength={LOCATION_MAX + 20}
              required
            />
            {errors.location && <div className="form-error-msg" role="alert">⚠️ {errors.location}</div>}
          </div>

          {/* Description */}
          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="inst-description" className="form-label">
                About the institution
              </label>
              <span className="char-counter">{formData.description.length}/{DESC_MAX}</span>
            </div>
            <textarea
              id="inst-description"
              name="description"
              className="form-control"
              placeholder="Mission, focus areas, notable programs…"
              rows={4}
              value={formData.description}
              onChange={handleChange}
              disabled={submitting}
              maxLength={DESC_MAX + 50}
            />
          </div>

          {/* Website + email */}
          <div className="inst-form-row">
            <div className="form-group">
              <label htmlFor="inst-website" className="form-label">Website</label>
              <input
                id="inst-website"
                name="website"
                type="url"
                className={`form-control ${errors.website ? "has-error" : ""}`}
                placeholder="https://university.edu.in"
                value={formData.website}
                onChange={handleChange}
                disabled={submitting}
              />
              {errors.website && <div className="form-error-msg" role="alert">⚠️ {errors.website}</div>}
            </div>
            <div className="form-group">
              <label htmlFor="inst-email" className="form-label">Contact email</label>
              <input
                id="inst-email"
                name="contact_email"
                type="email"
                className="form-control"
                placeholder="contact@university.edu.in"
                value={formData.contact_email}
                onChange={handleChange}
                disabled={submitting}
              />
            </div>
          </div>

          {/* Domains (from taxonomy API) */}
          <div className="form-group">
            <label className="form-label" id="inst-domains-label">
              Societal domains your institution can contribute to
            </label>
            <p className="form-helper">
              Loaded live from the Aikyra taxonomy — pick every area where you can
              credibly work on challenges.
            </p>
            <div className="inst-domain-picker" role="group" aria-labelledby="inst-domains-label">
              {(taxonomy?.domains ?? []).map((domain) => (
                <button
                  key={domain.key}
                  type="button"
                  className={`chip-toggle ${domains.includes(domain.key) ? "is-active" : ""}`}
                  onClick={() => toggleDomain(domain.key)}
                  aria-pressed={domains.includes(domain.key)}
                  disabled={submitting}
                >
                  {domain.label}
                </button>
              ))}
              {!taxonomy && <span className="form-helper">Loading taxonomy…</span>}
            </div>
          </div>

          {/* Capabilities */}
          <div className="form-group">
            <span className="form-label">Capabilities &amp; expertise</span>
            <p className="form-helper">
              Comma-separated lists. Only filled sections are saved. These are
              self-declared and reviewed during verification.
            </p>
            <div className="inst-capability-grid">
              {CAPABILITY_INPUTS.map(({ key, label, placeholder }) => (
                <div key={key} className="inst-capability-field">
                  <label htmlFor={`cap-${key}`} className="form-label inst-capability-label">
                    {label}
                  </label>
                  <input
                    id={`cap-${key}`}
                    type="text"
                    className="form-control"
                    placeholder={placeholder}
                    value={capabilityText[key]}
                    onChange={handleCapabilityChange(key)}
                    disabled={submitting}
                  />
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: "var(--space-8)" }}>
            <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting}>
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>{isEdit ? "Saving changes..." : "Registering institution..."}</span>
                </>
              ) : (
                <span>{isEdit ? "Save Changes" : "Register Institution"}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
