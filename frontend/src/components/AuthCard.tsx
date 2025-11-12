import React from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Box from "@mui/material/Box";

type AuthCardProps = {
	title: string;
	subtitle?: string;
	children: React.ReactNode;
	footer?: React.ReactNode;
};

export default function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
    return (
        <Box sx={{ width: '100%', maxWidth: 560, mx: 'auto' }}>
            <Card elevation={8} sx={{ bgcolor: 'background.paper', borderRadius: 3 }}>
                <CardContent sx={{ pb: 2, px: { xs: 3, sm: 5 }, pt: { xs: 3, sm: 4 } }}>
                    <Typography variant="h6" component="h1" gutterBottom>
                        {title}
                    </Typography>
                    {subtitle ? (
                        <Typography variant="caption" color="text.secondary">
                            {subtitle}
                        </Typography>
                    ) : null}
                </CardContent>
                <Divider />
                <CardContent sx={{ pt: { xs: 2.5, sm: 3 }, px: { xs: 3, sm: 5 }, pb: { xs: 3, sm: 4 } }}>
                    {children}
                </CardContent>
                {footer ? (
                    <>
                        <Divider />
                        <CardContent sx={{ px: { xs: 3, sm: 5 }, pb: { xs: 3, sm: 4 } }}>{footer}</CardContent>
                    </>
                ) : null}
            </Card>
        </Box>
    );
}


