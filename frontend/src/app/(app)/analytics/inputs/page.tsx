"use client";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DrillDownExplorer, type Crumb } from "@/components/DrillDownExplorer";
import type { AnalyticsInputRow, AnalyticsLevel, District, Product, DashboardStats } from "@/lib/types";

export default function InputAnalyticsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const { data: products = [] } = useQuery<Product[]>({ queryKey: ["products"], queryFn: async () => (await api.get("/master/products")).data });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data,
    enabled: user?.role === "DISTRICT_ADMIN",
  });
  const { data: dash } = useQuery<DashboardStats>({
    queryKey: ["dashboard"], queryFn: async () => (await api.get("/reports/dashboard")).data,
    enabled: user?.role === "FIG_PRESIDENT",
  });

  if (!user) return null;

  let levels: AnalyticsLevel[] = ["district", "sericulture_circle", "fig", "farmer"];
  let lockedRoot: Crumb | undefined;
  if (user.role === "DISTRICT_ADMIN" && user.district_id) {
    levels = ["sericulture_circle", "fig", "farmer"];
    lockedRoot = { level: "district", id: user.district_id, name: districts.find((d) => d.id === user.district_id)?.district_name || "Your district" };
  } else if (user.role === "FIG_PRESIDENT" && user.fig_id) {
    levels = ["farmer"];
    lockedRoot = { level: "fig", id: user.fig_id, name: dash?.fig_name || "Your FIG" };
  }

  return (
    <DrillDownExplorer<AnalyticsInputRow>
      title="Input Explorer"
      description="Input quantities consumed by district, sericulture circle, FIG, and farmer, broken down by source"
      endpoint="/reports/analytics/inputs"
      levels={levels}
      lockedRoot={lockedRoot}
      dimension={{
        label: "Product",
        paramName: "product_id",
        options: products.map((p) => ({ id: p.id, label: `${p.product_name} (${p.unit_of_measure})` })),
        initialId: searchParams.get("product_id") || "",
      }}
      columns={(rows) => {
        const sourceNames = Array.from(new Set(rows.flatMap((r) => Object.keys(r.by_source)))).sort();
        return [
          { key: "name", label: "Name", render: (r) => <span className="font-semibold">{r.name}</span> },
          { key: "farmers", label: "Farmers", render: (r) => r.farmer_count ?? "—", className: "text-right" },
          { key: "total_qty", label: "Total Qty", render: (r) => r.total_qty.toLocaleString(undefined, { maximumFractionDigits: 1 }), className: "text-right font-semibold" },
          ...sourceNames.map((name) => ({
            key: `source_${name}`,
            label: name,
            render: (r: AnalyticsInputRow) => (r.by_source[name] ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 }),
            className: "text-right",
          })),
        ];
      }}
    />
  );
}
