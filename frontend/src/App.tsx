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
      <Box sx={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        bgcolor: 'background.default', 
        color: 'text.primary',
        px: 2
      }}>
        <Box sx={{ 
          animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite', 
          fontSize: '0.9375rem', 
          fontWeight: 500, 
          letterSpacing: '0.025em',
          textAlign: 'center'
        }}>
          Preparing your EduTrackr workspace...
        </Box>
      </Box>
    );
  }

  if (sessionState === "authenticated") {
    return (
      <Box sx={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        bgcolor: 'background.default', 
        color: 'text.primary', 
        px: 2
      }}>
        <AuthCard
          title="Welcome to EduTrackr"
          subtitle="You are signed in. Next: connect session state and onboarding."
        >
          <Box sx={{ 
            fontSize: '0.875rem', 
            color: 'text.secondary',
            textAlign: 'center',
            py: 1
          }}>
            This placeholder view confirms authentication flow is working.
          </Box>
        </AuthCard>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      bgcolor: 'background.default', 
      color: 'text.primary', 
      px: 2,
      py: 3
    }}>
      <Box sx={{ position: 'relative', width: '100%', maxWidth: 560 }}>
        <AuthCard
          title="EduTrackr"
          subtitle="Sign in or create your account to continue"
        >
          <Box sx={{ mb: { xs: 3, sm: 4 } }}>
            <AuthTabs mode={mode} onChange={setMode} />
          </Box>
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
              '& > * + *': { mt: { xs: 3, sm: 3.5 } },
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
            <Box sx={{ mb: 1 }}>
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
            </Box>
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
              <Box sx={{ 
                fontSize: '0.875rem', 
                color: 'error.main',
                textAlign: 'center',
                py: 1,
                px: 2,
                borderRadius: 2,
                bgcolor: 'rgba(239, 68, 68, 0.1)'
              }}>{error}</Box>
            ) : null}
            <SubmitButton loading={loading}>
              {mode === "sign_in" ? "Sign In" : "Create Account"}
            </SubmitButton>
          </Box>
        </AuthCard>
      </Box>
    </Box>
  );
}
