import React from "react";

export default function AuthenticatedView() {
	return (
		<div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
			<div className="px-8 py-6 rounded-2xl bg-surface-elevated shadow-2xl border border-slate-800/80">
				<h1 className="text-2xl font-semibold tracking-tight mb-1">Welcome to EduTrackr</h1>
				<p className="text-sm text-slate-400">
					You are signed in. Next: wire this view to Supabase session state and onboarding.
				</p>
			</div>
		</div>
	);
}


