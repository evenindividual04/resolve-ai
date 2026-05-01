import "./globals.css";
import type { Metadata } from "next";
import TopNav from "../components/top-nav";

export const metadata: Metadata = {
  title: "Negotiation Ops Console",
  description: "Workflow and escalation reliability console",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
