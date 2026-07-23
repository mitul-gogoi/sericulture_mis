"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface Caste { id: string; caste_name: string; is_active: boolean }

export default function CastePage() {
  return (
    <MasterCrud<Caste>
      title="Caste"
      description="Caste categories used for farmer classification and reporting."
      endpoint="castes"
      queryKey="master-castes"
      searchOn={["caste_name"]}
      addLabel="Add Caste"
      columns={[{ key: "caste_name", label: "Caste", render: (r) => <span className="font-semibold">{r.caste_name}</span> }]}
      fields={[{ name: "caste_name", label: "Caste Name", type: "text", required: true, placeholder: "e.g. General" }]}
      emptyForm={{ caste_name: "" }}
      toForm={(r) => ({ caste_name: r.caste_name })}
      buildPayload={(f) => ({ caste_name: f.caste_name })}
    />
  );
}
