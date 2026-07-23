"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DrillDownExplorer, type Crumb } from "@/components/DrillDownExplorer";
import type { AnalyticsLandRow, District } from "@/lib/types";

export default function LandsAnalyticsPage() {
  const { user } = useAuth();
  const isDA = user?.role === "DISTRICT_ADMIN";
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data,
    enabled: isDA,
  });

  if (user?.role === "FIG_PRESIDENT") return <div>Not available for your role.</div>;

  const lockedRoot: Crumb | undefined = isDA && user?.district_id
    ? { level: "district", id: user.district_id, name: districts.find((d) => d.id === user.district_id)?.district_name || "Your district" }
    : undefined;

  return (
    <DrillDownExplorer<AnalyticsLandRow>
      title="Lands"
      description="Registered land parcels and area by district and sericulture circle"
      endpoint="/reports/analytics/lands"
      levels={isDA ? ["sericulture_circle"] : ["district", "sericulture_circle"]}
      lockedRoot={lockedRoot}
      columns={[
        { key: "name", label: "Name", render: (r) => <span className="font-semibold">{r.name}</span> },
        { key: "parcels", label: "Parcels", render: (r) => r.parcels.toLocaleString(), className: "text-right" },
        { key: "bigha", label: "Bigha", render: (r) => r.bigha.toFixed(2), className: "text-right" },
        { key: "hectare", label: "Hectare", render: (r) => r.hectare.toFixed(4), className: "text-right" },
        { key: "verified", label: "GPS Verified", render: (r) => r.verified.toLocaleString(), className: "text-right" },
        { key: "pending", label: "GPS Pending", render: (r) => r.pending.toLocaleString(), className: "text-right" },
      ]}
    />
  );
}
