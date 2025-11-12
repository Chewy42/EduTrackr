import React from "react";
import Button from "@mui/material/Button";

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
                borderRadius: 2,
                fontWeight: 700,
                minHeight: 48,
                boxShadow:
                    '0 6px 12px rgba(14, 30, 37, 0.08), 0 2px 4px rgba(14, 30, 37, 0.08)',
                transition: 'transform 120ms ease, box-shadow 160ms ease, background-color 160ms ease',
                '&:hover': {
                    boxShadow:
                        '0 10px 18px rgba(14, 30, 37, 0.10), 0 4px 8px rgba(14, 30, 37, 0.10)',
                    transform: 'translateY(-1px)'
                },
                '&:active': {
                    boxShadow:
                        '0 4px 8px rgba(14, 30, 37, 0.12), 0 1px 3px rgba(14, 30, 37, 0.16)',
                    transform: 'translateY(0)'
                },
                '&.Mui-disabled': {
                    boxShadow: 'none'
                }
            }}
        >
            {loading ? "Please wait..." : children}
        </Button>
    );
}

