import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Job Aggregator — Sri Lanka Tech Jobs Engine",
  description: "Software engineering job dashboard aggregating listings from major Sri Lankan job boards",
  authors: [{ name: "Yasiru Kaveeshwara", url: "https://github.com/YasiruKaveeshwara" }],
  creator: "Yasiru Kaveeshwara",
  publisher: "Yasiru Kaveeshwara",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/icon.png",
    apple: "/apple-icon.png",
  },
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
      <body style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <Nav />
        <main style={{ flex: 1, background: "var(--bg-base)" }}>
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
