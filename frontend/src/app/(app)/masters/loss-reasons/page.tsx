"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface LossReason { id: string; reason_name: string; is_active: boolean }

export default function LossReasonsPage() {
  return (
    <MasterCrud<LossReason>
      title="Loss Reasons"
      description="Reasons a FIG President can select when reported yield falls well short of plan."
      endpoint="loss-reasons"
      queryKey="master-loss-reasons"
      searchOn={["reason_name"]}
      addLabel="Add Loss Reason"
      columns={[{ key: "reason_name", label: "Reason", render: (r) => <span className="font-semibold">{r.reason_name}</span> }]}
      fields={[{ name: "reason_name", label: "Reason", type: "text", required: true, placeholder: "e.g. Disease outbreak" }]}
      emptyForm={{ reason_name: "" }}
      toForm={(r) => ({ reason_name: r.reason_name })}
      buildPayload={(f) => ({ reason_name: f.reason_name })}
    />
  );
}
