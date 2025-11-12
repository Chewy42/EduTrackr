import React from "react";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";

type SubmitButtonProps = {
	loading?: boolean;
	children: React.ReactNode;
};

export default function SubmitButton({ loading, children }: SubmitButtonProps) {
    return (
        <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={!!loading}
            sx={{
                borderRadius: 0.5,
                fontWeight: 600,
                minHeight: 48,
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                background: '#2563eb',
                color: 'white',
                '&:hover': {
                    background: '#1d4ed8',
                    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
                    transform: 'translateY(-1px)',
                },
                '&:active': {
                    background: '#1d4ed8',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1), 0 1px 1px rgba(0, 0, 0, 0.06)',
                    transform: 'translateY(0)',
                },
                '&.Mui-disabled': {
                    background: '#93c5fd',
                    color: '#ffffff',
                    boxShadow: 'none',
                    transform: 'none',
                }
            }}
        >
            {loading ? "Please wait..." : children}
        </Button>
    );
}

