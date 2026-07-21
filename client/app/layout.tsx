import StoreProvider from "@/store/StoreProvider";
import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";

const displayFont = IBM_Plex_Mono({
    subsets: ["latin"],
    weight: ["500", "600"],
    variable: "--font-display",
});

const bodyFont = Inter({
    subsets: ["latin"],
    variable: "--font-body",
});

export const metadata: Metadata = {
    title: "IRCTC Assist — AI Agent",
    description:
        "Chat with an AI agent for PNR status, train search, and seat availability.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html
            lang="en"
            className={`${displayFont.variable} ${bodyFont.variable}`}
        >
            <body className="h-screen overflow-hidden">
                <StoreProvider>{children}</StoreProvider>
            </body>
        </html>
    );
}
