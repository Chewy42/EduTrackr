import { createTheme } from '@mui/material/styles'

export const appTheme = createTheme({
	palette: {
		mode: 'light',
		primary: {
			main: '#4f46e5', // Deep indigo
			light: '#6366f1',
			dark: '#4338ca',
			contrastText: '#ffffff',
		},
		secondary: {
			main: '#7c3aed', // Purple accent
			light: '#8b5cf6',
			dark: '#6d28d9',
			contrastText: '#ffffff',
		},
		background: {
			default: '#f8fafc', // Light slate background
			paper: '#ffffff', // Pure white for cards
		},
		text: {
			primary: '#1e293b', // Deep slate for primary text
			secondary: '#64748b', // Muted slate for secondary text
		},
		info: {
			main: '#0ea5e9',
		},
		success: {
			main: '#10b981',
		},
		warning: {
			main: '#f59e0b',
		},
		error: {
			main: '#ef4444',
		},
		divider: 'rgba(148, 163, 184, 0.2)', // Subtle divider
	},
	shape: {
		borderRadius: 16,
	},
	typography: {
		fontFamily: [
			'Inter',
			'-apple-system',
			'BlinkMacSystemFont',
			'"Segoe UI"',
			'Roboto',
			'sans-serif',
		].join(','),
		h1: {
			fontWeight: 700,
			fontSize: '2.5rem',
			lineHeight: 1.2,
			letterSpacing: '-0.02em',
		},
		h4: {
			fontWeight: 600,
			fontSize: '1.75rem',
			lineHeight: 1.3,
			letterSpacing: '-0.01em',
		},
		h6: {
			fontWeight: 600,
			fontSize: '1.25rem',
			lineHeight: 1.2,
			letterSpacing: '-0.01em',
		},
		body1: {
			fontSize: '1rem',
			lineHeight: 1.6,
			fontWeight: 400,
		},
		body2: {
			fontSize: '0.875rem',
			lineHeight: 1.5,
			fontWeight: 400,
		},
		caption: {
			fontSize: '0.75rem',
			lineHeight: 1.4,
			fontWeight: 500,
		},
		button: {
			fontWeight: 600,
			fontSize: '0.9375rem',
			textTransform: 'none',
			letterSpacing: '0.01em',
		},
	},
	components: {
		MuiButton: {
			defaultProps: {
				disableElevation: true,
			},
			styleOverrides: {
				root: {
					textTransform: 'none',
					borderRadius: 12,
					fontWeight: 600,
					fontSize: '0.9375rem',
					paddingInline: '1.5rem',
					paddingBlock: '0.875rem',
					transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
					boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
					'&:hover': {
						boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
						transform: 'translateY(-1px)',
					},
				},
				containedPrimary: {
					background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
					'&:hover': {
						background: 'linear-gradient(135deg, #4338ca 0%, #6d28d9 100%)',
					},
				},
				outlinedPrimary: {
					borderColor: 'rgba(79, 70, 229, 0.5)',
					color: '#4f46e5',
					'&:hover': {
						borderColor: '#4f46e5',
						backgroundColor: 'rgba(79, 70, 229, 0.04)',
					},
				},
			},
		},
		MuiCard: {
			styleOverrides: {
				root: {
					transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
					borderRadius: 24,
					backgroundColor: '#ffffff',
					border: '1px solid rgba(148, 163, 184, 0.1)',
					boxShadow: '0 10px 25px rgba(0, 0, 0, 0.06), 0 4px 10px rgba(0, 0, 0, 0.04)',
					'&:hover': {
						boxShadow: '0 20px 40px rgba(0, 0, 0, 0.08), 0 8px 16px rgba(0, 0, 0, 0.06)',
						transform: 'translateY(-2px)',
					},
					overflow: 'hidden',
				},
			},
		},
		MuiCardContent: {
			styleOverrides: {
				root: {
					padding: '32px',
					'&:last-child': {
						paddingBottom: '32px',
					},
				},
			},
		},
		MuiDivider: {
			styleOverrides: {
				root: {
					backgroundColor: 'rgba(148, 163, 184, 0.15)',
					margin: '0',
				},
			},
		},
		MuiTabs: {
			styleOverrides: {
				root: {
					minHeight: 56,
					backgroundColor: 'rgba(248, 250, 252, 0.8)',
					borderRadius: 16,
					padding: '6px',
					border: '1px solid rgba(148, 163, 184, 0.15)',
				},
				indicator: {
					height: 44,
					borderRadius: 12,
					backgroundColor: '#ffffff',
					boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
					transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
				},
			},
		},
		MuiTab: {
			styleOverrides: {
				root: {
					minHeight: 44,
					fontWeight: 500,
					fontSize: '0.9375rem',
					textTransform: 'none',
					color: '#64748b',
					transition: 'all 0.2s ease-in-out',
					zIndex: 1,
					'&.Mui-selected': {
						fontWeight: 600,
						color: '#1e293b',
					},
				},
			},
		},
		MuiTextField: {
			defaultProps: {
				variant: 'outlined',
				fullWidth: true,
			},
		},
		MuiOutlinedInput: {
			styleOverrides: {
				root: {
					backgroundColor: '#ffffff',
					borderRadius: 16,
					transition: 'all 0.2s ease-in-out',
					border: '1px solid rgba(148, 163, 184, 0.2)',
					'&:hover': {
						borderColor: 'rgba(79, 70, 229, 0.4)',
						backgroundColor: '#ffffff',
					},
					'&.Mui-focused': {
						backgroundColor: '#ffffff',
						borderColor: '#4f46e5',
						boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.1)',
					},
				},
				notchedOutline: {
					border: 'none',
				},
				input: {
					paddingBlock: '18px',
					paddingInline: '16px',
					fontSize: '0.9375rem',
				},
			},
		},
		MuiInputLabel: {
			styleOverrides: {
				root: {
					fontSize: '0.9375rem',
					fontWeight: 500,
					color: '#64748b',
					'&.Mui-focused': {
						color: '#4f46e5',
					},
				},
			},
		},
	},
})