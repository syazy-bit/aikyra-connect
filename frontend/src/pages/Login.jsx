import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth, SESSION_EXPIRED_MESSAGE } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { LoginPathSelection } from "../components/OnboardingPathSelection.jsx";

/**
 * Only allow internal application paths for post-login redirects.
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
      <circle cx="12" cy="7" r="3" />
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

export function Login() {
  const { route, navigate } = useRouter();
  const { login, error: authError, clearError, user } = useAuth();

  const [selectedPath, setSelectedPath] = useState(null); // "citizen" or "institution_admin"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(authError === SESSION_EXPIRED_MESSAGE);

  const next = sanitizeNext(route.query.next);
  const registerHref = next !== "/" ? `/register?next=${encodeURIComponent(next)}` : "/register";

  // Arriving on the login page resets any stale error from a previous
  // auth action (e.g. a failed registration), but keeps the calm
  // session-expired notice so users understand what happened.
  useEffect(() => {
    if (authError === SESSION_EXPIRED_MESSAGE) {
      setSessionExpired(true);
    } else {
      clearError();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const validateForm = () => {
    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Please enter your email address.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!password) nextErrors.password = "Please enter your password.";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    setServerError(null);
    setSessionExpired(false);
    const result = await login(email.trim(), password);
    setSubmitting(false);

    if (result.success) {
      // If user selected "Institution Admin" path, check for institution_admin membership
      if (selectedPath === "institution_admin") {
        // The user will be redirected to the default next page.
        // If they have institution_admin membership, they can access admin areas.
        // If not, they'll see appropriate messaging in those areas.
        // For now, just navigate to the intended destination.
        navigate(next);
      } else {
        navigate(next);
      }
    } else {
      setServerError(result.error);
    }
  };

  const handlePathSelect = (path) => {
    setSelectedPath(path);
    setErrors({});
    setServerError(null);
  };

  // Show path selection if no path selected yet
  if (!selectedPath) {
    return (
      <LoginPathSelection
        onPathSelect={handlePathSelect}
        showBackLink={true}
      />
    );
  }

  // Show login form after path selection
  return (
    <div className="auth-page">
      <div className="container-narrow">
        <div className="auth-card card">
          <div className="auth-header">
            <Link href="/login" className="back-link" style={{ marginBottom: "var(--space-6)" }}>
              ← Back
            </Link>
            <h1 className="auth-title">
              {selectedPath === "institution_admin" ? "Institution Admin Sign In" : "Welcome Back"}
            </h1>
            <p className="auth-subtitle">
              {selectedPath === "institution_admin"
                ? "Sign in to manage your institution"
                : "Sign in to your Aikyra account"}
            </p>
          </div>

          {sessionExpired && (
            <Alert type="info" title="Session Expired">
              <p>{SESSION_EXPIRED_MESSAGE}</p>
            </Alert>
          )}

          {!sessionExpired && serverError && (
            <Alert type="danger" title="Sign In Failed">
              <p>{serverError}</p>
            </Alert>
          )}

          <form onSubmit={handleSubmit} noValidate className="auth-form">
            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                Email <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="login-email"
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
                aria-describedby={errors.email ? "login-email-error" : undefined}
              />
              {errors.email && <div className="form-error-msg" role="alert" id="login-email-error">⚠️ {errors.email}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="login-password" className="form-label">
                Password <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <div className="password-field">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  className={`form-control ${errors.password ? "has-error" : ""}`}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={submitting}
                  required
                  autoComplete="current-password"
                  aria-describedby={errors.password ? "login-password-error" : undefined}
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-controls="login-password"
                  disabled={submitting}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
              {errors.password && <div className="form-error-msg" role="alert" id="login-password-error">⚠️ {errors.password}</div>}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Don't have an account? <Link href={registerHref} className="auth-link">Create one</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}