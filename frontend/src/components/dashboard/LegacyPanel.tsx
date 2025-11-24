"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  Search,
  Wrench,
  ClipboardList,
  PackageOpen,
  FileCheck,
  AlertCircle,
  FileText,
  Calendar,
  Cog,
  FolderOpen,
  LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  equipment: Wrench,
  work_orders: ClipboardList,
  inventory: PackageOpen,
  certificates: FileCheck,
  faults: AlertCircle,
  notes: FileText,
  scheduled_maintenance: Calendar,
  spare_parts: Cog,
  documents: FolderOpen,
};

const titleMap: Record<string, string> = {
  equipment: "Equipment Overview",
  work_orders: "Work Orders Overview",
  inventory: "Inventory Overview",
  certificates: "Certificates & Compliance",
  faults: "Fault History",
  notes: "Notes & Logs",
  scheduled_maintenance: "Scheduled Maintenance",
  spare_parts: "Spare Parts",
  documents: "Documents & Manuals",
};

const searchQueryMap: Record<string, string> = {
  equipment: "equipment",
  work_orders: "work orders",
  inventory: "inventory parts",
  certificates: "certificates compliance",
  faults: "fault history",
  notes: "notes logs",
  scheduled_maintenance: "scheduled maintenance",
  spare_parts: "spare parts",
  documents: "documents manuals",
};

export interface LegacyPanelItem {
  id: string;
  name: string;
  status?: string;
  detail?: string;
}

export interface LegacyPanelProps {
  panelKey: string;
  items: LegacyPanelItem[];
  className?: string;
}

export function LegacyPanel({ panelKey, items, className }: LegacyPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();

  const Icon = iconMap[panelKey] || FolderOpen;
  const title = titleMap[panelKey] || panelKey;
  const searchQuery = searchQueryMap[panelKey] || panelKey;

  const handleInspect = (itemName: string) => {
    const query = `${searchQuery} ${itemName}`.trim();
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  const visibleItems = isExpanded ? items.slice(0, 20) : [];
  const hasMore = items.length > 20;

  const getStatusColor = (status?: string) => {
    if (!status) return "";
    const s = status.toLowerCase();
    if (s === "operational" || s === "valid" || s === "completed") {
      return "text-risk-low";
    }
    if (s === "maintenance" || s === "expiring" || s === "in_progress" || s === "pending") {
      return "text-risk-medium";
    }
    if (s === "offline" || s === "expired" || s === "critical" || s === "high") {
      return "text-risk-critical";
    }
    return "text-muted-foreground";
  };

  return (
    <div
      className={cn(
        "border border-border rounded-lg overflow-hidden",
        className
      )}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <span className="font-medium">{title}</span>
          <span className="text-sm text-muted-foreground">
            ({items.length})
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-5 w-5 text-muted-foreground" />
        )}
      </button>

      {isExpanded && (
        <div className="border-t border-border animate-slideDown">
          <div className="p-4 space-y-2">
            {visibleItems.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No items to display
              </p>
            ) : (
              visibleItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="font-medium text-sm truncate">{item.name}</p>
                    {item.detail && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {item.detail}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {item.status && (
                      <span
                        className={cn(
                          "text-xs font-medium capitalize",
                          getStatusColor(item.status)
                        )}
                      >
                        {item.status.replace("_", " ")}
                      </span>
                    )}
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
              ))
            )}
            {hasMore && (
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-2"
                onClick={() =>
                  router.push(`/search?q=${encodeURIComponent(searchQuery)}`)
                }
              >
                <Search className="h-4 w-4 mr-2" />
                View all {items.length} items in Search
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
