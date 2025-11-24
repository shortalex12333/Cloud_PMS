import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CelesteOS - Yacht Management Intelligence",
  description: "Cloud-first AI engineering intelligence system for yachts",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
