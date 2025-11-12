import { createTheme } from '@mui/material/styles'

export const appTheme = createTheme({
	palette: {
		mode: 'light',
		primary: {
			main: '#3b82f6', // modern blue
			light: '#93c5fd',
			dark: '#1d4ed8',
		},
		secondary: {
			main: '#22c55e',
		},
		background: {
			default: '#f8fafc', // very light blue-gray
			paper: '#ffffff', // pure white for cards
		},
		text: {
			primary: '#1e293b', // slate-800
			secondary: '#64748b', // slate-500
		},
	},
	shape: {
		borderRadius: 12,
	},
	typography: {
		fontFamily: [
			'Inter',
			'ui-sans-serif',
			'system-ui',
			'-apple-system',
			'Segoe UI',
			'Roboto',
			'Ubuntu',
			'Cantarell',
			'Noto Sans',
			'sans-serif',
		].join(','),
		h6: {
			fontWeight: 600,
			fontSize: '1.5rem',
			lineHeight: 1.2,
		},
		caption: {
			fontSize: '0.875rem',
			lineHeight: 1.4,
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
					paddingInline: '1rem',
					paddingBlock: '0.75rem',
				},
				containedPrimary: {
					boxShadow: 'none',
					'&:hover': { boxShadow: 'none' },
					'&:active': { boxShadow: 'none' },
				},
			},
		},
		MuiCard: {
			styleOverrides: {
				root: {
					transition: 'all 0.2s ease-in-out',
					borderRadius: 16,
					boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.06)',
				},
			},
		},
		MuiTabs: {
			styleOverrides: {
				root: {
					minHeight: 48,
				},
				indicator: {
					height: 3,
					borderRadius: 1.5,
					transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
				},
			},
		},
		MuiTab: {
			styleOverrides: {
				root: {
					minHeight: 48,
					fontWeight: 500,
					fontSize: '0.875rem',
					transition: 'all 0.2s ease-in-out',
					'&.Mui-selected': {
						fontWeight: 600,
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
					backgroundColor: '#fff',
				},
				notchedOutline: {
					borderColor: 'rgba(148, 163, 184, 0.4)',
				},
				input: {
					paddingBlock: '12px',
				},
			},
		},
	},
})


