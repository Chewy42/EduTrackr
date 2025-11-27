import React from "react";
import { useLocation } from "react-router-dom";
import { FiMail, FiLock } from "react-icons/fi";
import { useAuth } from "./auth/AuthContext";
import AuthCard from "./components/AuthCard";
import AuthTabs from "./components/AuthTabs";
import TextField from "./components/TextField";
import SubmitButton from "./components/SubmitButton";
import EmailConfirmationNotice from "./components/EmailConfirmationNotice";
import Sidebar from "./components/Sidebar";
import ProgramEvaluationUpload from "./components/ProgramEvaluationUpload";
import ProgramEvaluationViewer from "./components/ProgramEvaluationViewer";
import OnboardingChat from "./components/OnboardingChat";
import ExploreChatLayout from "./components/ExploreChatLayout";
import { ProgressPage } from "./components/progress";

export default function App() {
  const location = useLocation();
  const {
    sessionState,
    mode,
    auth,
    loading,
    error,
    preferences,
    setMode,
    setField,
    handleSubmit,
    pendingEmail,
    resendConfirmation,
    signOut,
  } = useAuth();

  if (sessionState === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-muted text-text-primary px-4">
        <div className="text-sm font-medium tracking-[0.025em] text-center animate-pulse">
          Preparing your EduTrackr workspace...
        </div>
      </div>
    );
  }

  if (sessionState === "pending_confirmation") {
    return (
      <EmailConfirmationNotice
        email={pendingEmail || auth.email}
        onResend={resendConfirmation}
        onBack={signOut}
      />
    );
  }

  if (sessionState === "authenticated") {
    if (!preferences.hasProgramEvaluation) {
      return (
        <div className="flex h-screen w-screen overflow-hidden bg-surface-muted text-text-primary">
          <Sidebar />
          <main className="flex-1 h-full overflow-y-auto p-4 min-w-0">
            <div className="min-h-full flex items-center justify-center">
              <AuthCard
                title="Upload your program evaluation"
                subtitle="Start by uploading your official program evaluation PDF so EduTrackr can understand your path."
                maxWidth="max-w-7xl"
              >
                <ProgramEvaluationUpload />
              </AuthCard>
            </div>
          </main>
        </div>
      );
    }

    if (!preferences.onboardingComplete) {
      return <OnboardingChat />;
    }

    // Progress page uses full-width layout
    if (location.pathname === "/progress-page") {
      return (
        <div className="flex h-screen w-screen overflow-hidden bg-surface-muted text-text-primary">
          <Sidebar />
          <main className="flex-1 h-full overflow-y-auto min-w-0">
            <ProgressPage />
          </main>
        </div>
      );
    }

    if (location.pathname === "/exploration-assistant") {
      return (
        <div className="flex h-screen w-screen overflow-hidden bg-surface-muted text-text-primary">
          <Sidebar />
          <main className="flex-1 h-full overflow-y-auto min-w-0">
            <ExploreChatLayout />
          </main>
        </div>
      );
    }

    let title = "Welcome to EduTrackr";
    let subtitle = "You are signed in. Next: connect session state and onboarding.";
    let body: React.ReactNode = (
      <div className="text-sm text-text-secondary text-center py-1">
        This placeholder view confirms authentication flow is working.
      </div>
    );

    if (location.pathname === "/schedule-gen-home") {
      title = "Generate Your Schedule";
      subtitle = "Quickly build a balanced term around your preferences.";
      body = (
        <div className="text-sm text-text-secondary text-center py-1">
          Schedule generation tools and recommendations will appear here.
        </div>
      );
    } else if (location.pathname === "/settings") {
      title = "Settings";
      subtitle = "Adjust your EduTrackr experience.";
      body = <ProgramEvaluationViewer />;
    }

    return (
      <div className="flex h-screen w-screen overflow-hidden bg-surface-muted text-text-primary">
        <Sidebar />
        <main className="flex-1 h-full overflow-y-auto p-4 min-w-0">
          <div className="min-h-full flex items-center justify-center">
            <AuthCard
              title={title}
              subtitle={subtitle}
            >
              {body}
            </AuthCard>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted text-text-primary px-4 py-6">
      <div className="relative w-full max-w-xl">
        <AuthCard
          title="EduTrackr"
          subtitle="Sign in or create your account to continue"
        >
          <div className="mb-4 sm:mb-5">
            <AuthTabs mode={mode} onChange={setMode} />
          </div>
          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-4">
            <TextField
              label="Chapman Email"
              type="email"
              value={auth.email}
              onChange={(v) => setField("email", v)}
              placeholder="you@chapman.edu"
              autoComplete="email"
              required
              leftIcon={<FiMail size={16} />}
            />
            <TextField
              label="Password"
              type="password"
              value={auth.password}
              onChange={(v) => setField("password", v)}
              placeholder={
                mode === "sign_in"
                  ? "Enter your password"
                  : "Create a strong password"
              }
              autoComplete={
                mode === "sign_in" ? "current-password" : "new-password"
              }
              required
              leftIcon={<FiLock size={16} />}
            />
            {mode === "sign_up" ? (
              <TextField
                label="Confirm Password"
                type="password"
                value={auth.confirmPassword}
                onChange={(v) => setField("confirmPassword", v)}
                placeholder="Re-enter password"
                autoComplete="new-password"
                required
                leftIcon={<FiLock size={16} />}
              />
            ) : null}
            {error ? (
              <div className="text-sm text-danger text-center py-2 px-3 rounded-lg bg-[rgba(239,68,68,0.08)]">
                {error}
              </div>
            ) : null}
            <SubmitButton loading={loading}>
              {mode === "sign_in" ? "Sign In" : "Create Account"}
            </SubmitButton>
          </form>
        </AuthCard>
      </div>
    </div>
  );
}
