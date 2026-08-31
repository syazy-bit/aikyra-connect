import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { OnboardingPathSelection } from "../components/OnboardingPathSelection.jsx";

const PASSWORD_MIN = 8;
const PASSWORD_MAX = 128;

const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

function sanitizeNext(value) {
  if (typeof value !== "string" || value === "") return "/";
  if (!value.startsWith("/") || value.startsWith("//")) return "/";
  if (value.includes("://") || value.includes("\\")) return "/";
  return value;
}

function EyeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

// Institution Admin registration form - collects user info + institution info
function InstitutionAdminRegistration({ onBack, onSuccess, loginHref }) {
  const { register, login, navigate } = useAuth();
  const { route } = useRouter();

  // User info
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Institution info
  const [instName, setInstName] = useState("");
  const [instType, setInstType] = useState("");
  const [instLocation, setInstLocation] = useState("");
  const [instDescription, setInstDescription] = useState("");
  const [instWebsite, setInstWebsite] = useState("");
  const [instContactEmail, setInstContactEmail] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState("user"); // "user" -> "institution"
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);

  const next = sanitizeNext(route.query.next);

  const validateUserForm = () => {
    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Please enter your email address.";
    else if (!EMAIL_PATTERN.test(email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!password) nextErrors.password = "Please create a password.";
    else if (password.length < PASSWORD_MIN) {
      nextErrors.password = `Password must be at least ${PASSWORD_MIN} characters.`;
    } else if (password.length > PASSWORD_MAX) {
      nextErrors.password = `Password must not exceed ${PASSWORD_MAX} characters.`;
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const validateInstitutionForm = () => {
    const nextErrors = {};
    if (!instName.trim()) nextErrors.instName = "Please enter the institution name.";
    if (!instType) nextErrors.instType = "Please select the type of institution.";
    if (!instLocation.trim()) nextErrors.instLocation = "Please enter the primary location.";
    if (instWebsite.trim() && !/^https?:\/\/.+\..+/.test(instWebsite.trim())) {
      nextErrors.instWebsite = "Website must be a full URL starting with http:// or https://";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleUserSubmit = async (e) => {
    e.preventDefault();
    if (!validateUserForm()) return;

    setSubmitting(true);
    setServerError(null);
    try {
      const result = await register(email.trim(), password, fullName.trim() || undefined);
      if (result.success) {
        // Auto-login after registration
        const loginResult = await login(email.trim(), password);
        if (loginResult.success) {
          setStep("institution");
          setSubmitting(false);
          return;
        }
        setServerError("Account created but login failed. Please sign in manually.");
        navigate("/login");
        return;
      }
      if (result.status === 409) {
        setErrors((prev) => ({ ...prev, email: result.error }));
      } else {
        setServerError(result.error);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleInstitutionSubmit = async (e) => {
    e.preventDefault();
    if (!validateInstitutionForm()) return;

    setSubmitting(true);
    setServerError(null);

    try {
      // Import institutionService dynamically to avoid circular deps
      const { registerInstitution } = await import("../services/institutionService.js");

      const payload = {
        name: instName.trim(),
        institution_type: instType,
        location: instLocation.trim(),
        ...(instDescription.trim() ? { description: instDescription.trim() } : {}),
        ...(instWebsite.trim() ? { website: instWebsite.trim() } : {}),
        ...(instContactEmail.trim() ? { contact_email: instContactEmail.trim() } : {}),
        domains: [],
        capabilities: {},
      };

      const result = await registerInstitution(payload);
      // Success - institution created with institution_admin membership
      sessionStorage.setItem("aikyra_welcome_ts", String(Date.now()));
      onSuccess?.(result.id);
      navigate(`/institutions/${result.id}`);
    } catch (err) {
      if (err.status === 401) {
        setServerError("Your session has expired. Please sign in again.");
        navigate("/login");
        return;
      }
      if (err.status === 403) {
        setServerError("You don't have permission to register an institution.");
        return;
      }
      setServerError(err.message || "We could not register your institution right now.");
    } finally {
      setSubmitting(false);
    }
  };

  const passwordState = !password
    ? "empty"
    : password.length < PASSWORD_MIN
      ? "short"
      : password.length > PASSWORD_MAX
        ? "long"
        : "ok";

  if (step === "user") {
    return (
      <div className="auth-page">
        <div className="container-narrow">
          <div className="auth-card card">
            <div className="auth-header">
              <Link href="/register" className="back-link" style={{ marginBottom: "var(--space-6)" }} onClick={onBack}>
                ← Back
              </Link>
              <h1 className="auth-title">Create Institution Admin Account</h1>
              <p className="auth-subtitle">
                First, create your personal account. Then you'll register your institution.
              </p>
            </div>

            {serverError && (
              <Alert type="danger" title="Registration Failed">
                <p>{serverError}</p>
              </Alert>
            )}

            <form onSubmit={handleUserSubmit} noValidate className="auth-form">
              <div className="form-group">
                <label htmlFor="reg-email" className="form-label">
                  Email <span className="form-label-required" aria-hidden="true">*</span>
                </label>
                <input
                  id="reg-email"
                  name="email"
                  type="email"
                  className={`form-control ${errors.email ? "has-error" : ""}`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submitting}
                  required
                  autoComplete="email"
                  autoFocus
                  maxLength={254}
                  aria-describedby={errors.email ? "reg-email-error" : undefined}
                />
                {errors.email && <div className="form-error-msg" role="alert" id="reg-email-error">⚠️ {errors.email}</div>}
              </div>

              <div className="form-group">
                <label htmlFor="reg-fullname" className="form-label">Full Name (optional)</label>
                <input
                  id="reg-fullname"
                  name="full_name"
                  type="text"
                  className="form-control"
                  placeholder="Your name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={submitting}
                  maxLength={250}
                  autoComplete="name"
                />
              </div>

              <div className="form-group">
                <label htmlFor="reg-password" className="form-label">
                  Password <span className="form-label-required" aria-hidden="true">*</span>
                </label>
                <div className="password-field">
                  <input
                    id="reg-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    className={`form-control ${errors.password ? "has-error" : ""}`}
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={submitting}
                    required
                    autoComplete="new-password"
                    minLength={PASSWORD_MIN}
                    maxLength={PASSWORD_MAX}
                    aria-describedby={errors.password ? "reg-password-error" : undefined}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-controls="reg-password"
                    disabled={submitting}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
                {errors.password && <div className="form-error-msg" role="alert" id="reg-password-error">⚠️ {errors.password}</div>}
                {passwordState === "empty" && (
                  <p className="form-helper" style={{ marginTop: "var(--space-1)" }}>
                    Minimum {PASSWORD_MIN} characters, maximum {PASSWORD_MAX} characters.
                  </p>
                )}
                {passwordState === "short" && (
                  <p className="form-helper" style={{ marginTop: "var(--space-1)" }}>
                    At least {PASSWORD_MIN} characters.
                  </p>
                )}
                {passwordState === "long" && (
                  <p className="form-helper is-invalid" style={{ marginTop: "var(--space-1)" }}>
                    Maximum {PASSWORD_MAX} characters.
                  </p>
                )}
                {passwordState === "ok" && (
                  <p className="form-helper is-valid" style={{ marginTop: "var(--space-1)" }}>
                    <span aria-hidden="true">✓ </span>At least {PASSWORD_MIN} characters
                  </p>
                )}
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg btn-block"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <LoadingSpinner size="sm" message="" center={false} />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <span>Continue to Institution Details</span>
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                Already have an account? <Link href={loginHref} className="auth-link">Sign in</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Institution details
  const INSTITUTION_TYPE_LABELS = {
    university: "University",
    college: "College",
    research_institute: "Research Institute",
    innovation_hub: "Innovation Hub",
    other: "Other",
  };

  return (
    <div className="auth-page">
      <div className="container-narrow">
        <div className="auth-card card" style={{ maxWidth: "42rem" }}>
          <div className="auth-header">
            <Link href="/register" className="back-link" style={{ marginBottom: "var(--space-6)" }} onClick={onBack}>
              ← Back
            </Link>
            <h1 className="auth-title">Register Your Institution</h1>
            <p className="auth-subtitle">
              Provide your institution's details. You will become its first Institution Admin.
            </p>
          </div>

          {serverError && (
            <Alert type="danger" title="Registration Failed">
              <p>{serverError}</p>
            </Alert>
          )}

          <form onSubmit={handleInstitutionSubmit} noValidate className="auth-form">
            <div className="form-group">
              <label htmlFor="inst-name" className="form-label">
                Institution name <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="inst-name"
                name="name"
                type="text"
                className={`form-control ${errors.instName ? "has-error" : ""}`}
                placeholder="e.g. Regional Institute of Technology"
                value={instName}
                onChange={(e) => setInstName(e.target.value)}
                disabled={submitting}
                required
                maxLength={250}
              />
              {errors.instName && <div className="form-error-msg" role="alert">⚠️ {errors.instName}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="inst-type" className="form-label">
                Institution type <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <select
                id="inst-type"
                name="institution_type"
                className={`form-control ${errors.instType ? "has-error" : ""}`}
                value={instType}
                onChange={(e) => setInstType(e.target.value)}
                disabled={submitting}
                required
              >
                <option value="" disabled>Select type…</option>
                {Object.entries(INSTITUTION_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              {errors.instType && <div className="form-error-msg" role="alert">⚠️ {errors.instType}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="inst-location" className="form-label">
                Primary location <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="inst-location"
                name="location"
                type="text"
                className={`form-control ${errors.instLocation ? "has-error" : ""}`}
                placeholder="e.g. Anantapur, Andhra Pradesh"
                value={instLocation}
                onChange={(e) => setInstLocation(e.target.value)}
                disabled={submitting}
                required
                maxLength={200}
              />
              {errors.instLocation && <div className="form-error-msg" role="alert">⚠️ {errors.instLocation}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="inst-description" className="form-label">About the institution</label>
              <textarea
                id="inst-description"
                name="description"
                className="form-control"
                placeholder="Mission, focus areas, notable programs…"
                rows={3}
                value={instDescription}
                onChange={(e) => setInstDescription(e.target.value)}
                disabled={submitting}
                maxLength={5000}
              />
            </div>

            <div className="inst-form-row">
              <div className="form-group">
                <label htmlFor="inst-website" className="form-label">Website</label>
                <input
                  id="inst-website"
                  name="website"
                  type="url"
                  className={`form-control ${errors.instWebsite ? "has-error" : ""}`}
                  placeholder="https://university.edu.in"
                  value={instWebsite}
                  onChange={(e) => setInstWebsite(e.target.value)}
                  disabled={submitting}
                />
                {errors.instWebsite && <div className="form-error-msg" role="alert">⚠️ {errors.instWebsite}</div>}
              </div>
              <div className="form-group">
                <label htmlFor="inst-email" className="form-label">Contact email</label>
                <input
                  id="inst-email"
                  name="contact_email"
                  type="email"
                  className="form-control"
                  placeholder="contact@university.edu.in"
                  value={instContactEmail}
                  onChange={(e) => setInstContactEmail(e.target.value)}
                  disabled={submitting}
                />
              </div>
            </div>

            <Alert type="info" title="How verification works" className="inst-info-alert">
              New registrations appear publicly with an <strong>Unverified</strong> badge.
              Aikyra reviews institutional profiles before they participate in
              challenge matching. All capability information you provide here is
              human-entered and attributed to your institution.
            </Alert>

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Registering institution...</span>
                </>
              ) : (
                <span>Register Institution</span>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Already have an account? <Link href={loginHref} className="auth-link">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Register() {
  const { route, navigate } = useRouter();
  const { register, clearError } = useAuth();

  const [selectedPath, setSelectedPath] = useState(null); // "citizen" or "institution_admin"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);

  const next = sanitizeNext(route.query.next);
  const loginHref = next !== "/" ? `/login?next=${encodeURIComponent(next)}` : "/login";

  useEffect(() => {
    clearError();
  }, [clearError]);

  const validateForm = () => {
    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Please enter your email address.";
    else if (!EMAIL_PATTERN.test(email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!password) nextErrors.password = "Please create a password.";
    else if (password.length < PASSWORD_MIN) {
      nextErrors.password = `Password must be at least ${PASSWORD_MIN} characters.`;
    } else if (password.length > PASSWORD_MAX) {
      nextErrors.password = `Password must not exceed ${PASSWORD_MAX} characters.`;
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    setServerError(null);
    const result = await register(email.trim(), password, fullName.trim() || undefined);
    setSubmitting(false);

    if (result.success) {
      sessionStorage.setItem("aikyra_welcome_ts", String(Date.now()));
      navigate(next);
      return;
    }

    if (result.status === 409) {
      setErrors((prev) => ({ ...prev, email: result.error }));
    } else {
      setServerError(result.error);
    }
  };

  const handlePathSelect = (path) => {
    setSelectedPath(path);
    setErrors({});
    setServerError(null);
  };

  const handleInstitutionAdminSuccess = (institutionId) => {
    // Institution registered successfully
    console.log("Institution registered:", institutionId);
  };

  // Show path selection if no path selected yet
  if (!selectedPath) {
    return (
      <OnboardingPathSelection
        title="Create your Aikyra account"
        subtitle="How will you use Aikyra?"
        onPathSelect={handlePathSelect}
        showBackLink={true}
      />
    );
  }

  // Citizen path - existing registration form
  if (selectedPath === "citizen") {
    const passwordState = !password
      ? "empty"
      : password.length < PASSWORD_MIN
        ? "short"
        : password.length > PASSWORD_MAX
          ? "long"
          : "ok";

    return (
      <div className="auth-page">
        <div className="container-narrow">
          <div className="auth-card card">
            <div className="auth-header">
              <Link href="/register" className="back-link" style={{ marginBottom: "var(--space-6)" }} onClick={() => setSelectedPath(null)}>
                ← Back
              </Link>
              <h1 className="auth-title">Create your Aikyra account</h1>
              <p className="auth-subtitle">
                Join challenges, collaborate with teams, and help turn community
                problems into measurable solutions.
              </p>
            </div>

            {serverError && (
              <Alert type="danger" title="Registration Failed">
                <p>{serverError}</p>
              </Alert>
            )}

            <form onSubmit={handleSubmit} noValidate className="auth-form">
              <div className="form-group">
                <label htmlFor="reg-email" className="form-label">
                  Email <span className="form-label-required" aria-hidden="true">*</span>
                </label>
                <input
                  id="reg-email"
                  name="email"
                  type="email"
                  className={`form-control ${errors.email ? "has-error" : ""}`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submitting}
                  required
                  autoComplete="email"
                  autoFocus
                  maxLength={254}
                  aria-describedby={errors.email ? "reg-email-error" : undefined}
                />
                {errors.email && <div className="form-error-msg" role="alert" id="reg-email-error">⚠️ {errors.email}</div>}
              </div>

              <div className="form-group">
                <label htmlFor="reg-fullname" className="form-label">Full Name (optional)</label>
                <input
                  id="reg-fullname"
                  name="full_name"
                  type="text"
                  className="form-control"
                  placeholder="Your name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={submitting}
                  maxLength={250}
                  autoComplete="name"
                />
              </div>

              <div className="form-group">
                <label htmlFor="reg-password" className="form-label">
                  Password <span className="form-label-required" aria-hidden="true">*</span>
                </label>
                <div className="password-field">
                  <input
                    id="reg-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    className={`form-control ${errors.password ? "has-error" : ""}`}
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={submitting}
                    required
                    autoComplete="new-password"
                    minLength={PASSWORD_MIN}
                    maxLength={PASSWORD_MAX}
                    aria-describedby={errors.password ? "reg-password-error" : undefined}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-controls="reg-password"
                    disabled={submitting}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
                {errors.password && <div className="form-error-msg" role="alert" id="reg-password-error">⚠️ {errors.password}</div>}
                {passwordState === "empty" && (
                  <p className="form-helper" style={{ marginTop: "var(--space-1)" }}>
                    Minimum {PASSWORD_MIN} characters, maximum {PASSWORD_MAX} characters.
                  </p>
                )}
                {passwordState === "short" && (
                  <p className="form-helper" style={{ marginTop: "var(--space-1)" }}>
                    At least {PASSWORD_MIN} characters.
                  </p>
                )}
                {passwordState === "long" && (
                  <p className="form-helper is-invalid" style={{ marginTop: "var(--space-1)" }}>
                    Maximum {PASSWORD_MAX} characters.
                  </p>
                )}
                {passwordState === "ok" && (
                  <p className="form-helper is-valid" style={{ marginTop: "var(--space-1)" }}>
                    <span aria-hidden="true">✓ </span>At least {PASSWORD_MIN} characters
                  </p>
                )}
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg btn-block"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <LoadingSpinner size="sm" message="" center={false} />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <span>Create Account</span>
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                Already have an account? <Link href={loginHref} className="auth-link">Sign in</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Institution Admin path - combined user + institution registration
  return (
    <InstitutionAdminRegistration
      onBack={() => setSelectedPath(null)}
      onSuccess={handleInstitutionAdminSuccess}
      loginHref={loginHref}
    />
  );
}