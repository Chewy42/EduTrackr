import React from 'react';

type AuthCardProps = {
	title: string;
	subtitle?: string;
	children: React.ReactNode;
	footer?: React.ReactNode;
    maxWidth?: string;
};

export default function AuthCard({ title, subtitle, children, footer, maxWidth = "max-w-xl" }: AuthCardProps) {
	return (
		<div className={`w-full ${maxWidth} mx-auto px-4 sm:px-6`}>
			<div className={'relative bg-surface rounded-[2rem] shadow-card border border-slate-100/70'}>
				<div className={'px-6 pt-10 pb-8 sm:px-12 sm:pt-12 text-center'}>
					<h1 className={'text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mb-4'}>
						{title}
					</h1>
					{subtitle ? (
						<p className={'mx-auto max-w-2xl text-base sm:text-lg leading-relaxed text-text-secondary'}>
							{subtitle}
						</p>
					) : null}
				</div>

				<div className={'h-px bg-slate-200/70 mx-6 sm:mx-12'} />

				<div className={'px-6 py-8 sm:px-12 sm:py-12'}>
					<div className={'space-y-8'}>
						{children}
					</div>
				</div>

				{footer ? (
					<>
						<div className={'h-px bg-slate-200/70 mx-6 sm:mx-12'} />
						<div className={'px-6 pt-6 pb-8 sm:px-12 sm:pt-8 sm:pb-12'}>
							<div className={'text-center text-base text-text-secondary'}>
								{footer}
							</div>
						</div>
					</>
				) : null}
			</div>
		</div>
	);
}