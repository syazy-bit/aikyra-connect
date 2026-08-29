import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

const PASSWORD_MIN = 8;
const PASSWORD_MAX = 128;

// Mirrors the backend regex (schemas/auth.py) so valid-for-client email
// addresses can't fail later with a server-side format error. The backend
// remains the authoritative validator.
const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

/**
 * Only allow internal application paths for redirects (mirrors Login).
 * Prevents open redirects: must start with "/", must not be protocol-relative
 * (//), absolute (contains ://), or contain backslash tricks.
 */
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
      <circle cx="12" cy="12" r="3" />
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

export function Register() {
  const { route, navigate } = useRouter();
  const { register, clearError } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);

  const next = sanitizeNext(route.query.next);
  const loginHref = next !== "/" ? `/login?next=${encodeURIComponent(next)}` : "/login";

  // Registration always starts clean — a stale error from another auth
  // page must never appear here.
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
      // Subtle one-time welcome cue on the destination page.
      sessionStorage.setItem("aikyra_welcome_ts", String(Date.now()));
      navigate(next);
      return;
    }

    if (result.status === 409) {
      // Duplicate email: keep the exact backend message, but surface it
      // inline at the email field with a clear path to sign in below.
      setErrors((prev) => ({ ...prev, email: result.error }));
    } else {
      setServerError(result.error);
    }
  };

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
            <Link href="/" className="back-link" style={{ marginBottom: "var(--space-6)" }}>
              ← Back to Home
            </Link>
            <h1 className="auth-title">Create your AIKYRA account</h1>
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