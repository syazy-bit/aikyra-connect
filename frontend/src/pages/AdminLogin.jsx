import React, { useEffect, useState } from "react";
import { useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

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

export function AdminLogin() {
  const { route, navigate } = useRouter();
  const { login, logout, error: authError, clearError } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);

  const next = route.query.next || "/admin";

  useEffect(() => {
    clearError();
  }, [clearError]);

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
    const result = await login(email.trim(), password);
    setSubmitting(false);

    if (result.success) {
      const user = result.user;
      const isAdmin = user?.can_review_problems === true || user?.can_review_institutions === true;
      if (!isAdmin) {
        logout();
        setServerError("Admin access required. Your account does not have platform administration capabilities.");
        return;
      }
      navigate(next);
    } else {
      setServerError(result.error);
    }
  };

  return (
    <div className="admin-login-page">
      <div className="admin-login-container">
        <div className="admin-login-card card">
          <div className="admin-login-header">
            <div className="admin-login-brand">
              <span className="admin-login-brand-mark" aria-hidden="true">A</span>
              <span className="admin-login-brand-title">Aikyra Admin</span>
            </div>
            <h1 className="admin-login-subtitle">Platform Administration Portal</h1>
            <div className="admin-login-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Authorized platform administrators only</span>
            </div>
          </div>

          {serverError && (
            <Alert type="danger" title="Authentication Notice">
              <p>{serverError}</p>
            </Alert>
          )}

          <form onSubmit={handleSubmit} noValidate className="admin-login-form">
            <div className="form-group">
              <label htmlFor="admin-login-email" className="form-label">
                Administrator Email <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="admin-login-email"
                name="email"
                type="email"
                className={`form-control ${errors.email ? "has-error" : ""}`}
                placeholder="admin@aikyra.dev"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
                required
                autoComplete="email"
                autoFocus
                aria-describedby={errors.email ? "admin-login-email-error" : undefined}
              />
              {errors.email && <div className="form-error-msg" role="alert" id="admin-login-email-error">⚠️ {errors.email}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="admin-login-password" className="form-label">
                Password <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <div className="password-field">
                <input
                  id="admin-login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  className={`form-control ${errors.password ? "has-error" : ""}`}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={submitting}
                  required
                  autoComplete="current-password"
                  aria-describedby={errors.password ? "admin-login-password-error" : undefined}
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-controls="admin-login-password"
                  disabled={submitting}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
              {errors.password && <div className="form-error-msg" role="alert" id="admin-login-password-error">⚠️ {errors.password}</div>}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block admin-login-submit"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign in to Admin Portal</span>
              )}
            </button>
          </form>

          <div className="admin-login-footer-text">
            <small>Aikyra Societal Innovation Platform · Administration Console</small>
          </div>
        </div>
      </div>
    </div>
  );
}