import React from "react";
import { FiMail, FiLock } from "react-icons/fi";
import { useAuth } from "./auth/AuthContext";
import AuthCard from "./components/AuthCard";
import AuthTabs from "./components/AuthTabs";
import TextField from "./components/TextField";
import SubmitButton from "./components/SubmitButton";
import Box from "@mui/material/Box";

export default function App() {
  const {
    sessionState,
    mode,
    auth,
    loading,
    error,
    setMode,
    setField,
    handleSubmit,
  } = useAuth();

  if (sessionState === "checking") {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default', color: 'text.primary' }}>
        <Box sx={{ animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite', fontSize: '0.875rem', fontWeight: 500, letterSpacing: '0.025em' }}>
          Preparing your EduTrackr workspace...
        </Box>
      </Box>
    );
  }

  if (sessionState === "authenticated") {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default', color: 'text.primary', px: 2 }}>
        <AuthCard
          title="Welcome to EduTrackr"
          subtitle="You are signed in. Next: connect session state and onboarding."
        >
          <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
            This placeholder view confirms authentication flow is working.
          </Box>
        </AuthCard>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default', color: 'text.primary', px: 2 }}>
      <Box sx={{ position: 'relative', py: 3 }}>
        <Box sx={{ position: 'relative' }}>
          <AuthCard
            title="EduTrackr"
            subtitle="Sign in or create your account to continue"
            footer={
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'text.secondary' }}>
                <span>Protected for verified @chapman.edu accounts.</span>
                <Box sx={(theme) => ({
                  px: 1,
                  py: 0.5,
                  borderRadius: '9999px',
                  bgcolor: 'primary.light',
                  color: 'primary.dark',
                  border: '1px solid',
                  borderColor: 'primary.main',
                  fontSize: '0.625rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  backgroundColor: theme.palette.action.hover,
                })}>
                  Auth ready
                </Box>
              </Box>
            }
          >
            <Box sx={{ mb: { xs: 2.5, sm: 3 } }}>
              <AuthTabs mode={mode} onChange={setMode} />
            </Box>
            <Box
              component="form"
              onSubmit={handleSubmit}
              sx={{
                '& > * + *': { mt: { xs: 2.5, sm: 3 } },
              }}
            >
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
                placeholder={mode === "sign_in" ? "Enter your password" : "Create a strong password"}
                autoComplete={mode === "sign_in" ? "current-password" : "new-password"}
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
                <Box sx={{ fontSize: '0.75rem', color: 'error.main' }}>{error}</Box>
              ) : null}
              <SubmitButton loading={loading}>
                {mode === "sign_in" ? "Sign In" : "Create Account"}
              </SubmitButton>
            </Box>
          </AuthCard>
        </Box>
      </Box>
    </Box>
  );
}
