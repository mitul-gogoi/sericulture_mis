"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { MasterCrud } from "@/components/MasterCrud";

interface Circle {
  id: string; circle_name: string; district_id: string; lac_id?: string | null; is_active: boolean;
  office_name?: string; office_address?: string; office_contact_no?: string; officer_in_charge_name?: string;
}
interface District { id: string; district_name: string; is_active: boolean }
interface Lac { id: string; lac_no?: number | null; lac_name: string; district_id: string; is_active: boolean }

export default function SericultureCirclesPage() {
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["master-districts-select"],
    queryFn: async () => (await api.get("/master/districts?all=true")).data,
  });
  const { data: lacs = [] } = useQuery<Lac[]>({
    queryKey: ["master-lacs-select"],
    queryFn: async () => (await api.get("/master/lacs?all=true")).data,
  });
  const distName = (id: string) => districts.find((d) => d.id === id)?.district_name || "—";
  const lacLabel = (id?: string | null) => (id && lacs.find((l) => l.id === id)?.lac_name) || "—";

  return (
    <MasterCrud<Circle>
      title="Sericulture Circles"
      description="Sericulture circles under each district."
      endpoint="sericulture-circles"
      queryKey="master-sericulture-circles"
      searchOn={["circle_name"]}
      addLabel="Add Sericulture Circle"
      columns={[
        { key: "circle_name", label: "Sericulture Circle", render: (r) => <span className="font-semibold">{r.circle_name}</span> },
        { key: "district", label: "District", render: (r) => distName(r.district_id) },
        { key: "lac", label: "LAC", render: (r) => lacLabel(r.lac_id) },
        { key: "office_name", label: "Office Name", render: (r) => r.office_name || "—" },
      ]}
      fields={[
        { name: "district_id", label: "District", type: "select", required: true, options: districts.map((d) => ({ value: d.id, label: d.district_name })) },
        { name: "lac_id", label: "LAC", type: "select", options: (form) => lacs.filter((l) => l.district_id === form.district_id).map((l) => ({ value: l.id, label: l.lac_no ? `${l.lac_no}. ${l.lac_name}` : l.lac_name })) },
        { name: "circle_name", label: "Circle Name", type: "text", required: true, placeholder: "e.g. Rani" },
        { name: "office_name", label: "Office Name", type: "text", placeholder: "e.g. Sericulture Circle Office, Rani" },
        { name: "office_address", label: "Office Address", type: "text" },
        { name: "office_contact_no", label: "Office Contact Number", type: "text" },
        { name: "officer_in_charge_name", label: "Officer-in-Charge", type: "text" },
      ]}
      emptyForm={{ circle_name: "", district_id: "", lac_id: "", office_name: "", office_address: "", office_contact_no: "", officer_in_charge_name: "" }}
      toForm={(r) => ({
        circle_name: r.circle_name, district_id: r.district_id, lac_id: r.lac_id || "",
        office_name: r.office_name || "", office_address: r.office_address || "",
        office_contact_no: r.office_contact_no || "", officer_in_charge_name: r.officer_in_charge_name || "",
      })}
      buildPayload={(f) => ({
        circle_name: f.circle_name, district_id: f.district_id, lac_id: f.lac_id || null,
        office_name: f.office_name || null, office_address: f.office_address || null,
        office_contact_no: f.office_contact_no || null, officer_in_charge_name: f.officer_in_charge_name || null,
      })}
    />
  );
}
