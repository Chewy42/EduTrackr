import React from "react";

type Props = {
	label: string;
	type?: "email" | "password";
	value: string;
	placeholder?: string;
	onChange: (next: string) => void;
	icon?: React.ReactNode;
	required?: boolean;
	autoComplete?: string;
	name?: string;
};

export default function AuthInput({
	label,
	type = "email",
	value,
	placeholder,
	onChange,
	icon,
	required = true,
	autoComplete,
	name,
}: Props) {
	return (
		<div className="group">
			<label className="block text-[10px] font-medium text-slate-400 mb-1">
				{label}
			</label>
			<div className="flex items-center gap-2 px-3 py-2.5 rounded-2xl border border-slate-800 bg-slate-950/80 transition-all group-hover:border-emerald-500/80 group-hover:bg-slate-900/90 cursor-text shadow-sm">
				{icon}
				<input
					name={name}
					type={type}
					required={required}
					value={value}
					onChange={(e) => onChange(e.target.value)}
					className="w-full bg-transparent outline-none text-xs placeholder:text-slate-600"
					placeholder={placeholder}
					autoComplete={autoComplete}
				/>
			</div>
		</div>
	);
}


