import React from "react";
import { Link } from "../context/RouterContext.jsx";

function UserIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function InstitutionIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 21H2" />
      <path d="M6 21V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v14" />
      <path d="M6 11h12" />
      <path d="M10 21V7" />
      <path d="M14 21V7" />
      <path d="M18 21V7" />
    </svg>
  );
}

export function OnboardingPathSelection({
  title = "How are you using Aikyra?",
  subtitle = "Choose the path that best describes you.",
  onPathSelect,
  showBackLink = true,
  backHref = "/",
  backText = "← Back to Home",
}) {
  return (
    <div className="auth-page">
      <div className="container-narrow">
        <div className="auth-card card">
          <div className="auth-header">
            {showBackLink && (
              <Link href={backHref} className="back-link" style={{ marginBottom: "var(--space-6)" }}>
                {backText}
              </Link>
            )}
            <h1 className="auth-title">{title}</h1>
            <p className="auth-subtitle">{subtitle}</p>
          </div>

          <div className="onboarding-paths" role="group" aria-labelledby="onboarding-title">
            <button
              type="button"
              className="onboarding-path-card"
              onClick={() => onPathSelect("citizen")}
              aria-label="Continue as Citizen — Report civic problems, discover projects and participate in Aikyra"
            >
              <div className="onboarding-path-icon">
                <UserIcon />
              </div>
              <div className="onboarding-path-content">
                <h2 className="onboarding-path-title">Citizen</h2>
                <p className="onboarding-path-description">
                  Report civic problems, discover projects and participate in Aikyra.
                </p>
              </div>
              <span className="onboarding-path-chevron" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </span>
            </button>

            <button
              type="button"
              className="onboarding-path-card"
              onClick={() => onPathSelect("institution_admin")}
              aria-label="Continue as Institution Admin — Register and manage your institution on Aikyra"
            >
              <div className="onboarding-path-icon">
                <InstitutionIcon />
              </div>
              <div className="onboarding-path-content">
                <h2 className="onboarding-path-title">Institution Admin</h2>
                <p className="onboarding-path-description">
                  Register and manage your institution on Aikyra.
                </p>
              </div>
              <span className="onboarding-path-chevron" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function LoginPathSelection({ onPathSelect, showBackLink = true }) {
  return (
    <div className="auth-page">
      <div className="container-narrow">
        <div className="auth-card card">
          <div className="auth-header">
            {showBackLink && (
              <Link href="/" className="back-link" style={{ marginBottom: "var(--space-6)" }}>
                ← Back to Home
              </Link>
            )}
            <h1 className="auth-title">Welcome Back</h1>
            <p className="auth-subtitle">How would you like to sign in?</p>
          </div>

          <div className="onboarding-paths" role="group" aria-labelledby="login-path-title">
            <button
              type="button"
              className="onboarding-path-card"
              onClick={() => onPathSelect("citizen")}
              aria-label="Continue as Citizen — Sign in to your Aikyra account"
            >
              <div className="onboarding-path-icon">
                <UserIcon />
              </div>
              <div className="onboarding-path-content">
                <h2 className="onboarding-path-title">Continue as Citizen</h2>
                <p className="onboarding-path-description">
                  Sign in to your Aikyra account to report problems, discover projects, and participate.
                </p>
              </div>
              <span className="onboarding-path-chevron" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </span>
            </button>

            <button
              type="button"
              className="onboarding-path-card"
              onClick={() => onPathSelect("institution_admin")}
              aria-label="Continue as Institution Admin — Sign in to manage your institution"
            >
              <div className="onboarding-path-icon">
                <InstitutionIcon />
              </div>
              <div className="onboarding-path-content">
                <h2 className="onboarding-path-title">Continue as Institution Admin</h2>
                <p className="onboarding-path-description">
                  Sign in to manage your institution, review proposals, and access admin tools.
                </p>
              </div>
              <span className="onboarding-path-chevron" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}