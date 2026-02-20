import type { Metadata } from 'next';
import '@/styles/globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { QueryProvider } from '@/providers/QueryProvider';
import { MicroactionsProvider } from '@/providers/MicroactionsProvider';
import { AuthDebug } from '@/components/AuthDebug';

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
    <html lang="en" className="dark" data-theme="dark" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <QueryProvider>
          <AuthProvider>
            <MicroactionsProvider>
              {children}
              <AuthDebug />
            </MicroactionsProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
