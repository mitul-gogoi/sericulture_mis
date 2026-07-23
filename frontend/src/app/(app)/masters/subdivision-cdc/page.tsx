"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { MasterCrud } from "@/components/MasterCrud";

interface SubdivisionCdc {
  id: string; office_type: string; office_name: string; district_id: string; is_active: boolean;
  office_address?: string; office_contact_no?: string; officer_in_charge_name?: string;
}
interface District { id: string; district_name: string; is_active: boolean }

export default function SubdivisionCdcPage() {
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["master-districts-select"],
    queryFn: async () => (await api.get("/master/districts?all=true")).data,
  });
  const distName = (id: string) => districts.find((d) => d.id === id)?.district_name || "—";

  return (
    <MasterCrud<SubdivisionCdc>
      title="Sub-division/CDC"
      description="Sub-division Offices and Chief Development Circles (CDC), one office per record, sitting under a District."
      endpoint="subdivision-cdc"
      queryKey="master-subdivision-cdc"
      searchOn={["office_name"]}
      addLabel="Add Sub-division/CDC"
      columns={[
        { key: "office_name", label: "Office Name", render: (r) => <span className="font-semibold">{r.office_name}</span> },
        { key: "office_type", label: "Type", render: (r) => r.office_type },
        { key: "district", label: "District", render: (r) => distName(r.district_id) },
      ]}
      fields={[
        { name: "office_type", label: "Type", type: "select", required: true, options: [
          { value: "Sub-division Office", label: "Sub-division Office" },
          { value: "CDC", label: "CDC" },
        ] },
        { name: "office_name", label: "Office Name", type: "text", required: true, placeholder: "e.g. Rangia Sub-division Office" },
        { name: "district_id", label: "District", type: "select", required: true, options: districts.map((d) => ({ value: d.id, label: d.district_name })) },
        { name: "office_address", label: "Office Address", type: "text" },
        { name: "office_contact_no", label: "Office Contact Number", type: "text" },
        { name: "officer_in_charge_name", label: "Officer-in-Charge", type: "text" },
      ]}
      emptyForm={{ office_type: "", office_name: "", district_id: "", office_address: "", office_contact_no: "", officer_in_charge_name: "" }}
      toForm={(r) => ({
        office_type: r.office_type, office_name: r.office_name, district_id: r.district_id,
        office_address: r.office_address || "", office_contact_no: r.office_contact_no || "",
        officer_in_charge_name: r.officer_in_charge_name || "",
      })}
      buildPayload={(f) => ({
        office_type: f.office_type, office_name: f.office_name, district_id: f.district_id,
        office_address: f.office_address || null, office_contact_no: f.office_contact_no || null,
        officer_in_charge_name: f.officer_in_charge_name || null,
      })}
    />
  );
}
