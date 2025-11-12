import React from "react";
import MuiTextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Box from "@mui/material/Box";

type TextFieldProps = {
	label: string;
	type?: "text" | "email" | "password";
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	autoComplete?: string;
	required?: boolean;
	leftIcon?: React.ReactNode;
};

export default function TextField({
	label,
	type = "text",
	value,
	onChange,
	placeholder,
	autoComplete,
	required,
	leftIcon,
}: TextFieldProps) {
	return (
		<Box>
			<MuiTextField
				label={label}
				type={type}
				value={value}
				onChange={(e) => onChange(e.target.value)}
				placeholder={placeholder}
				autoComplete={autoComplete}
				required={required}
				fullWidth
				InputProps={
					leftIcon
						? {
								startAdornment: (
									<InputAdornment position="start">
										<Box sx={{ display: 'inline-flex', color: 'action.active' }}>{leftIcon}</Box>
									</InputAdornment>
								),
						  }
						: undefined
				}
			/>
		</Box>
	);
}

