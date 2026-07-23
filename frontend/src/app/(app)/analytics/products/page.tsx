"use client";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DrillDownExplorer, type Crumb } from "@/components/DrillDownExplorer";
import type { AnalyticsProductionRow, AnalyticsLevel, District, Product, DashboardStats } from "@/lib/types";

export default function ProductAnalyticsPage() {
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
    <DrillDownExplorer<AnalyticsProductionRow>
      title="Production Explorer"
      description="Planned vs actual production by district, sericulture circle, FIG, and farmer"
      endpoint="/reports/analytics/products"
      levels={levels}
      lockedRoot={lockedRoot}
      dimension={{
        label: "Product",
        paramName: "product_id",
        options: products.filter((p) => !p.is_byproduct).map((p) => ({ id: p.id, label: `${p.product_name} (${p.unit_of_measure})` })),
        initialId: searchParams.get("product_id") || "",
      }}
      columns={[
        { key: "name", label: "Name", render: (r) => <span className="font-semibold">{r.name}</span> },
        { key: "farmers", label: "Farmers", render: (r) => r.farmer_count ?? "—", className: "text-right" },
        { key: "planned", label: "Planned", render: (r) => r.planned.toLocaleString(undefined, { maximumFractionDigits: 1 }), className: "text-right" },
        { key: "actual", label: "Actual", render: (r) => r.actual.toLocaleString(undefined, { maximumFractionDigits: 1 }), className: "text-right font-semibold" },
        { key: "earning", label: "Earning (₹)", render: (r) => r.earning.toLocaleString(), className: "text-right" },
      ]}
    />
  );
}
