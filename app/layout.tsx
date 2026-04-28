import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DailyBET - AI Football Accumulators",
  description: "AI-powered daily football accumulator predictions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <meta name="theme-color" content="#050a07" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
      </head>
      <body className="min-h-screen bg-[#050a07] text-[#e0f2e9] antialiased">
        {children}
      </body>
    </html>
  );
}

