"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface SilkType { id: string; silk_type_name: string; is_active: boolean; created_at: string }

export default function SilkTypesPage() {
  return (
    <MasterCrud<SilkType>
      title="Silk Types"
      description="Top-level silk classification (Eri, Muga, Mulberry, Tasar) used across products and mappings."
      endpoint="silk-types"
      queryKey="master-silk-types"
      searchOn={["silk_type_name"]}
      columns={[{ key: "silk_type_name", label: "Silk Type", render: (r) => <span className="font-semibold">{r.silk_type_name}</span> }]}
      fields={[{ name: "silk_type_name", label: "Silk Type Name", type: "text", required: true, placeholder: "e.g. Eri" }]}
      emptyForm={{ silk_type_name: "" }}
      toForm={(r) => ({ silk_type_name: r.silk_type_name })}
      buildPayload={(f) => ({ silk_type_name: f.silk_type_name })}
    />
  );
}
