"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface District {
  id: string; district_name: string; state_name: string; is_active: boolean;
  office_name?: string; office_address?: string; office_contact_no?: string; officer_in_charge_name?: string;
}

export default function DistrictsPage() {
  return (
    <MasterCrud<District>
      title="Districts"
      description="Administrative districts (Assam LGD codes). Add / edit / activate-deactivate as needed."
      endpoint="districts"
      queryKey="master-districts"
      searchOn={["district_name"]}
      columns={[
        { key: "district_name", label: "District", render: (r) => <span className="font-semibold">{r.district_name}</span> },
        { key: "state_name", label: "State" },
        { key: "office_name", label: "District Sericulture Office", render: (r) => r.office_name || "—" },
      ]}
      fields={[
        { name: "district_name", label: "District Name", type: "text", required: true, placeholder: "e.g. Kamrup Metropolitan" },
        { name: "state_name", label: "State", type: "text", required: true, placeholder: "Assam" },
        { name: "office_name", label: "Office Name", type: "text", placeholder: "e.g. District Sericulture Office, Kamrup Metropolitan" },
        { name: "office_address", label: "Office Address", type: "text" },
        { name: "office_contact_no", label: "Office Contact Number", type: "text" },
        { name: "officer_in_charge_name", label: "Officer-in-Charge", type: "text" },
      ]}
      emptyForm={{ district_name: "", state_name: "Assam", office_name: "", office_address: "", office_contact_no: "", officer_in_charge_name: "" }}
      toForm={(r) => ({
        district_name: r.district_name, state_name: r.state_name,
        office_name: r.office_name || "", office_address: r.office_address || "",
        office_contact_no: r.office_contact_no || "", officer_in_charge_name: r.officer_in_charge_name || "",
      })}
      buildPayload={(f) => ({
        district_name: f.district_name, state_name: f.state_name || "Assam",
        office_name: f.office_name || null, office_address: f.office_address || null,
        office_contact_no: f.office_contact_no || null, officer_in_charge_name: f.officer_in_charge_name || null,
      })}
    />
  );
}
