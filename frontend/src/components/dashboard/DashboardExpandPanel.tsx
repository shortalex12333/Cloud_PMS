"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

export interface ExpandPanelItem {
  id: string;
  name: string;
  metric: string;
  reason: string;
}

export interface DashboardExpandPanelProps {
  items: ExpandPanelItem[];
  searchQuery: string;
  maxVisible?: number;
}

export function DashboardExpandPanel({
  items,
  searchQuery,
  maxVisible = 10,
}: DashboardExpandPanelProps) {
  const router = useRouter();

  const handleInspect = (itemName: string) => {
    const query = `${searchQuery} ${itemName}`.trim();
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  const visibleItems = items.slice(0, maxVisible);
  const hasMore = items.length > maxVisible;

  return (
    <div className="space-y-2 animate-fadeIn">
      {visibleItems.map((item) => (
        <div
          key={item.id}
          className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
        >
          <div className="flex-1 min-w-0 mr-4">
            <p className="font-medium text-sm">{item.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{item.reason}</p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-sm font-semibold text-primary">
              {item.metric}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => handleInspect(item.name)}
            >
              <Search className="h-3 w-3 mr-1.5" />
              Inspect in Search
            </Button>
          </div>
        </div>
      ))}
      {hasMore && (
        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-2"
          onClick={() =>
            router.push(`/search?q=${encodeURIComponent(searchQuery)}`)
          }
        >
          Show {items.length - maxVisible} more in Search
        </Button>
      )}
    </div>
  );
}
