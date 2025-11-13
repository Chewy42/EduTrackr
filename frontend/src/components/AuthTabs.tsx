import React from 'react';
import type { AuthMode } from '../auth/AuthContext';

type AuthTabsProps = {
	mode: AuthMode;
	onChange: (mode: AuthMode) => void;
};

export default function AuthTabs({ mode, onChange }: AuthTabsProps) {
	const entries: { key: AuthMode; label: string }[] = [
		{ key: 'sign_in', label: 'Sign In' },
		{ key: 'sign_up', label: 'Sign Up' },
	];

	return (
		<div className={'bg-surface-muted/80 border border-slate-200/80 rounded-full p-1.5 flex items-center gap-1'}>
			{entries.map(({ key, label }) => {
				const active = mode === key;
				return (
					<button
						key={key}
						type="button"
						onClick={() => onChange(key)}
						className={
							'flex-1 rounded-full text-sm font-medium px-3 py-2.5 transition-colors duration-150 ' +
							(active
								? 'bg-white text-text-primary shadow-sm'
								: 'text-text-secondary hover:text-text-primary hover:bg-white/40')
						}
					>
						{label}
					</button>
				);
			})}
		</div>
	);
}
