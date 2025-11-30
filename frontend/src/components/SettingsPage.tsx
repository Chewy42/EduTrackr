import React from "react";
import { FiLogOut } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext";
import AuthCard from "./AuthCard";
import ProgramEvaluationViewer from "./ProgramEvaluationViewer";

export default function SettingsPage() {
  const { signOut } = useAuth();

  return (
    <div className="min-h-full flex items-center justify-center py-8">
      <AuthCard
        title="Settings"
        subtitle="Adjust your EduTrackr experience."
        maxWidth="max-w-3xl"
      >
        <div className="space-y-8">
          <ProgramEvaluationViewer />

          <div className="pt-8 border-t border-slate-200/70">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Account</h3>
            <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-200/70 bg-white shadow-sm">
              <div>
                <div className="font-medium text-text-primary">Sign Out</div>
                <div className="text-sm text-text-secondary">
                  Sign out of your account on this device.
                </div>
              </div>
              <button
                onClick={signOut}
                className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-danger bg-red-50 hover:bg-red-100 transition-colors duration-150"
              >
                <FiLogOut className="text-lg" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </AuthCard>
    </div>
  );
}
