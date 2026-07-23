"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface Religion { id: string; religion_name: string; is_active: boolean }

export default function ReligionPage() {
  return (
    <MasterCrud<Religion>
      title="Religion"
      description="Religion values used for farmer profile fields."
      endpoint="religions"
      queryKey="master-religions"
      searchOn={["religion_name"]}
      addLabel="Add Religion"
      columns={[{ key: "religion_name", label: "Religion", render: (r) => <span className="font-semibold">{r.religion_name}</span> }]}
      fields={[{ name: "religion_name", label: "Religion Name", type: "text", required: true, placeholder: "e.g. Hindu" }]}
      emptyForm={{ religion_name: "" }}
      toForm={(r) => ({ religion_name: r.religion_name })}
      buildPayload={(f) => ({ religion_name: f.religion_name })}
    />
  );
}
