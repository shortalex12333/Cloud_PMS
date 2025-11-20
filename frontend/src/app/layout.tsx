/**
 * Root Layout
 * Wraps all pages
 */

import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CelesteOS - Yacht Management System',
  description: 'Intelligent yacht management and document system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
