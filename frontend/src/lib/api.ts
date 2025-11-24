import type { DashboardBriefing } from "@/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDashboardBriefing(): Promise<DashboardBriefing> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/dashboard/briefing`, {
      next: { revalidate: 60 }, // Revalidate every 60 seconds
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch dashboard briefing: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error("Error fetching dashboard briefing:", error);
    // Return mock data in development or when API is unavailable
    return getMockDashboardData();
  }
}

// Mock data for development
function getMockDashboardData(): DashboardBriefing {
  return {
    risk_movements: [
      {
        id: "rm-1",
        equipment_name: "Main Engine #1",
        risk_delta: 0.15,
        current_risk: 0.72,
        reason: "Unusual vibration patterns detected over 24h",
      },
      {
        id: "rm-2",
        equipment_name: "Generator #2",
        risk_delta: 0.08,
        current_risk: 0.45,
        reason: "Oil pressure fluctuation detected",
      },
      {
        id: "rm-3",
        equipment_name: "Watermaker",
        risk_delta: -0.12,
        current_risk: 0.28,
        reason: "Recent maintenance improved metrics",
      },
    ],
    high_risk_equipment: [
      {
        id: "hre-1",
        name: "Main Engine #1",
        risk_score: 0.72,
        category: "Propulsion",
        last_service: "2024-11-01",
        reason: "Multiple fault codes, vibration anomaly",
      },
      {
        id: "hre-2",
        name: "Bow Thruster",
        risk_score: 0.68,
        category: "Maneuvering",
        last_service: "2024-10-15",
        reason: "Overdue service, motor temperature high",
      },
      {
        id: "hre-3",
        name: "Air Conditioning Compressor #1",
        risk_score: 0.55,
        category: "HVAC",
        last_service: "2024-09-20",
        reason: "Refrigerant pressure low",
      },
    ],
    patterns_7d: [
      {
        id: "p-1",
        pattern_type: "recurring_fault",
        description: "Generator startup failures between 0600-0800",
        occurrences: 5,
        affected_items: ["Generator #1", "Generator #2"],
        trend: "increasing",
      },
      {
        id: "p-2",
        pattern_type: "search_cluster",
        description: "Repeated crew searches for bilge pump documentation",
        occurrences: 12,
        affected_items: ["Bilge Pump Manual", "Bilge System Diagram"],
        trend: "stable",
      },
    ],
    unstable_systems: [
      {
        id: "us-1",
        name: "Generator #1",
        stability_score: 0.35,
        fault_count_48h: 8,
        reason: "Intermittent voltage fluctuations",
      },
      {
        id: "us-2",
        name: "Navigation System",
        stability_score: 0.52,
        fault_count_48h: 3,
        reason: "GPS signal dropouts",
      },
    ],
    inventory_gaps: [
      {
        id: "ig-1",
        part_name: "Oil Filter Element - Main Engine",
        current_stock: 1,
        minimum_required: 4,
        deficit: 3,
        criticality: "critical",
      },
      {
        id: "ig-2",
        part_name: "V-Belt - Generator",
        current_stock: 0,
        minimum_required: 2,
        deficit: 2,
        criticality: "high",
      },
      {
        id: "ig-3",
        part_name: "Impeller - Seawater Pump",
        current_stock: 2,
        minimum_required: 3,
        deficit: 1,
        criticality: "medium",
      },
    ],
    overdue_critical: [
      {
        id: "oc-1",
        work_order_id: "WO-2024-0847",
        title: "Main Engine 500hr Service",
        equipment_name: "Main Engine #1",
        days_overdue: 12,
        priority: "critical",
      },
      {
        id: "oc-2",
        work_order_id: "WO-2024-0891",
        title: "Fire Suppression System Inspection",
        equipment_name: "Engine Room Fire System",
        days_overdue: 5,
        priority: "high",
      },
    ],
    inspections_due: [
      {
        id: "id-1",
        name: "Annual Life Raft Inspection",
        equipment_name: "Life Raft #1",
        due_date: "2024-12-15",
        days_until_due: 21,
        type: "Regulatory",
      },
      {
        id: "id-2",
        name: "EPIRB Battery Replacement",
        equipment_name: "EPIRB",
        due_date: "2024-12-20",
        days_until_due: 26,
        type: "Regulatory",
      },
      {
        id: "id-3",
        name: "Class Survey - Hull",
        equipment_name: "Hull Structure",
        due_date: "2025-01-10",
        days_until_due: 47,
        type: "Classification",
      },
    ],
    crew_signals: [
      {
        id: "cs-1",
        signal_type: "repeated_search",
        description: "Multiple searches for waste management procedures",
        frequency: 8,
        department: "Interior",
      },
      {
        id: "cs-2",
        signal_type: "documentation_gap",
        description: "Questions about tender operation checklist",
        frequency: 5,
        department: "Deck",
      },
    ],
    legacy: {
      equipment: [
        { id: "eq-1", name: "Main Engine #1", category: "Propulsion", status: "operational", last_service: "2024-11-01" },
        { id: "eq-2", name: "Main Engine #2", category: "Propulsion", status: "operational", last_service: "2024-11-01" },
        { id: "eq-3", name: "Generator #1", category: "Electrical", status: "maintenance", last_service: "2024-10-15" },
        { id: "eq-4", name: "Generator #2", category: "Electrical", status: "operational", last_service: "2024-10-15" },
        { id: "eq-5", name: "Watermaker", category: "Water Systems", status: "operational", last_service: "2024-11-10" },
        { id: "eq-6", name: "Bow Thruster", category: "Maneuvering", status: "operational", last_service: "2024-10-15" },
        { id: "eq-7", name: "AC Compressor #1", category: "HVAC", status: "maintenance", last_service: "2024-09-20" },
        { id: "eq-8", name: "AC Compressor #2", category: "HVAC", status: "operational", last_service: "2024-09-20" },
      ],
      work_orders: [
        { id: "wo-1", title: "Main Engine 500hr Service", status: "pending", priority: "critical", equipment_name: "Main Engine #1", due_date: "2024-11-12" },
        { id: "wo-2", title: "Fire System Inspection", status: "pending", priority: "high", equipment_name: "Fire Suppression", due_date: "2024-11-19" },
        { id: "wo-3", title: "Generator Oil Change", status: "in_progress", priority: "medium", equipment_name: "Generator #1", due_date: "2024-11-25" },
        { id: "wo-4", title: "AC Filter Replacement", status: "completed", priority: "low", equipment_name: "HVAC System", due_date: "2024-11-20" },
        { id: "wo-5", title: "Tender Engine Service", status: "pending", priority: "medium", equipment_name: "Tender", due_date: "2024-12-01" },
      ],
      inventory: [
        { id: "inv-1", name: "Oil Filter Element", quantity: 1, location: "Engine Room Store", category: "Filters" },
        { id: "inv-2", name: "V-Belt Generator", quantity: 0, location: "Engine Room Store", category: "Belts" },
        { id: "inv-3", name: "Impeller Seawater Pump", quantity: 2, location: "Engine Room Store", category: "Pumps" },
        { id: "inv-4", name: "Zinc Anodes", quantity: 12, location: "Deck Store", category: "Corrosion" },
        { id: "inv-5", name: "Hydraulic Oil", quantity: 40, location: "Engine Room Store", category: "Fluids" },
      ],
      certificates: [
        { id: "cert-1", name: "MCA Commercial Certificate", expiry_date: "2025-06-15", status: "valid", authority: "MCA" },
        { id: "cert-2", name: "Life Raft Service Certificate", expiry_date: "2024-12-15", status: "expiring", authority: "Viking" },
        { id: "cert-3", name: "Radio License", expiry_date: "2025-03-20", status: "valid", authority: "Ofcom" },
        { id: "cert-4", name: "ISM Certificate", expiry_date: "2025-08-01", status: "valid", authority: "Lloyds" },
      ],
      faults: [
        { id: "fault-1", code: "E-101", equipment_name: "Generator #1", description: "Low oil pressure warning", date: "2024-11-22", severity: "high" },
        { id: "fault-2", code: "E-205", equipment_name: "Main Engine #1", description: "Vibration sensor alert", date: "2024-11-21", severity: "medium" },
        { id: "fault-3", code: "A-302", equipment_name: "AC Compressor #1", description: "Low refrigerant pressure", date: "2024-11-20", severity: "medium" },
        { id: "fault-4", code: "N-401", equipment_name: "Navigation System", description: "GPS signal lost", date: "2024-11-19", severity: "low" },
      ],
      notes: [
        { id: "note-1", title: "Engine room inspection complete", author: "Chief Engineer", date: "2024-11-22", category: "Inspection" },
        { id: "note-2", title: "Guest arrival briefing", author: "Captain", date: "2024-11-21", category: "Operations" },
        { id: "note-3", title: "Fuel bunkering completed", author: "2nd Engineer", date: "2024-11-20", category: "Fuel" },
      ],
      scheduled_maintenance: [
        { id: "sm-1", name: "Main Engine 1000hr Service", equipment_name: "Main Engine #1", schedule: "Every 1000 hours", next_due: "2025-01-15" },
        { id: "sm-2", name: "Generator Monthly Check", equipment_name: "Generator #1", schedule: "Monthly", next_due: "2024-12-01" },
        { id: "sm-3", name: "AC Filter Cleaning", equipment_name: "HVAC System", schedule: "Bi-weekly", next_due: "2024-12-05" },
        { id: "sm-4", name: "Watermaker Membrane Clean", equipment_name: "Watermaker", schedule: "Quarterly", next_due: "2025-02-10" },
      ],
      spare_parts: [
        { id: "sp-1", name: "Fuel Injector", part_number: "FI-2024-A", quantity: 4, equipment_compatible: ["Main Engine #1", "Main Engine #2"] },
        { id: "sp-2", name: "Alternator Belt", part_number: "AB-G100", quantity: 2, equipment_compatible: ["Generator #1", "Generator #2"] },
        { id: "sp-3", name: "Water Pump Seal Kit", part_number: "WP-SK-01", quantity: 3, equipment_compatible: ["Watermaker"] },
      ],
      documents: [
        { id: "doc-1", name: "Main Engine Manual", type: "Manual", last_updated: "2023-06-15", category: "Technical" },
        { id: "doc-2", name: "Safety Management System", type: "Policy", last_updated: "2024-08-01", category: "Safety" },
        { id: "doc-3", name: "Emergency Procedures", type: "Procedure", last_updated: "2024-10-15", category: "Safety" },
        { id: "doc-4", name: "Electrical Schematics", type: "Drawing", last_updated: "2022-03-20", category: "Technical" },
      ],
    },
  };
}
