import React from "react";
import { Link } from "../context/RouterContext.jsx";

export function Footer() {
  return (
    <footer className="footer" role="contentinfo">
      <div className="container">
        <div className="footer-grid">
          {/* Brand & Purpose */}
          <div className="footer-brand">
            <div className="footer-brand-title">AIKYRA</div>
            <div className="footer-brand-tagline">Many Minds. One Impact.</div>
            <p className="footer-desc">
              A collaborative societal innovation platform connecting citizen
              problems directly with student innovators, university faculty,
              and industry resources to build measurable solutions.
            </p>
          </div>

          {/* Navigation Links */}
          <div>
            <div className="footer-heading">Platform</div>
            <ul className="footer-links">
              <li>
                <Link href="/" className="footer-link">Home</Link>
              </li>
              <li>
                <Link href="/challenges" className="footer-link">Community Challenges</Link>
              </li>
              <li>
                <Link href="/report" className="footer-link">Report a Problem</Link>
              </li>
            </ul>
          </div>

          {/* Civic Pledge */}
          <div>
            <div className="footer-heading">Civic Commitment</div>
            <p className="footer-desc" style={{ fontSize: "0.875rem" }}>
              Every problem brought to Aikyra is treated as an opportunity for
              community collaboration and transparent action. Not a black hole ticket system.
            </p>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="footer-bottom">
          <div>&copy; {new Date().getFullYear()} Aikyra Platform. Built for Societal Innovation.</div>
          <div>Citizen Experience Vertical Slice (Phase 1)</div>
        </div>
      </div>
    </footer>
  );
}
