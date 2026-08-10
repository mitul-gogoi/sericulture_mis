"use client";
import { useQuery } from "@tanstack/react-query";
import { MasterCrud } from "@/components/MasterCrud";
import api from "@/lib/api";
import type { SilkType, Product, ConversionStandard } from "@/lib/types";

export default function ConversionStandardsPage() {
  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["master-products-all"],
    queryFn: async () => (await api.get("/master/products?all=true")).data,
  });

  const productOptionsFor = (form: Record<string, string>) =>
    products
      .filter((p) => !p.silk_type_id || p.silk_type_id === form.silk_type_id)
      .sort((a, b) => a.product_name.localeCompare(b.product_name))
      .map((p) => ({ value: p.id, label: `${p.product_name} (${p.unit_of_measure})` }));

  const unitFor = (productId: string) => products.find((p) => p.id === productId)?.unit_of_measure || "units";

  const expectedPctLabel = (form: Record<string, string>) => {
    const input = Number(form.standard_input_qty);
    const min = Number(form.output_min_qty);
    const max = Number(form.output_max_qty);
    if (!input || input <= 0 || !Number.isFinite(min) || !Number.isFinite(max) || min < 0 || max < 0) return null;
    const minPct = Math.round((min / input) * 100 * 10000) / 10000;
    const maxPct = Math.round((max / input) * 100 * 10000) / 10000;
    return `→ Expected conversion: ${minPct}%–${maxPct}%`;
  };

  return (
    <MasterCrud<ConversionStandard>
      title="Conversion Standards"
      description="Set an expected input→output conversion range by quantity (e.g. 100 Eri Eggs (DFL) should yield 20–25 kg Eri Cocoon), independent of which activities sit in between — the system calculates the percentage range automatically. Shown as an 'Expected' range next to Actual output in the Yield View."
      endpoint="conversion-standards"
      queryKey="master-conversion-standards"
      searchOn={["silk_type_name", "input_product_name", "output_product_name"]}
      columns={[
        { key: "silk_type_name", label: "Silk Type" },
        { key: "input_product_name", label: "Input Product" },
        { key: "standard_input_qty", label: "For Input Qty", render: (r) => `${r.standard_input_qty} ${r.input_unit_of_measure || ""}` },
        { key: "output_product_name", label: "Output Product" },
        { key: "output_min_qty", label: "Output Min Qty", render: (r) => `${r.output_min_qty} ${r.output_unit_of_measure || ""}` },
        { key: "output_max_qty", label: "Output Max Qty", render: (r) => `${r.output_max_qty} ${r.output_unit_of_measure || ""}` },
        { key: "min_pct", label: "Conversion %", render: (r) => `${r.min_pct}%–${r.max_pct}%` },
      ]}
      fields={[
        { name: "silk_type_id", label: "Silk Type", type: "select", required: true,
          options: silkTypes.map((s) => ({ value: s.id, label: s.silk_type_name })) },
        { name: "input_product_id", label: "Input Product", type: "select", required: true, options: productOptionsFor },
        { name: "output_product_id", label: "Output Product", type: "select", required: true, options: productOptionsFor },
        {
          name: "standard_input_qty",
          label: (form) => `For Input Quantity (in ${unitFor(form.input_product_id)})`,
          type: "number", required: true, placeholder: "e.g. 100",
        },
        {
          name: "output_min_qty",
          label: (form) => `Output Min Quantity (${unitFor(form.output_product_id)})`,
          type: "number", required: true, placeholder: "e.g. 20",
        },
        {
          name: "output_max_qty",
          label: (form) => `Output Max Quantity (${unitFor(form.output_product_id)})`,
          type: "number", required: true, placeholder: "e.g. 25",
          helperText: expectedPctLabel,
        },
      ]}
      emptyForm={{ silk_type_id: "", input_product_id: "", output_product_id: "", standard_input_qty: "", output_min_qty: "", output_max_qty: "" }}
      toForm={(r) => ({
        silk_type_id: r.silk_type_id,
        input_product_id: r.input_product_id,
        output_product_id: r.output_product_id,
        standard_input_qty: String(r.standard_input_qty),
        output_min_qty: String(r.output_min_qty),
        output_max_qty: String(r.output_max_qty),
      })}
      buildPayload={(f) => ({
        silk_type_id: f.silk_type_id,
        input_product_id: f.input_product_id,
        output_product_id: f.output_product_id,
        standard_input_qty: Number(f.standard_input_qty),
        output_min_qty: Number(f.output_min_qty),
        output_max_qty: Number(f.output_max_qty),
      })}
    />
  );
}
