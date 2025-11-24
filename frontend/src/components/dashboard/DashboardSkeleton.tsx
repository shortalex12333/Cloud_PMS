"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/card";

export function SearchBarSkeleton() {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <Skeleton className="h-12 w-full rounded-xl" />
    </div>
  );
}

export function DashboardCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-lg" />
          <div className="space-y-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
        <Skeleton className="h-8 w-12" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Skeleton className="h-14 w-full rounded-lg" />
          <Skeleton className="h-14 w-full rounded-lg" />
        </div>
      </CardContent>
    </Card>
  );
}

export function LegacyPanelSkeleton() {
  return (
    <div className="border border-border rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-8" />
        </div>
        <Skeleton className="h-5 w-5" />
      </div>
    </div>
  );
}

export function DashboardPageSkeleton() {
  return (
    <div className="space-y-8">
      {/* Search Bar Skeleton */}
      <section className="py-6">
        <SearchBarSkeleton />
      </section>

      {/* Intelligence Cards Skeleton */}
      <section className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <DashboardCardSkeleton key={i} />
          ))}
        </div>
      </section>

      {/* Legacy Panels Skeleton */}
      <section className="space-y-4">
        <Skeleton className="h-6 w-56" />
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <LegacyPanelSkeleton key={i} />
          ))}
        </div>
      </section>
    </div>
  );
}
