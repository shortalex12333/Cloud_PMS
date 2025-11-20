'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user } = useAuth()
  const router = useRouter()

  return (
    <div className="min-h-screen bg-background">
      {/* Top Bar */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">CelesteOS</h1>
            {user?.yacht_name && (
              <span className="text-sm text-muted-foreground">
                {user.yacht_name}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <div className="text-right">
                  <p className="text-sm font-medium">{user.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    Role: {user.role.replace('_', ' ')}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push('/search')}
                >
                  ← Back to Search
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  )
}
