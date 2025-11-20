import type { Metadata } from 'next';
import '@/styles/globals.css';
import { cn } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'CelesteOS - Engineering Intelligence for Yachts',
  description: 'Cloud-first AI-driven engineering intelligence system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={cn('font-sans antialiased')}>
        {children}
      </body>
    </html>
  );
}
