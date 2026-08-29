import React, { useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { UserMenu } from "./UserMenu.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function Navbar() {
  const { currentPath, navigate } = useRouter();
  const { isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => setMobileMenuOpen((prev) => !prev);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <header className="navbar" role="banner">
      <div className="container navbar-inner">
        {/* Brand */}
        <Link href="/" className="navbar-brand" onClick={closeMobileMenu} aria-label="Aikyra Home">
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

        {/* Navigation Links */}
        <nav className={`nav-links ${mobileMenuOpen ? "open" : ""}`} role="navigation" aria-label="Main Navigation">
          <Link href="/" className={`nav-link ${currentPath === "/" ? "active" : ""}`} onClick={closeMobileMenu}>
            Home
          </Link>
          <Link href="/challenges" className={`nav-link ${currentPath === "/challenges" ? "active" : ""}`} onClick={closeMobileMenu}>
            Community Challenges
          </Link>
          <Link href="/institutions" className={`nav-link ${currentPath.startsWith("/institutions") ? "active" : ""}`} onClick={closeMobileMenu}>
            Institutions
          </Link>
          <Link href="/projects" className={`nav-link ${currentPath.startsWith("/projects") ? "active" : ""}`} onClick={closeMobileMenu}>
            Approved Solutions
          </Link>
          <Link href="/impact" className={`nav-link ${currentPath === "/impact" ? "active" : ""}`} onClick={closeMobileMenu}>
            Impact
          </Link>
          {isAuthenticated && (
            <Link href="/workspace" className={`nav-link ${currentPath.startsWith("/workspace") ? "active" : ""}`} onClick={closeMobileMenu}>
              Workspace
            </Link>
          )}
          {mobileMenuOpen && (
            <button
              type="button"
              className="btn btn-primary btn-block"
              style={{ marginTop: "var(--space-2)" }}
              onClick={() => {
                closeMobileMenu();
                navigate("/report");
              }}
            >
              Report a Problem
            </button>
          )}
        </nav>

        {/* User Menu / Auth Actions */}
        <div className="nav-actions">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}