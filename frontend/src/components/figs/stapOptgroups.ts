import type { SilkTypeActivityProduct } from "@/lib/types";

export const stapLabel = (s: SilkTypeActivityProduct) => `${s.silk_type_name} · ${s.activity_name} · ${s.product_name}`;

export function stapOptgroups(staps: SilkTypeActivityProduct[]) {
  const groups: Record<string, SilkTypeActivityProduct[]> = {};
  for (const s of staps) {
    groups[s.silk_type_name] = groups[s.silk_type_name] || [];
    groups[s.silk_type_name].push(s);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
}
