import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Job Aggregator — Sri Lanka Tech Jobs",
  description: "Personal software engineering job dashboard aggregating listings from multiple Sri Lankan job boards",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Nav />
        <main style={{ minHeight: "calc(100vh - var(--nav-height))", background: "var(--bg-base)" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
