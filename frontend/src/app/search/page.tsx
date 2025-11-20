'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const { user, isHOD } = useAuth()
  const router = useRouter()

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement search functionality with API
    console.log('Search query:', query)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Top Bar */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">CelesteOS</h1>
            {user && (
              <span className="text-sm text-muted-foreground">
                {user.yacht_name || 'Yacht'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <span className="text-sm text-muted-foreground">
                  {user.name} ({user.role})
                </span>
                {isHOD() && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/dashboard')}
                  >
                    Dashboard
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Universal Search Bar */}
        <div className="max-w-3xl mx-auto mb-12">
          <form onSubmit={handleSearch}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search anything… (fault code, system, part, note, document)"
              className="w-full px-6 py-4 text-lg border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </form>
          <p className="text-sm text-muted-foreground mt-2 text-center">
            Try: "Fault E047 main engine" or "Find MTU coolant drawing"
          </p>
        </div>

        {/* Results Area */}
        <div className="max-w-4xl mx-auto">
          {query ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Searching for: <span className="font-medium">{query}</span>
              </p>
              {/* TODO: Results cards will appear here */}
              <Card>
                <CardContent className="p-6">
                  <p className="text-muted-foreground">
                    Search results will appear here...
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center text-muted-foreground">
              <p>Start typing to search across all yacht systems</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
