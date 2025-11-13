import React from 'react';

type SubmitButtonProps = {
	loading?: boolean;
	children: React.ReactNode;
	onClick?: () => void;
};

export default function SubmitButton({ loading, children, onClick }: SubmitButtonProps) {
	return (
		<button
			type="submit"
			disabled={!!loading}
			onClick={onClick}
			className={
				'inline-flex w-full items-center justify-center rounded-xl bg-brand-600 text-white text-sm font-semibold py-3.5 px-4 shadow-md transition-all duration-200 ease-out ' +
				'hover:bg-brand-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 disabled:bg-brand-300 disabled:shadow-none disabled:cursor-not-allowed'
			}
		>
			{loading ? 'Please wait...' : children}
		</button>
	);
}
