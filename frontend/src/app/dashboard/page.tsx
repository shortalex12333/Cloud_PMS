import { Suspense } from "react";
import { fetchDashboardBriefing } from "@/lib/api";
import {
  Header,
  Footer,
  SearchBar,
  DashboardCard,
  LegacyPanel,
  DashboardPageSkeleton,
} from "@/components/dashboard";
import type { LegacyPanelItem } from "@/components/dashboard";
import type { DashboardBriefing } from "@/types/dashboard";

// Intelligence card configurations
const intelligenceCards = [
  {
    id: "risk_movements",
    title: "Today's Risk Movements",
    icon: "TrendingUp",
    searchQuery: "risk movement today",
  },
  {
    id: "high_risk_equipment",
    title: "High-Risk Equipment",
    icon: "AlertTriangle",
    searchQuery: "high risk equipment",
  },
  {
    id: "patterns_7d",
    title: "Patterns (7-day)",
    icon: "Activity",
    searchQuery: "patterns last 7 days",
  },
  {
    id: "unstable_systems",
    title: "Unstable Systems",
    icon: "Activity",
    searchQuery: "unstable systems last 48h",
  },
  {
    id: "inventory_gaps",
    title: "Inventory Gaps",
    icon: "PackageOpen",
    searchQuery: "parts below minimum inventory",
  },
  {
    id: "overdue_critical",
    title: "Overdue Critical Work",
    icon: "ClipboardList",
    searchQuery: "overdue critical work orders",
  },
  {
    id: "inspections_due",
    title: "Inspections in Next 30 Days",
    icon: "Timer",
    searchQuery: "inspections due next 30 days",
  },
  {
    id: "crew_signals",
    title: "Crew Frustration Signals",
    icon: "Users",
    searchQuery: "crew search patterns",
  },
];

// Legacy panel keys in order
const legacyPanelKeys = [
  "equipment",
  "work_orders",
  "inventory",
  "certificates",
  "faults",
  "notes",
  "scheduled_maintenance",
  "spare_parts",
  "documents",
];

// Transform data to card items
function transformToCardItems(
  data: DashboardBriefing,
  cardId: string
): { id: string; name: string; metric: string; reason: string }[] {
  switch (cardId) {
    case "risk_movements":
      return data.risk_movements.map((item) => ({
        id: item.id,
        name: item.equipment_name,
        metric: `${item.risk_delta > 0 ? "+" : ""}${(item.risk_delta * 100).toFixed(0)}%`,
        reason: item.reason,
      }));
    case "high_risk_equipment":
      return data.high_risk_equipment.map((item) => ({
        id: item.id,
        name: item.name,
        metric: `${(item.risk_score * 100).toFixed(0)}% risk`,
        reason: item.reason,
      }));
    case "patterns_7d":
      return data.patterns_7d.map((item) => ({
        id: item.id,
        name: item.pattern_type.replace("_", " "),
        metric: `${item.occurrences}x`,
        reason: item.description,
      }));
    case "unstable_systems":
      return data.unstable_systems.map((item) => ({
        id: item.id,
        name: item.name,
        metric: `${item.fault_count_48h} faults`,
        reason: item.reason,
      }));
    case "inventory_gaps":
      return data.inventory_gaps.map((item) => ({
        id: item.id,
        name: item.part_name,
        metric: `-${item.deficit} units`,
        reason: `${item.current_stock}/${item.minimum_required} in stock`,
      }));
    case "overdue_critical":
      return data.overdue_critical.map((item) => ({
        id: item.id,
        name: item.title,
        metric: `${item.days_overdue}d overdue`,
        reason: item.equipment_name,
      }));
    case "inspections_due":
      return data.inspections_due.map((item) => ({
        id: item.id,
        name: item.name,
        metric: `${item.days_until_due}d`,
        reason: `${item.equipment_name} - ${item.type}`,
      }));
    case "crew_signals":
      return data.crew_signals.map((item) => ({
        id: item.id,
        name: item.signal_type.replace("_", " "),
        metric: `${item.frequency}x`,
        reason: item.description,
      }));
    default:
      return [];
  }
}

// Transform legacy data to panel items
function transformLegacyData(
  data: DashboardBriefing["legacy"],
  panelKey: string
): LegacyPanelItem[] {
  const items = data[panelKey as keyof typeof data];
  if (!Array.isArray(items)) return [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (items as any[]).map((item) => {
    const base: LegacyPanelItem = {
      id: item.id as string,
      name: (item.name || item.title || item.code || "Unknown") as string,
    };

    // Add status if available
    if ("status" in item) {
      base.status = item.status as string;
    }

    // Add detail based on item type
    if ("category" in item) {
      base.detail = item.category as string;
    } else if ("equipment_name" in item) {
      base.detail = item.equipment_name as string;
    } else if ("due_date" in item) {
      base.detail = `Due: ${item.due_date}`;
    } else if ("expiry_date" in item) {
      base.detail = `Expires: ${item.expiry_date}`;
    } else if ("date" in item) {
      base.detail = item.date as string;
    } else if ("quantity" in item) {
      base.detail = `Qty: ${item.quantity}`;
    } else if ("type" in item) {
      base.detail = item.type as string;
    }

    return base;
  });
}

async function DashboardContent() {
  const data = await fetchDashboardBriefing();

  return (
    <>
      {/* Primary Management Search Bar */}
      <section className="py-8 border-b border-border">
        <SearchBar />
      </section>

      {/* Section 1: Intelligence Cards */}
      <section className="py-8">
        <h2 className="text-xl font-semibold mb-6">Ship Intelligence</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {intelligenceCards.map((cardConfig) => {
            const items = transformToCardItems(data, cardConfig.id);
            const count = items.length;

            if (count === 0) return null;

            return (
              <DashboardCard
                key={cardConfig.id}
                title={cardConfig.title}
                icon={cardConfig.icon}
                count={count}
                topItems={items}
                searchQuery={cardConfig.searchQuery}
              />
            );
          })}
        </div>
      </section>

      {/* Section 2: Legacy Compatibility Panels */}
      <section className="py-8 border-t border-border">
        <h2 className="text-xl font-semibold mb-6">System Overview</h2>
        <div className="space-y-2">
          {legacyPanelKeys.map((panelKey) => {
            const items = transformLegacyData(data.legacy, panelKey);
            return (
              <LegacyPanel key={panelKey} panelKey={panelKey} items={items} />
            );
          })}
        </div>
      </section>
    </>
  );
}

export default function DashboardPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-6">
        <Suspense fallback={<DashboardPageSkeleton />}>
          <DashboardContent />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}

export const metadata = {
  title: "Dashboard | CelesteOS",
  description: "Ship state awareness and intelligence overview",
};
