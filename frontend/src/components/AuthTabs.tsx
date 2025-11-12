import React from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Box from "@mui/material/Box";
import type { AuthMode } from "../auth/AuthContext";

type AuthTabsProps = {
	mode: AuthMode;
	onChange: (mode: AuthMode) => void;
};

export default function AuthTabs({ mode, onChange }: AuthTabsProps) {
	const value = mode === 'sign_in' ? 0 : 1;

	return (
		<Box sx={{ px: 3 }}>
			<Tabs
				value={value}
				onChange={(_, v: number) => onChange(v === 0 ? 'sign_in' : 'sign_up')}
				variant="fullWidth"
				textColor="primary"
				indicatorColor="primary"
				TabIndicatorProps={{
					sx: {
						height: 3,
						borderRadius: 1.5,
						transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1), width 300ms cubic-bezier(0.4, 0, 0.2, 1)',
					},
				}}
				sx={{
					minHeight: 48,
					'& .MuiTabs-flexContainer': {
						gap: 1,
					},
				}}
			>
				<Tab
					label="Sign In"
					sx={{
						minHeight: 48,
						textTransform: 'none',
						fontWeight: 500,
						fontSize: '0.875rem',
						color: 'text.secondary',
						'&.Mui-selected': {
							fontWeight: 600,
							color: 'text.primary',
						},
					}}
				/>
				<Tab
					label="Sign Up"
					sx={{
						minHeight: 48,
						textTransform: 'none',
						fontWeight: 500,
						fontSize: '0.875rem',
						color: 'text.secondary',
						'&.Mui-selected': {
							fontWeight: 600,
							color: 'text.primary',
						},
					}}
				/>
			</Tabs>
		</Box>
	);
}


