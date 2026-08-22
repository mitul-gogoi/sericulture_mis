"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { MasterCrud } from "@/components/MasterCrud";

interface Lac {
  id: string; lac_no?: number | null; lac_name: string; district_id: string; is_active: boolean;
}
interface District { id: string; district_name: string; is_active: boolean }

export default function LacPage() {
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["master-districts-select"],
    queryFn: async () => (await api.get("/master/districts?all=true")).data,
  });
  const distName = (id: string) => districts.find((d) => d.id === id)?.district_name || "—";

  return (
    <MasterCrud<Lac>
      title="LAC"
      description="Legislative Assembly Constituencies. Assam's 126 constituencies are pre-loaded against their districts; each Sericulture Circle is then mapped to the one it falls in."
      endpoint="lacs"
      queryKey="master-lacs"
      searchOn={["lac_name"]}
      addLabel="Add LAC"
      columns={[
        { key: "lac_no", label: "No.", render: (r) => <span className="font-mono text-xs">{r.lac_no ?? "—"}</span> },
        { key: "lac_name", label: "LAC", render: (r) => <span className="font-semibold">{r.lac_name}</span> },
        { key: "district", label: "District", render: (r) => distName(r.district_id) },
      ]}
      fields={[
        { name: "lac_name", label: "LAC Name", type: "text", required: true, placeholder: "e.g. Dispur" },
        { name: "lac_no", label: "LAC Number", type: "text", placeholder: "1–126" },
        { name: "district_id", label: "District", type: "select", required: true, options: districts.map((d) => ({ value: d.id, label: d.district_name })) },
      ]}
      emptyForm={{ lac_name: "", lac_no: "", district_id: "" }}
      toForm={(r) => ({
        lac_name: r.lac_name, lac_no: r.lac_no ? String(r.lac_no) : "", district_id: r.district_id,
      })}
      buildPayload={(f) => ({
        lac_name: f.lac_name,
        lac_no: f.lac_no ? Number(f.lac_no) : null,
        district_id: f.district_id,
      })}
    />
  );
}
