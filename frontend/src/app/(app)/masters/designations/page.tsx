"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface Designation { id: string; designation_name: string; display_order: number; is_active: boolean }

export default function DesignationsPage() {
  return (
    <MasterCrud<Designation>
      title="Designations"
      description="Departmental posts held by State and District Admins, e.g. Assistant Director of Sericulture (ADS). Order decides how they are listed — lower numbers appear first, so the hierarchy reads correctly."
      endpoint="designations"
      queryKey="master-designations"
      searchOn={["designation_name"]}
      addLabel="Add Designation"
      columns={[
        { key: "designation_name", label: "Designation", render: (r) => <span className="font-semibold">{r.designation_name}</span> },
        { key: "display_order", label: "Order" },
      ]}
      fields={[
        { name: "designation_name", label: "Designation", type: "text", required: true,
          placeholder: "e.g. Assistant Director of Sericulture (ADS)" },
        { name: "display_order", label: "Order (lower shows first)", type: "number",
          placeholder: "e.g. 50" },
      ]}
      emptyForm={{ designation_name: "", display_order: "" }}
      toForm={(r) => ({ designation_name: r.designation_name, display_order: String(r.display_order ?? "") })}
      buildPayload={(f) => ({
        designation_name: f.designation_name,
        display_order: f.display_order ? Number(f.display_order) : 0,
      })}
    />
  );
}
