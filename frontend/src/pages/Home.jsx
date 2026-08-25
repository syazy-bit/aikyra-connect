import React, { useState, useEffect } from "react";
import { Link } from "../context/RouterContext.jsx";
import { listChallenges } from "../services/challengeService.js";
import { ChallengeCard } from "../components/ChallengeCard.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

export function Home() {
  const [recentChallenges, setRecentChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadRecentChallenges() {
      try {
        setLoading(true);
        setError(null);
        // Fetch latest 3 challenges
        const data = await listChallenges({ skip: 0, limit: 3 });
        if (mounted) {
          setRecentChallenges(data?.items ?? []);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load recent challenges.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadRecentChallenges();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="home-page">
      {/* ====================================================================
          Hero Section
          ==================================================================== */}
      <section className="hero-section" aria-labelledby="hero-heading">
        <div className="container">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="hero-badge-dot" aria-hidden="true" />
              Collaborative Societal Innovation
            </div>

            <h1 id="hero-heading" className="hero-title">
              Transforming Community Problems into Real-World Solutions.
            </h1>

            <p className="hero-lead">
              Aikyra bridges the gap between citizens experiencing everyday societal
              challenges and the university researchers, student innovators, and industry
              partners capable of building lasting, measurable solutions.
            </p>

            <div className="hero-actions">
              <Link href="/report" className="btn btn-primary btn-lg">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Report a Problem
              </Link>

              <Link href="/challenges" className="btn btn-outline btn-lg">
                Explore Community Challenges
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          The Aikyra Ecosystem Section (Why Aikyra Exists)
          ==================================================================== */}
      <section className="ecosystem-section" aria-labelledby="ecosystem-heading">
        <div className="container">
          <div className="section-header">
            <span className="section-kicker">The Aikyra Ecosystem</span>
            <h2 id="ecosystem-heading" className="section-title">
              Not Just a Complaint Portal. A Path to Solutions.
            </h2>
            <p className="section-description">
              Most community complaints end up in a closed ticket with no action.
              Aikyra connects ground-level realities directly with academic talent,
              research expertise, and industry resources.
            </p>
          </div>

          <div className="ecosystem-flow">
            {/* Step 1 */}
            <div className="ecosystem-card">
              <div className="ecosystem-step">01</div>
              <div className="ecosystem-role">Citizens & Communities</div>
              <h3 className="ecosystem-card-title">Bring Real Problems to Light</h3>
              <p className="ecosystem-card-text">
                Citizens report acute local challenges — from water management and rural
                healthcare to waste processing and educational access.
              </p>
            </div>

            <div className="ecosystem-arrow" aria-hidden="true">→</div>

            {/* Step 2 */}
            <div className="ecosystem-card">
              <div className="ecosystem-step">02</div>
              <div className="ecosystem-role">Aikyra Platform</div>
              <h3 className="ecosystem-card-title">Structured Problem Understanding</h3>
              <p className="ecosystem-card-text">
                Challenges are structured with clear context, severity, and domain focus,
                turning raw issues into actionable engineering and societal questions.
              </p>
            </div>

            <div className="ecosystem-arrow" aria-hidden="true">→</div>

            {/* Step 3 */}
            <div className="ecosystem-card">
              <div className="ecosystem-step">03</div>
              <div className="ecosystem-role">Universities & Students</div>
              <h3 className="ecosystem-card-title">Research & Student Innovation</h3>
              <p className="ecosystem-card-text">
                Academic faculties, student research labs, and innovators adopt problems as
                capstone projects, research initiatives, and hackathon challenges.
              </p>
            </div>

            <div className="ecosystem-arrow" aria-hidden="true">→</div>

            {/* Step 4 */}
            <div className="ecosystem-card">
              <div className="ecosystem-step">04</div>
              <div className="ecosystem-role">Industry & Mentors</div>
              <h3 className="ecosystem-card-title">Resources & Scaling</h3>
              <p className="ecosystem-card-text">
                Startups, industry mentors, and CSR partners support active student teams
                with technical guidance, prototyping resources, and deployment support.
              </p>
            </div>

            <div className="ecosystem-arrow" aria-hidden="true">→</div>

            {/* Step 5 */}
            <div className="ecosystem-card ecosystem-card-highlight">
              <div className="ecosystem-step">05</div>
              <div className="ecosystem-role">Measurable Social Impact</div>
              <h3 className="ecosystem-card-title">Deployed Solutions</h3>
              <p className="ecosystem-card-text">
                Validated prototypes are deployed directly in the community, creating
                tangible, transparent, and verifiable social progress.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          Recent Community Challenges
          ==================================================================== */}
      <section className="recent-challenges-section" aria-labelledby="recent-heading">
        <div className="container">
          <div className="section-header-flex">
            <div>
              <span className="section-kicker">Ground Realities</span>
              <h2 id="recent-heading" className="section-title">
                Recent Community Challenges
              </h2>
            </div>
            <Link href="/challenges" className="btn btn-outline-primary">
              View All Challenges →
            </Link>
          </div>

          {loading && <LoadingSpinner message="Fetching community challenges from database..." />}

          {error && (
            <div className="alert alert-warning" role="status">
              <div>{error}</div>
            </div>
          )}

          {!loading && !error && recentChallenges.length === 0 && (
            <div className="empty-feed-card">
              <p style={{ marginBottom: "var(--space-4)" }}>
                No challenges have been reported in the database yet.
              </p>
              <Link href="/report" className="btn btn-primary">
                Report the First Problem
              </Link>
            </div>
          )}

          {!loading && !error && recentChallenges.length > 0 && (
            <div className="challenges-grid">
              {recentChallenges.map((challenge) => (
                <ChallengeCard key={challenge.id} challenge={challenge} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ====================================================================
          Civic Call to Action
          ==================================================================== */}
      <section className="cta-section" aria-labelledby="cta-heading">
        <div className="container">
          <div className="cta-card">
            <h2 id="cta-heading" className="cta-title">
              Have you noticed an urgent problem in your area?
            </h2>
            <p className="cta-text">
              Every real problem brought to Aikyra gives students and researchers
              the opportunity to build meaningful, community-tested solutions.
            </p>
            <Link href="/report" className="btn btn-primary btn-lg">
              Report a Community Problem
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
