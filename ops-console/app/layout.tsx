import "./globals.css";
import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import TopNav from "../components/top-nav";
import { ToastProvider } from "../components/ToastContext";

export const metadata: Metadata = {
  title: "Resolve AI — Collections Intelligence Console",
  description: "Operator control surface for autonomous collections workflows, escalation triage, and negotiation intelligence",
};

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <ToastProvider>
          <TopNav />
          <main className="app-shell">
            {children}
          </main>
        </ToastProvider>
      </body>
    </html>
  );
}
