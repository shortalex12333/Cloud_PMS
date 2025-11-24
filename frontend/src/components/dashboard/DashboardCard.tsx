"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  TrendingUp,
  Activity,
  ClipboardList,
  PackageOpen,
  Timer,
  Wrench,
  Users,
  ChevronDown,
  ChevronUp,
  Search,
  LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  AlertTriangle,
  TrendingUp,
  Activity,
  ClipboardList,
  PackageOpen,
  Timer,
  Wrench,
  Users,
};

export interface DashboardCardItem {
  id: string;
  name: string;
  metric: string;
  reason: string;
}

export interface DashboardCardProps {
  title: string;
  icon: string;
  count: number;
  trend?: string;
  topItems: DashboardCardItem[];
  searchQuery: string;
  className?: string;
}

export function DashboardCard({
  title,
  icon,
  count,
  trend,
  topItems,
  searchQuery,
  className,
}: DashboardCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();
  const Icon = iconMap[icon] || AlertTriangle;

  const handleInspect = (itemName: string) => {
    const query = `${searchQuery} ${itemName}`.trim();
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  const handleCardClick = () => {
    setIsExpanded(!isExpanded);
  };

  const visibleItems = isExpanded ? topItems : topItems.slice(0, 2);
  const hasMoreItems = topItems.length > 2;

  if (count === 0) {
    return null;
  }

  return (
    <Card
      className={cn(
        "cursor-pointer hover:border-primary/50 transition-all duration-200",
        isExpanded && "col-span-full",
        className
      )}
    >
      <CardHeader
        className="flex flex-row items-center justify-between space-y-0 pb-2"
        onClick={handleCardClick}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold">{title}</CardTitle>
            {trend && (
              <p className="text-xs text-muted-foreground mt-0.5">{trend}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold">{count}</span>
          {hasMoreItems && (
            <Button variant="ghost" size="icon" className="h-8 w-8">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            "space-y-2",
            isExpanded && "animate-fadeIn"
          )}
        >
          {visibleItems.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-2 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
            >
              <div className="flex-1 min-w-0 mr-3">
                <p className="font-medium text-sm truncate">{item.name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {item.reason}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-sm font-medium text-primary">
                  {item.metric}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleInspect(item.name);
                  }}
                >
                  <Search className="h-3 w-3 mr-1" />
                  Inspect
                </Button>
              </div>
            </div>
          ))}
          {isExpanded && topItems.length > 0 && (
            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={(e) => {
                  e.stopPropagation();
                  router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
                }}
              >
                <Search className="h-4 w-4 mr-2" />
                View all in Search
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
