import React from "react";
import { FiMail, FiLock } from "react-icons/fi";
import TextField from "./TextField";
import SubmitButton from "./SubmitButton";
import { AuthMode } from "../auth/AuthContext";

type Props = {
  mode: AuthMode;
  email: string;
  password: string;
  confirmPassword: string;
  error: string | null;
  loading: boolean;
  setField: (field: "email" | "password" | "confirmPassword", value: string) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
};

export default function AuthForm({
  mode,
  email,
  password,
  confirmPassword,
  error,
  loading,
  setField,
  onSubmit,
}: Props) {
  return (
    <form onSubmit={onSubmit} className={"mt-2 space-y-4 sm:space-y-5"}>
      <TextField
        label="Email"
        type="email"
        value={email}
        onChange={(v) => setField("email", v)}
        placeholder="you@chapman.edu"
        leftIcon={<FiMail size={16} />}
      />

      <TextField
        label="Password"
        type="password"
        value={password}
        onChange={(v) => setField("password", v)}
        placeholder={mode === "sign_in" ? "Enter your password" : "Create a strong password"}
        leftIcon={<FiLock size={16} />}
      />

      {mode === "sign_up" && (
        <TextField
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={(v) => setField("confirmPassword", v)}
          placeholder="Re-enter password"
          leftIcon={<FiLock size={16} />}
        />
      )}

      {error && (
        <p className={"mt-1 text-xs text-danger text-center"}>{error}</p>
      )}

      <div className={"pt-1"}>
        <SubmitButton loading={loading}>
          {mode === "sign_in" ? "Sign In" : "Create Account"}
        </SubmitButton>
      </div>
    </form>
  );
}
