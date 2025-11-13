import React from 'react';

type PasswordStrengthIndicatorProps = {
	password: string;
};

const requirements = [
	{ label: 'At least 7 characters', test: (value: string) => value.length >= 7 },
	{ label: 'Contains a number', test: (value: string) => /\d/.test(value) },
	{ label: 'Contains an uppercase letter', test: (value: string) => /[A-Z]/.test(value) },
	{ label: 'Contains a special character', test: (value: string) => /[^A-Za-z0-9]/.test(value) },
];

const strengthLabel = ['Very weak', 'Needs work', 'Getting there', 'Almost there', 'Strong'];

export default function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
	const satisfied = requirements.map((req) => req.test(password));
	const score = satisfied.filter(Boolean).length;
	const percentage = (score / requirements.length) * 100;
	const label = strengthLabel[score];

	return (
		<div className="mt-3">
			<div className="flex items-center justify-between mb-1">
				<span className="text-[0.7rem] font-semibold tracking-tight text-text-secondary">
					Password strength
				</span>
				<span className="text-[0.7rem] font-semibold tracking-tight" style={{ color: score <= 1 ? '#ef4444' : score === 2 ? '#f97316' : score === 3 ? '#84cc16' : '#22c55e' }}>
					{label}
				</span>
			</div>
			<div className="h-2 rounded-full bg-slate-900/5 overflow-hidden relative">
				<div
					className="h-full rounded-full shadow-md transition-[width] duration-200"
					style={{
						width: `${password ? Math.max(8, percentage) : 0}%`,
						background:
							'linear-gradient(90deg, #ef4444 0%, #f97316 35%, #84cc16 70%, #22c55e 100%)',
						boxShadow: '0 4px 12px rgba(15, 118, 110, 0.25)',
					}}
				/>
			</div>
			<div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
				{requirements.map((req, index) => (
					<div
						key={req.label}
						className="flex items-center min-w-fit"
					>
						<span
							className="w-2 h-2 rounded-full mr-1.5"
							style={{
								backgroundColor: satisfied[index]
									? '#22c55e'
									: 'rgba(15, 23, 42, 0.2)',
							}}
						/>
						<span
							className="text-[0.7rem] font-medium"
							style={{
								color: satisfied[index] ? '#0f172a' : '#64748b',
							}}
						>
							{req.label}
						</span>
					</div>
				))}
			</div>
		</div>
	);
}
