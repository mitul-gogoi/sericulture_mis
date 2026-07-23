"use client";
import type { StapOption, LossReason } from "@/lib/types";

export type OutputRowState = {
  planned?: string; actual?: string; sold_qty?: string; sold_rate?: string;
  stock?: string; next_plan?: string; loss_reason_id?: string;
};
export type ByproductRowState = Record<string, OutputRowState>;

interface OutputsTableProps {
  primary: StapOption | null;
  primaryValue: OutputRowState;
  onPrimaryChange: (field: string, val: string) => void;
  byproductOptions: StapOption[];
  byproductValue: ByproductRowState;
  onByproductChange: (productId: string, field: string, val: string) => void;
  lossReasons: LossReason[];
}

function OutputRow({ name, uom, category, value, onChange, lossReasons }: {
  name: string; uom: string; category: "primary" | "secondary";
  value: OutputRowState; onChange: (field: string, val: string) => void; lossReasons: LossReason[];
}) {
  return (
    <tr>
      <td>{name} <span style={{ color: "var(--text-muted)" }}>({uom})</span></td>
      <td><span className={`badge ${category === "primary" ? "badge-success" : "badge-muted"}`}>
        {category === "primary" ? "Primary Product" : "Secondary Product"}
      </span></td>
      <td><input type="number" className="input" value={value.planned || ""}
        onChange={(e) => onChange("planned", e.target.value)} /></td>
      <td><input type="number" className="input" value={value.actual || ""}
        onChange={(e) => onChange("actual", e.target.value)} /></td>
      <td><input type="number" className="input" value={value.sold_qty || ""}
        onChange={(e) => onChange("sold_qty", e.target.value)} /></td>
      <td><input type="number" className="input" value={value.sold_rate || ""}
        onChange={(e) => onChange("sold_rate", e.target.value)} /></td>
      <td><input type="number" className="input" value={value.stock || ""}
        onChange={(e) => onChange("stock", e.target.value)} /></td>
      <td><input type="number" className="input" value={value.next_plan || ""}
        onChange={(e) => onChange("next_plan", e.target.value)} /></td>
      <td>
        <select className="input" value={value.loss_reason_id || ""}
          onChange={(e) => onChange("loss_reason_id", e.target.value)}>
          <option value="">—</option>
          {lossReasons.map((lr) => <option key={lr.id} value={lr.id}>{lr.reason_name}</option>)}
        </select>
      </td>
    </tr>
  );
}

export function OutputsTable({ primary, primaryValue, onPrimaryChange, byproductOptions, byproductValue, onByproductChange, lossReasons }: OutputsTableProps) {
  if (!primary && byproductOptions.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="seri-table">
        <thead>
          <tr>
            <th>Product</th><th>Category</th><th>Planned Qty</th><th>Qty Produced</th>
            <th>Qty Sold</th><th>Sold Rate</th><th>Current Stock</th><th>Next Month Plan</th><th>Loss Reason</th>
          </tr>
        </thead>
        <tbody>
          {primary && (
            <OutputRow name={primary.product_name} uom={primary.unit_of_measure} category="primary"
              value={primaryValue} onChange={onPrimaryChange} lossReasons={lossReasons} />
          )}
          {byproductOptions.map((o) => (
            <OutputRow key={o.product_id} name={o.product_name} uom={o.unit_of_measure} category="secondary"
              value={byproductValue[o.product_id] || {}}
              onChange={(field, val) => onByproductChange(o.product_id, field, val)}
              lossReasons={lossReasons} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
