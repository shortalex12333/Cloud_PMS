import type { Metadata } from 'next'
import { AuthProvider } from '@/components/AuthProvider'

export const metadata: Metadata = {
  title: 'CelesteOS',
  description: 'Yacht management system'
}

export default function RootLayout({
  children
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
