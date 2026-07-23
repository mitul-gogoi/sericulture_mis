"use client";
import { MasterCrud } from "@/components/MasterCrud";
import type { InputSourceCategory } from "@/lib/types";

export default function InputSourceCategoriesPage() {
  return (
    <MasterCrud<InputSourceCategory>
      title="Input Source Categories"
      description="Groups Input Source Types by kind (e.g. Land Related, Produce Related) so a Product's default and an Activity Input mapping in Map Activity to Product can restrict which source types apply."
      endpoint="input-source-categories"
      queryKey="master-input-source-categories"
      searchOn={["category_name"]}
      addLabel="Add Input Source Category"
      columns={[{ key: "category_name", label: "Category", render: (r) => <span className="font-semibold">{r.category_name}</span> }]}
      fields={[{ name: "category_name", label: "Category name", type: "text", required: true, placeholder: "e.g. Land Related" }]}
      emptyForm={{ category_name: "" }}
      toForm={(r) => ({ category_name: r.category_name })}
      buildPayload={(f) => ({ category_name: f.category_name })}
    />
  );
}
