import type { Metadata } from 'next';
import '@/styles/globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { QueryProvider } from '@/providers/QueryProvider';
import AuthDebug from '@/components/AuthDebug';

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
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <QueryProvider>
          <AuthProvider>
            {children}
            <AuthDebug />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
