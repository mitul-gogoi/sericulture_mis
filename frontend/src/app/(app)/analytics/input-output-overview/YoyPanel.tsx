"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import api from "@/lib/api";
import { fyOptions, currentFY } from "@/lib/fiscal";

const MultiSeriesTrendChart = dynamic(() => import("../../dashboard/charts").then((m) => m.MultiSeriesTrendChart), { ssr: false });

export function YoyPanel({ productId, districtId }: { productId: string; districtId?: string }) {
  const [metric, setMetric] = useState<"output" | "input">("output");
  const defaultFys = useMemo(() => [currentFY(), fyOptions(2)[1]].filter(Boolean), []);
  const [selected, setSelected] = useState<string[]>(defaultFys);
  const options = fyOptions();

  const { data } = useQuery({
    queryKey: ["yoy-trend", selected, metric, productId, districtId],
    queryFn: async () => {
      const params = new URLSearchParams();
      selected.forEach((fy) => params.append("fiscal_years", fy));
      params.set("metric", metric);
      if (productId) params.set("product_id", productId);
      if (districtId) params.set("district_id", districtId);
      return (await api.get(`/reports/yoy-trend?${params.toString()}`)).data;
    },
    enabled: selected.length > 0 && !!productId,
  });

  const chartData = useMemo(() => {
    if (!data?.labels) return [];
    return data.labels.map((label: string, i: number) => {
      const row: Record<string, string | number> = { label };
      data.series.forEach((s: { fiscal_year: string; data: { actual: number }[] }) => {
        row[s.fiscal_year] = s.data[i]?.actual ?? 0;
      });
      return row;
    });
  }, [data]);

  function toggleFy(fy: string) {
    setSelected((prev) => (prev.includes(fy) ? prev.filter((f) => f !== fy) : prev.length < 4 ? [...prev, fy] : prev));
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h3 className="font-heading text-lg font-bold">Year-on-year trend</h3>
        <div className="flex items-center gap-1">
          <button onClick={() => setMetric("output")} className={metric === "output" ? "btn-primary btn-sm" : "btn-secondary btn-sm"}>Output</button>
          <button onClick={() => setMetric("input")} className={metric === "input" ? "btn-primary btn-sm" : "btn-secondary btn-sm"}>Input</button>
        </div>
      </div>
      <div className="flex items-center gap-1 flex-wrap mb-4">
        {options.map((fy) => (
          <button key={fy} onClick={() => toggleFy(fy)}
                  className={selected.includes(fy) ? "btn-primary btn-sm" : "btn-secondary btn-sm"}>
            {fy}
          </button>
        ))}
      </div>
      <div style={{ height: 260 }}>
        <MultiSeriesTrendChart data={chartData} seriesKeys={selected} />
      </div>
      {!productId && (
        <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>Pick a product to see its year-on-year trend.</div>
      )}
      {productId && chartData.length === 0 && (
        <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>Select at least one fiscal year.</div>
      )}
    </div>
  );
}
