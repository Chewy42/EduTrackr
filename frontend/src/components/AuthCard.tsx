import React from 'react';

type AuthCardProps = {
	title: string;
	subtitle?: string;
	children: React.ReactNode;
	footer?: React.ReactNode;
};

export default function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
	return (
		<div className={'w-full max-w-xl mx-auto px-4 sm:px-4'}>
			<div className={'relative bg-surface rounded-3xl shadow-card border border-slate-100/70'}>
				<div className={'px-5 pt-8 pb-6 sm:px-10 sm:pt-10 text-center'}>
					<h1 className={'text-2xl sm:text-3xl font-bold tracking-tight text-text-primary mb-2.5'}>
						{title}
					</h1>
					{subtitle ? (
						<p className={'mx-auto max-w-md text-sm sm:text-[0.95rem] leading-relaxed text-text-secondary'}>
							{subtitle}
						</p>
					) : null}
				</div>

				<div className={'h-px bg-slate-200/70 mx-5 sm:mx-10'} />

				<div className={'px-5 pt-8 pb-8 sm:px-10 sm:pb-10'}>
					<div className={'space-y-6'}>
						{children}
					</div>
				</div>

				{footer ? (
					<>
						<div className={'h-px bg-slate-200/70 mx-5 sm:mx-10'} />
						<div className={'px-5 pt-5 pb-8 sm:px-10 sm:pt-6 sm:pb-10'}>
							<div className={'text-center text-sm text-text-secondary'}>
								{footer}
							</div>
						</div>
					</>
				) : null}
			</div>
		</div>
	);
}