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
        <Box sx={{ 
            width: '100%', 
            maxWidth: 560, 
            mx: 'auto',
            p: { xs: 2, sm: 3 }
        }}>
            <Card 
                elevation={0} 
                sx={{ 
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    overflow: 'visible',
                    position: 'relative'
                }}
            >
                <CardContent sx={{ 
                    pb: 3, 
                    px: { xs: 4, sm: 6 }, 
                    pt: { xs: 6, sm: 8 },
                    position: 'relative'
                }}>
                    <Box sx={{ textAlign: 'center', mb: 2 }}>
                        <Typography 
                            variant="h4" 
                            component="h1" 
                            gutterBottom
                            sx={{ 
                                fontWeight: 700,
                                color: 'text.primary',
                                mb: 1.5,
                                letterSpacing: '-0.02em'
                            }}
                        >
                            {title}
                        </Typography>
                        {subtitle ? (
                            <Typography 
                                variant="body2" 
                                color="text.secondary"
                                sx={{ 
                                    maxWidth: 420,
                                    mx: 'auto',
                                    lineHeight: 1.6,
                                    fontWeight: 400
                                }}
                            >
                                {subtitle}
                            </Typography>
                        ) : null}
                    </Box>
                </CardContent>
                
                <Divider sx={{ mx: { xs: 4, sm: 6 } }} />
                
                <CardContent sx={{ 
                    pt: { xs: 5, sm: 6 }, 
                    px: { xs: 4, sm: 6 }, 
                    pb: { xs: 5, sm: 6 }
                }}>
                    <Box sx={{
                        '& > * + *': { mt: 3.5 },
                    }}>
                        {children}
                    </Box>
                </CardContent>
                
                {footer ? (
                    <>
                        <Divider sx={{ mx: { xs: 4, sm: 6 } }} />
                        <CardContent sx={{ 
                            px: { xs: 4, sm: 6 }, 
                            pb: { xs: 6, sm: 8 },
                            pt: { xs: 4, sm: 5 }
                        }}>
                            <Box sx={{ textAlign: 'center' }}>
                                {footer}
                            </Box>
                        </CardContent>
                    </>
                ) : null}
            </Card>
        </Box>
    );
}