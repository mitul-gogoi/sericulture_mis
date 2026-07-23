export function ViewField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <label className="label-tag">{label}</label>
      <div className="mt-1 text-sm">{value ?? "—"}</div>
    </div>
  );
}
