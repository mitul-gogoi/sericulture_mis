"use client";
import { useQuery } from "@tanstack/react-query";
import { MasterCrud } from "@/components/MasterCrud";
import api from "@/lib/api";
import type { SilkType, InputSourceCategory } from "@/lib/types";

const UNIT_OPTIONS = ["kg", "Number", "Litre", "Meter", "Bigha", "DFL", "Not Measured"].map((u) => ({ value: u, label: u }));

interface Product {
  id: string;
  product_name: string;
  unit_of_measure: string;
  silk_type_id?: string | null;
  silk_type_name?: string | null;
  default_source_category_id?: string | null;
  is_perishable: boolean;
  is_byproduct: boolean;
  show_in_dashboard: boolean;
  is_active: boolean;
  created_at: string;
}

export default function ProductsPage() {
  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: sourceCategories = [] } = useQuery<InputSourceCategory[]>({
    queryKey: ["master-input-source-categories-all"],
    queryFn: async () => (await api.get("/master/input-source-categories?all=true")).data,
  });

  return (
    <MasterCrud<Product>
      hasUsageCheck
      title="Products"
      description="Every primary and byproduct output (cocoon, raw silk, DFLs, pupae, reel waste, etc.), each tied to a silk type (or left generic for materials shared across silk types), tagged with unit of measure and perishability."
      endpoint="products"
      queryKey="master-products"
      searchOn={["product_name"]}
      columns={[
        { key: "product_name", label: "Product", render: (r) => <span className="font-semibold">{r.product_name}</span> },
        { key: "silk_type_name", label: "Silk Type", render: (r) => r.silk_type_name || <span style={{ color: "var(--text-muted)" }}>Generic</span> },
        { key: "unit_of_measure", label: "Unit" },
        { key: "is_byproduct", label: "Byproduct", render: (r) => (r.is_byproduct ? "Yes" : "No") },
        { key: "is_perishable", label: "Perishable", render: (r) => (r.is_perishable ? "Yes" : "No") },
        { key: "show_in_dashboard", label: "On Dashboard", render: (r) => (r.show_in_dashboard ? "Yes" : "No") },
      ]}
      fields={[
        { name: "product_name", label: "Product Name", type: "text", required: true, placeholder: "e.g. Eri Fabric" },
        {
          name: "silk_type_id", label: "Silk Type (leave blank for a generic, shared material)", type: "select",
          options: silkTypes.map((s) => ({ value: s.id, label: s.silk_type_name })),
        },
        {
          name: "unit_of_measure", label: "Unit of Measure", type: "select", required: true,
          options: UNIT_OPTIONS, allowOther: true, placeholder: "e.g. Cocoons",
        },
        {
          name: "default_source_category_id",
          label: "Default Input Source Category (only relevant if this product is later mapped as an Activity Input)",
          type: "select", options: sourceCategories.map((c) => ({ value: c.id, label: c.category_name })),
        },
        { name: "is_byproduct", label: "Is byproduct", type: "checkbox" },
        { name: "is_perishable", label: "Is perishable", type: "checkbox" },
        { name: "show_in_dashboard", label: "Show on Dashboard (Input & Output Overview, tiles, summaries)", type: "checkbox" },
      ]}
      emptyForm={{ product_name: "", silk_type_id: "", unit_of_measure: "", default_source_category_id: "", is_byproduct: "false", is_perishable: "false", show_in_dashboard: "true" }}
      toForm={(r) => ({
        product_name: r.product_name,
        silk_type_id: r.silk_type_id || "",
        unit_of_measure: r.unit_of_measure,
        default_source_category_id: r.default_source_category_id || "",
        is_byproduct: String(r.is_byproduct),
        is_perishable: String(r.is_perishable),
        show_in_dashboard: String(r.show_in_dashboard),
      })}
      buildPayload={(f) => ({
        product_name: f.product_name,
        silk_type_id: f.silk_type_id || null,
        unit_of_measure: f.unit_of_measure,
        default_source_category_id: f.default_source_category_id || null,
        is_byproduct: f.is_byproduct === "true",
        is_perishable: f.is_perishable === "true",
        show_in_dashboard: f.show_in_dashboard === "true",
      })}
    />
  );
}
