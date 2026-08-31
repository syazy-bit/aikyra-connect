import React from "react";
import { RouterProvider, useRouter, Link } from "./context/RouterContext.jsx";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProtectedRoute } from "./components/ProtectedRoute.jsx";
import { Navbar } from "./components/Navbar.jsx";
import { Footer } from "./components/Footer.jsx";
import { Home } from "./pages/Home.jsx";
import { ReportProblem } from "./pages/ReportProblem.jsx";
import { Challenges } from "./pages/Challenges.jsx";
import { ChallengeDetail } from "./pages/ChallengeDetail.jsx";
import { Institutions } from "./pages/Institutions.jsx";
import { InstitutionDetail } from "./pages/InstitutionDetail.jsx";
import { RegisterInstitution } from "./pages/RegisterInstitution.jsx";
import { InstitutionAdminOnboarding } from "./pages/InstitutionAdminOnboarding.jsx";
import { Login } from "./pages/Login.jsx";
import { Register } from "./pages/Register.jsx";
import { Workspace } from "./pages/Workspace.jsx";
import { TeamDetail } from "./pages/TeamDetail.jsx";
import { ProposalDetail } from "./pages/ProposalDetail.jsx";
import { Projects } from "./pages/Projects.jsx";
import { ProjectDetail } from "./pages/ProjectDetail.jsx";
import { ProjectFunding } from "./pages/ProjectFunding.jsx";
import { ProjectFundingManage } from "./pages/ProjectFundingManage.jsx";
import { ProjectFundingDemoPayment } from "./pages/ProjectFundingDemoPayment.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";

function AppContent() {
  const { route } = useRouter();

  const renderPage = () => {
    switch (route.name) {
      case "home":
        return <Home />;
      case "login":
        return <Login />;
      case "register":
        return <Register />;
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
        return (
          <ProtectedRoute>
            <RegisterInstitution />
          </ProtectedRoute>
        );
      case "institution-admin-onboarding":
        return <InstitutionAdminOnboarding />;
      case "workspace":
        return (
          <ProtectedRoute>
            <Workspace />
          </ProtectedRoute>
        );
      case "team-detail":
        return (
          <ProtectedRoute>
            <TeamDetail />
          </ProtectedRoute>
        );
      case "proposal-detail":
        return (
          <ProtectedRoute>
            <ProposalDetail />
          </ProtectedRoute>
        );
      case "projects":
        return <Projects />;
      case "project-detail":
        return <ProjectDetail />;
      case "project-funding":
        return <ProjectFunding />;
      case "project-funding-demo-payment":
        return (
          <ProtectedRoute>
            <ProjectFundingDemoPayment />
          </ProtectedRoute>
        );
      case "project-funding-manage":
        return (
          <ProtectedRoute>
            <ProjectFundingManage />
          </ProtectedRoute>
        );
      case "dashboard":
        return <Dashboard />;
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
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </RouterProvider>
  );
}