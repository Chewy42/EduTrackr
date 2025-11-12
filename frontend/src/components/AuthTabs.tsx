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
        <Box sx={{ px: 0 }}>
            <Tabs
                value={value}
                onChange={(_, v: number) => onChange(v === 0 ? 'sign_in' : 'sign_up')}
                variant="fullWidth"
                textColor="primary"
                indicatorColor="primary"
                TabIndicatorProps={{
                    sx: {
                        height: 44,
                        borderRadius: 3,
                        transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1), width 300ms cubic-bezier(0.4, 0, 0.2, 1)',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                    },
                }}
                sx={{
                    minHeight: 56,
                    '& .MuiTabs-flexContainer': {
                        gap: 0.5,
                    },
                    '& .MuiTab-root': {
                        borderRadius: 3,
                        minHeight: 44,
                        paddingInline: 2,
                        transition: 'background-color 160ms ease, color 160ms ease',
                        fontWeight: 500,
                        fontSize: '0.9375rem',
                        color: 'text.secondary',
                        zIndex: 1,
                        '&.Mui-selected': {
                            fontWeight: 600,
                            color: 'text.primary',
                        },
                        '&:hover': {
                            backgroundColor: 'action.hover',
                            color: 'text.primary',
                        },
                    },
                }}
            >
                <Tab
                    label="Sign In"
                    sx={{
                        minHeight: 44,
                        textTransform: 'none',
                        fontWeight: 500,
                        fontSize: '0.9375rem',
                        color: 'text.secondary',
                        '&.Mui-selected': {
                            fontWeight: 600,
                            color: 'text.primary',
                        },
                        '&:hover': {
                            backgroundColor: 'action.hover',
                        },
                    }}
                />
                <Tab
                    label="Sign Up"
                    sx={{
                        minHeight: 44,
                        textTransform: 'none',
                        fontWeight: 500,
                        fontSize: '0.9375rem',
                        color: 'text.secondary',
                        '&.Mui-selected': {
                            fontWeight: 600,
                            color: 'text.primary',
                        },
                        '&:hover': {
                            backgroundColor: 'action.hover',
                        },
                    }}
                />
            </Tabs>
        </Box>
    );
}


