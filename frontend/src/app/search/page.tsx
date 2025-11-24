"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Search, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center gap-4 px-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Button>
          </Link>
          <div className="flex-1 max-w-2xl">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                defaultValue={query}
                placeholder="Ask your yacht..."
                className="w-full h-10 pl-12 pr-4 rounded-lg border border-border bg-muted/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {query ? (
          <div className="space-y-6">
            <div className="text-center py-12">
              <h2 className="text-2xl font-semibold mb-2">
                Searching for: &quot;{query}&quot;
              </h2>
              <p className="text-muted-foreground">
                Search results will appear here when the backend is connected.
              </p>
              <p className="text-sm text-muted-foreground mt-4">
                The search engine will process your query and return relevant
                documents, equipment, faults, work orders, and predictive
                insights.
              </p>
            </div>

            {/* Placeholder cards showing what search will return */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 opacity-50">
              <div className="border border-dashed border-border rounded-lg p-6">
                <div className="h-4 w-24 bg-muted rounded mb-3" />
                <div className="h-3 w-full bg-muted rounded mb-2" />
                <div className="h-3 w-3/4 bg-muted rounded" />
              </div>
              <div className="border border-dashed border-border rounded-lg p-6">
                <div className="h-4 w-24 bg-muted rounded mb-3" />
                <div className="h-3 w-full bg-muted rounded mb-2" />
                <div className="h-3 w-3/4 bg-muted rounded" />
              </div>
              <div className="border border-dashed border-border rounded-lg p-6">
                <div className="h-4 w-24 bg-muted rounded mb-3" />
                <div className="h-3 w-full bg-muted rounded mb-2" />
                <div className="h-3 w-3/4 bg-muted rounded" />
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-2xl font-semibold mb-2">
              What would you like to find?
            </h2>
            <p className="text-muted-foreground max-w-md mx-auto">
              Search for documents, equipment, work orders, faults, parts, or
              ask questions about your yacht.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="animate-pulse">Loading search...</div>
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
