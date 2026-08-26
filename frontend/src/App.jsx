import React from "react";
import { RouterProvider, useRouter, Link } from "./context/RouterContext.jsx";
import { Navbar } from "./components/Navbar.jsx";
import { Footer } from "./components/Footer.jsx";
import { Home } from "./pages/Home.jsx";
import { ReportProblem } from "./pages/ReportProblem.jsx";
import { Challenges } from "./pages/Challenges.jsx";
import { ChallengeDetail } from "./pages/ChallengeDetail.jsx";
import { Institutions } from "./pages/Institutions.jsx";
import { InstitutionDetail } from "./pages/InstitutionDetail.jsx";
import { RegisterInstitution } from "./pages/RegisterInstitution.jsx";

function AppContent() {
  const { route } = useRouter();

  const renderPage = () => {
    switch (route.name) {
      case "home":
        return <Home />;
      case "report":
        return <ReportProblem />;
      case "challenges":
        return <Challenges />;
      case "challenge-detail":
        return <ChallengeDetail />;
      case "institutions":
        return <Institutions />;
      case "institution-detail":
        return <InstitutionDetail />;
      case "institution-register":
        return <RegisterInstitution />;
      default:
        return (
          <main className="container-narrow" style={{ padding: "var(--space-16) var(--space-4)", textAlign: "center" }}>
            <h1 style={{ fontSize: "2rem", marginBottom: "var(--space-3)" }}>Page Not Found</h1>
            <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              The page you are looking for does not exist or has been moved.
            </p>
            <Link href="/" className="btn btn-primary">
              Return to Home
            </Link>
          </main>
        );
    }
  };

  return (
    <>
      <Navbar />
      <main id="main-content" role="main" style={{ flexGrow: 1 }}>
        {renderPage()}
      </main>
      <Footer />
    </>
  );
}

export default function App() {
  return (
    <RouterProvider>
      <AppContent />
    </RouterProvider>
  );
}
