import React, { useState, useEffect } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { UserMenu } from "./UserMenu.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function Navbar() {
  const { currentPath, navigate } = useRouter();
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => setMobileMenuOpen((prev) => !prev);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  const handleMobileLogout = () => {
    closeMobileMenu();
    logout();
    navigate("/");
  };

  // Close the mobile menu on Escape for keyboard users.
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") closeMobileMenu();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileMenuOpen]);

  // Auth state is only ever read from AuthContext — never hardcoded.
  const isHome = currentPath === "/";
  const displayName = user?.full_name || user?.email || "Account";

  return (
    <header className="navbar" role="banner">
      <div className="container navbar-inner">
        {/* Brand — always returns to the home page. */}
        <Link
          href="/"
          className={`navbar-brand${isHome ? " is-active" : ""}`}
          onClick={closeMobileMenu}
          aria-label="Aikyra Home"
          aria-current={isHome ? "page" : undefined}
        >
          <div className="brand-mark" aria-hidden="true">A</div>
          <div className="brand-text">
            <span className="brand-title">AIKYRA</span>
            <span className="brand-subtitle">Many Minds. One Impact.</span>
          </div>
        </Link>

        {/* Mobile Toggle Button */}
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={toggleMobileMenu}
          aria-expanded={mobileMenuOpen}
          aria-controls="primary-navigation"
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {mobileMenuOpen ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <>
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </>
            )}
          </svg>
        </button>

        {/* Navigation Links (collapses into the mobile menu below the breakpoint) */}
        <nav id="primary-navigation" className={`nav-links ${mobileMenuOpen ? "open" : ""}`} aria-label="Main Navigation">
          <Link href="/challenges" className={`nav-link ${currentPath === "/challenges" ? "active" : ""}`} onClick={closeMobileMenu}>
            Challenges
          </Link>
          <Link href="/projects" className={`nav-link ${currentPath.startsWith("/projects") ? "active" : ""}`} onClick={closeMobileMenu}>
            Approved Solutions
          </Link>
          <Link href="/impact" className={`nav-link ${currentPath === "/impact" ? "active" : ""}`} onClick={closeMobileMenu}>
            Impact
          </Link>
          <Link href="/institutions" className={`nav-link ${currentPath.startsWith("/institutions") ? "active" : ""}`} onClick={closeMobileMenu}>
            Institutions
          </Link>
          {isAuthenticated && (
            <Link href="/workspace" className={`nav-link ${currentPath.startsWith("/workspace") ? "active" : ""}`} onClick={closeMobileMenu}>
              Workspace
            </Link>
          )}

          {/* Mobile-only: report + authentication actions */}
          <div className="mobile-nav-extra">
            <button
              type="button"
              className="btn btn-primary btn-block"
              onClick={() => {
                closeMobileMenu();
                navigate("/report");
              }}
            >
              Report a Problem
            </button>

            <div className="mobile-nav-auth">
              {isAuthenticated ? (
                <>
                  <div className="mobile-nav-user">
                    <span className="user-avatar" aria-hidden="true">
                      {displayName.charAt(0).toUpperCase()}
                    </span>
                    <span className="mobile-nav-user-name">{displayName}</span>
                  </div>
                  <button type="button" className="btn btn-outline btn-block" onClick={handleMobileLogout}>
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className="btn btn-outline btn-block" onClick={closeMobileMenu}>
                    Login
                  </Link>
                  <Link href="/register" className="btn btn-primary btn-block" onClick={closeMobileMenu}>
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </nav>

        {/* Desktop User Menu / Auth Actions */}
        <div className="nav-actions">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}