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
                variant="outlined"
                sx={{
                    '& .MuiOutlinedInput-root': {
                        borderRadius: 0.5,
                        backgroundColor: 'background.paper',
                        transition: 'all 0.2s ease-in-out',
                        border: '1px solid',
                        borderColor: 'divider',
                        '& fieldset': {
                            border: 'none',
                        },
                        '&:hover': {
                            borderColor: '#000000',
                            backgroundColor: 'background.paper',
                            boxShadow: 'none',
                        },
                        '&.Mui-focused': {
                            borderColor: '#000000',
                            backgroundColor: 'background.paper',
                            boxShadow: 'none',
                        },
                    },
                    '& input': {
                        fontSize: '0.9375rem',
                        paddingBlock: '12px',
                        paddingInline: '16px',
                    },
                    '& .MuiInputLabel-root': {
                        fontSize: '0.9375rem',
                        fontWeight: 500,
                        color: '#000000',
                        '&.Mui-focused': {
                            color: '#000000',
                        },
                        '&.MuiFormLabel-filled': {
                            transform: 'translateY(-10px) scale(0.85)',
                        },
                    },
                    // Adornment icon color sync
                    '& .MuiInputAdornment-root .MuiBox-root': {
                        color: '#000000',
                        transition: 'color 160ms ease',
                    },
                    '& .MuiOutlinedInput-root.Mui-focused .MuiInputAdornment-root .MuiBox-root': {
                        color: '#000000',
                    },
                }}
                InputProps={
                    leftIcon
                        ? {
                            startAdornment: (
                                <InputAdornment position="start">
                                    <Box sx={{ display: 'inline-flex', color: 'text.secondary' }}>{leftIcon}</Box>
                                </InputAdornment>
                            ),
                          }
                        : undefined
                }
            />
        </Box>
    );
}

