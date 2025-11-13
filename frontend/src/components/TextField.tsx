import React from 'react';

type TextFieldProps = {
	label: string;
	type?: 'text' | 'email' | 'password';
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	autoComplete?: string;
	required?: boolean;
	leftIcon?: React.ReactNode;
};

export default function TextField({
	label,
	type = 'text',
	value,
	onChange,
	placeholder,
	autoComplete,
	required,
	leftIcon,
}: TextFieldProps) {
	return (
		<label className={'block'}>
			<div className={'flex items-baseline justify-between mb-1.5'}>
				<span className={'text-[0.7rem] font-semibold tracking-tight text-slate-700'}>
					{label}
					{required ? <span className={'text-danger ml-0.5'}>*</span> : null}
				</span>
			</div>
			<div className={'group relative flex items-center rounded-2xl border border-slate-200 bg-white shadow-sm transition-transform duration-150 ease-out hover:-translate-y-0.5 hover:shadow-lg focus-within:-translate-y-0.5 focus-within:shadow-lg'}>
				{leftIcon ? (
					<span className={'pl-4 pr-2 text-slate-400 group-focus-within:text-slate-700'}>
						{leftIcon}
					</span>
				) : null}
				<input
					className={'w-full bg-transparent outline-none text-sm text-slate-900 placeholder:text-slate-400 py-3.5 pr-4'}
					type={type}
					value={value}
					onChange={(e) => onChange(e.target.value)}
					placeholder={placeholder}
					autoComplete={autoComplete}
					required={required}
				/>
			</div>
		</label>
	);
}
