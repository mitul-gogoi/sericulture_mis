"use client";
import { useQuery } from "@tanstack/react-query";
import { MasterCrud } from "@/components/MasterCrud";
import api from "@/lib/api";
import type { InputSourceType, InputSourceCategory } from "@/lib/types";

export default function InputSourceTypesPage() {
  const { data: categories = [] } = useQuery<InputSourceCategory[]>({
    queryKey: ["master-input-source-categories-all"],
    queryFn: async () => (await api.get("/master/input-source-categories?all=true")).data,
  });

  return (
    <MasterCrud<InputSourceType>
      title="Input Source Types"
      description="Where a FIG President can say an input came from — assigned per Activity→Product Input mapping in Map Activity to Product."
      endpoint="input-source-types"
      queryKey="master-input-source-types"
      searchOn={["source_name"]}
      addLabel="Add Input Source Type"
      columns={[
        { key: "source_name", label: "Source", render: (r) => <span className="font-semibold">{r.source_name}</span> },
        { key: "category_name", label: "Category", render: (r) => r.category_name || <span style={{ color: "var(--text-muted)" }}>—</span> },
        { key: "requires_scheme", label: "Requires Scheme", render: (r) => (r.requires_scheme ? "Yes" : "No") },
        { key: "is_own_source", label: "Own Source (auto-fill)", render: (r) => (r.is_own_source ? "Yes" : "No") },
      ]}
      fields={[
        { name: "source_name", label: "Source name", type: "text", required: true, placeholder: "e.g. Market Source" },
        {
          name: "category_id", label: "Category", type: "select", required: true,
          options: categories.map((c) => ({ value: c.id, label: c.category_name })),
        },
        { name: "requires_scheme", label: "Requires a linked Scheme", type: "checkbox" },
        { name: "is_own_source", label: "Auto-fills from stock + this cycle's output", type: "checkbox" },
      ]}
      emptyForm={{ source_name: "", category_id: "", requires_scheme: "false", is_own_source: "false" }}
      toForm={(r) => ({
        source_name: r.source_name,
        category_id: r.category_id,
        requires_scheme: String(r.requires_scheme),
        is_own_source: String(r.is_own_source),
      })}
      buildPayload={(f) => ({
        source_name: f.source_name,
        category_id: f.category_id,
        requires_scheme: f.requires_scheme === "true",
        is_own_source: f.is_own_source === "true",
      })}
    />
  );
}
