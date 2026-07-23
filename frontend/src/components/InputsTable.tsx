"use client";
import { Fragment } from "react";
import type { Scheme, StapInputOption } from "@/lib/types";

export type InputRowState = Record<string, {
  quantity?: string; remarks?: string; source_type_id?: string; scheme_id?: string;
}>;

interface InputsTableProps {
  options: StapInputOption[];
  schemes: Scheme[];
  value: InputRowState;
  onChange: (productId: string, field: string, val: string) => void;
  getAutoFillQty?: (producingStapId: string | null | undefined, productId: string) => number | undefined;
}

function InputRow({ o, row, schemes, onChange, getAutoFillQty }: {
  o: StapInputOption; row: { quantity?: string; remarks?: string; source_type_id?: string; scheme_id?: string };
  schemes: Scheme[];
  onChange: (productId: string, field: string, val: string) => void;
  getAutoFillQty?: (producingStapId: string | null | undefined, productId: string) => number | undefined;
}) {
  const notMeasured = o.unit_of_measure === "Not Measured";
  const defaultSourceId = o.allowed_source_types.find((s) => s.is_own_source)?.id ?? o.allowed_source_types[0]?.id;
  const sourceTypeId = row.source_type_id || defaultSourceId;
  const selected = o.allowed_source_types.find((s) => s.id === sourceTypeId);

  function handleSourceChange(newId: string) {
    onChange(o.product_id, "source_type_id", newId);
    const opt = o.allowed_source_types.find((s) => s.id === newId);
    if (opt?.is_own_source && !row.quantity) {
      const autofill = getAutoFillQty?.(o.producing_stap_id, o.product_id);
      if (autofill !== undefined && autofill > 0) onChange(o.product_id, "quantity", String(autofill));
    }
  }

  return (
    <tr>
      <td>{o.product_name} <span style={{ color: "var(--text-muted)" }}>({o.unit_of_measure})</span></td>
      <td>
        {notMeasured ? (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={!!row.quantity && row.quantity !== "0"}
              onChange={(e) => onChange(o.product_id, "quantity", e.target.checked ? "1" : "")} />
            Occurred this month
          </label>
        ) : (
          <input type="number" className="input" value={row.quantity || ""}
            onChange={(e) => onChange(o.product_id, "quantity", e.target.value)} />
        )}
      </td>
      <td>
        <div className="flex flex-col gap-1">
          <select className="input" value={sourceTypeId || ""}
            onChange={(e) => handleSourceChange(e.target.value)}>
            {o.allowed_source_types.map((s) => <option key={s.id} value={s.id}>{s.source_name}</option>)}
          </select>
          {selected?.requires_scheme && (
            <select className="input" value={row.scheme_id || ""}
              onChange={(e) => onChange(o.product_id, "scheme_id", e.target.value)}>
              <option value="">Select scheme...</option>
              {schemes.map((s) => <option key={s.id} value={s.id}>{s.scheme_name}</option>)}
            </select>
          )}
        </div>
      </td>
    </tr>
  );
}

export function InputsTable({ options, schemes, value, onChange, getAutoFillQty }: InputsTableProps) {
  if (options.length === 0) return null;

  const grouped = new Map<string, StapInputOption[]>();
  const ungrouped: StapInputOption[] = [];
  for (const o of options) {
    if (o.input_group) {
      if (!grouped.has(o.input_group)) grouped.set(o.input_group, []);
      grouped.get(o.input_group)!.push(o);
    } else {
      ungrouped.push(o);
    }
  }

  return (
    <table className="seri-table">
      <thead>
        <tr><th>Input</th><th>Quantity</th><th>Source</th></tr>
      </thead>
      <tbody>
        {ungrouped.map((o) => {
          const row = value[o.product_id] || {};
          return (
            <InputRow key={o.product_id} o={o} row={row}
              schemes={schemes} onChange={onChange} getAutoFillQty={getAutoFillQty} />
          );
        })}
        {Array.from(grouped.entries()).map(([label, opts]) => (
          <Fragment key={`group-${label}`}>
            <tr>
              <td colSpan={3} className="text-xs font-semibold pt-2" style={{ color: "var(--text-muted)" }}>
                {label} — what did you use?
              </td>
            </tr>
            {opts.map((o) => {
              const row = value[o.product_id] || {};
              return (
                <InputRow key={o.product_id} o={o} row={row}
                  schemes={schemes} onChange={onChange} getAutoFillQty={getAutoFillQty} />
              );
            })}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}
