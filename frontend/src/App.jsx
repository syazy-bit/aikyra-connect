import React from "react";
import { RouterProvider, useRouter, Link } from "./context/RouterContext.jsx";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProtectedRoute } from "./components/ProtectedRoute.jsx";
import { AdminProtectedRoute } from "./components/AdminProtectedRoute.jsx";
import { AdminLayout } from "./components/AdminLayout.jsx";
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
import { AdminOverview } from "./pages/AdminOverview.jsx";
import { ProblemReviewQueue } from "./pages/ProblemReviewQueue.jsx";
import { ProblemReviewDetail } from "./pages/ProblemReviewDetail.jsx";
import { InstitutionReviewQueue } from "./pages/InstitutionReviewQueue.jsx";
import { InstitutionReviewDetail } from "./pages/InstitutionReviewDetail.jsx";
import { AdminLogin } from "./pages/AdminLogin.jsx";

function PublicLayout({ children }) {
  return (
    <>
      <Navbar />
      <main id="main-content" role="main" style={{ flexGrow: 1 }}>
        {children}
      </main>
      <Footer />
    </>
  );
}

function AppContent() {
  const { route } = useRouter();

  // 1. Admin Login - Standalone authentication screen (NO Navbar, Footer, Sidebar, Header)
  if (route.name === "admin-login") {
    return <AdminLogin />;
  }

  // 2. Admin Console Routes - Isolated layout tree with AdminLayout + AdminProtectedRoute
  if (route.name === "admin-overview") {
    return (
      <AdminProtectedRoute requiredCapability="any">
        <AdminLayout>
          <AdminOverview />
        </AdminLayout>
      </AdminProtectedRoute>
    );
  }

  if (route.name === "admin-problems") {
    return (
      <AdminProtectedRoute requiredCapability="can_review_problems">
        <AdminLayout>
          <ProblemReviewQueue />
        </AdminLayout>
      </AdminProtectedRoute>
    );
  }

  if (route.name === "admin-problem-detail") {
    return (
      <AdminProtectedRoute requiredCapability="can_review_problems">
        <AdminLayout>
          <ProblemReviewDetail />
        </AdminLayout>
      </AdminProtectedRoute>
    );
  }

  if (route.name === "admin-institutions") {
    return (
      <AdminProtectedRoute requiredCapability="can_review_institutions">
        <AdminLayout>
          <InstitutionReviewQueue />
        </AdminLayout>
      </AdminProtectedRoute>
    );
  }

  if (route.name === "admin-institution-detail") {
    return (
      <AdminProtectedRoute requiredCapability="can_review_institutions">
        <AdminLayout>
          <InstitutionReviewDetail />
        </AdminLayout>
      </AdminProtectedRoute>
    );
  }

  // 3. Public Routes - Rendered inside PublicLayout (Navbar + main + Footer)
  const renderPublicPage = () => {
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
          <div className="container-narrow" style={{ padding: "var(--space-16) var(--space-4)", textAlign: "center" }}>
            <h1 style={{ fontSize: "2rem", marginBottom: "var(--space-3)" }}>Page Not Found</h1>
            <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              The page you are looking for does not exist or has been moved.
            </p>
            <Link href="/" className="btn btn-primary">
              Return to Home
            </Link>
          </div>
        );
    }
  };

  return <PublicLayout>{renderPublicPage()}</PublicLayout>;
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