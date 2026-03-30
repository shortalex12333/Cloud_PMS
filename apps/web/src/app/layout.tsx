import type { Metadata } from 'next';
import '@/styles/globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { QueryProvider } from '@/providers/QueryProvider';
import { MicroactionsProvider } from '@/providers/MicroactionsProvider';
import { ShellWrapper } from '@/components/shell/ShellWrapper';

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
              <ShellWrapper>
                {children}
              </ShellWrapper>
            </MicroactionsProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
