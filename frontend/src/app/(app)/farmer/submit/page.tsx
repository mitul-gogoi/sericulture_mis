"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueries } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { Farmer, Scheme, StapOptions, LossReason, StapOption, Stock, FarmerSubmissionDetail } from "@/lib/types";
import { OutputsTable, OutputRowState, ByproductRowState } from "@/components/OutputsTable";
import { InputsTable, InputRowState } from "@/components/InputsTable";

type ActivityState = { primaryOutput: OutputRowState; byproducts: ByproductRowState; inputs: InputRowState };
function emptyActivity(): ActivityState { return { primaryOutput: {}, byproducts: {}, inputs: {} }; }

function currentMonth() { return new Date().toISOString().slice(0, 7); }

export default function FarmerSubmitPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const correctSubmissionId = searchParams.get("correctSubmissionId");
  const isCorrection = !!correctSubmissionId;
  const [month, setMonth] = useState(currentMonth());
  const [entries, setEntries] = useState<Record<string, ActivityState>>({});
  const [submitted, setSubmitted] = useState(false);
  const [prefilled, setPrefilled] = useState(!isCorrection);

  useEffect(() => { if (user && user.role !== "FARMER") router.replace("/dashboard"); }, [user, router]);

  const { data: me } = useQuery<Farmer>({
    queryKey: ["farmer-me"], queryFn: async () => (await api.get("/farmers/me")).data, enabled: !!user,
  });

  const { data: correctionSource } = useQuery<FarmerSubmissionDetail>({
    queryKey: ["farmer-submission-correction-source", correctSubmissionId],
    queryFn: async () => (await api.get(`/farmers/me/submissions/${correctSubmissionId}`)).data,
    enabled: isCorrection,
  });

  useEffect(() => {
    if (!correctionSource || prefilled) return;
    setMonth(correctionSource.submission.submission_month);
    const newEntries: Record<string, ActivityState> = {};
    for (const e of correctionSource.entries) {
      const byproducts: ByproductRowState = {};
      for (const b of e.byproducts) {
        byproducts[b.product_id] = {
          actual: String(b.quantity), planned: String(b.planned_quantity),
          next_plan: String(b.next_month_plan), stock: String(b.stock_balance),
          sold_qty: String(b.sold_quantity), sold_rate: String(b.sold_rate),
          loss_reason_id: b.loss_reason_id || undefined,
        };
      }
      const inputs: InputRowState = {};
      for (const i of e.inputs) {
        inputs[i.product_id] = { quantity: String(i.quantity), source_type_id: i.source_type_id || undefined, scheme_id: i.scheme_id || undefined };
      }
      newEntries[e.stap_id] = {
        primaryOutput: {
          planned: String(e.output.planned_yield), actual: String(e.output.actual_yield),
          next_plan: String(e.output.next_month_plan), stock: String(e.output.stock_balance),
          sold_qty: String(e.output.sold_quantity), sold_rate: String(e.output.sold_rate),
          loss_reason_id: e.output.loss_reason_id || undefined,
        },
        byproducts, inputs,
      };
    }
    setEntries(newEntries);
    setPrefilled(true);
  }, [correctionSource, prefilled]);

  const stapIds = me?.stap_ids || [];

  const optionsQueries = useQueries({
    queries: stapIds.map((stapId) => ({
      queryKey: ["stap-options", stapId],
      queryFn: async () => (await api.get(`/master/silk-type-activity-products/${stapId}/options`)).data as StapOptions,
    })),
  });
  const optionsByStap = useMemo(() => {
    const m: Record<string, StapOptions> = {};
    stapIds.forEach((id, i) => { if (optionsQueries[i]?.data) m[id] = optionsQueries[i].data as StapOptions; });
    return m;
  }, [stapIds, optionsQueries]);

  const { data: schemes = [] } = useQuery<Scheme[]>({ queryKey: ["schemes"], queryFn: async () => (await api.get("/schemes")).data });
  const { data: lossReasons = [] } = useQuery<LossReason[]>({ queryKey: ["loss-reasons"], queryFn: async () => (await api.get("/master/loss-reasons")).data });
  const { data: stockRows = [] } = useQuery<Stock[]>({ queryKey: ["stock-own"], queryFn: async () => (await api.get("/stock")).data, enabled: !!user });
  const stockByProduct = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of stockRows) m[s.product_id] = s.closing_balance;
    return m;
  }, [stockRows]);

  function getEntry(stapId: string): ActivityState { return entries[stapId] || emptyActivity(); }
  function updatePrimaryField(stapId: string, field: string, val: string) {
    setEntries((prev) => ({ ...prev, [stapId]: { ...getEntry(stapId), primaryOutput: { ...getEntry(stapId).primaryOutput, [field]: val } } }));
  }
  function updateByproduct(stapId: string, productId: string, field: string, val: string) {
    const a = getEntry(stapId);
    setEntries((prev) => ({ ...prev, [stapId]: { ...a, byproducts: { ...a.byproducts, [productId]: { ...a.byproducts[productId], [field]: val } } } }));
  }
  function updateInput(stapId: string, productId: string, field: string, val: string) {
    const a = getEntry(stapId);
    setEntries((prev) => ({ ...prev, [stapId]: { ...a, inputs: { ...a.inputs, [productId]: { ...a.inputs[productId], [field]: val } } } }));
  }

  function effectiveByproducts(state: ByproductRowState, options: StapOption[]): ByproductRowState {
    const out: ByproductRowState = {};
    for (const o of options) out[o.product_id] = state[o.product_id] || {};
    return out;
  }

  const submit = async () => {
    try {
      const entriesArr: Record<string, unknown>[] = [];
      for (const [stapId, v] of Object.entries(entries)) {
        const byproducts = Object.entries(v.byproducts)
          .map(([pid, bv]) => ({
            product_id: pid, quantity: parseFloat(bv.actual || "0") || 0,
            planned_quantity: parseFloat(bv.planned || "0") || 0,
            next_month_plan: parseFloat(bv.next_plan || "0") || 0, stock_balance: parseFloat(bv.stock || "0") || 0,
            sold_quantity: parseFloat(bv.sold_qty || "0") || 0, sold_rate: parseFloat(bv.sold_rate || "0") || 0,
            loss_reason_id: bv.loss_reason_id || null,
          }))
          .filter((e) => e.quantity > 0);
        const inputOpts = optionsByStap[stapId]?.inputs || [];
        const inputs = Object.entries(v.inputs)
          .map(([pid, iv]) => {
            const opt = inputOpts.find((o) => o.product_id === pid);
            const defaultId = opt?.allowed_source_types.find((s) => s.is_own_source)?.id ?? opt?.allowed_source_types[0]?.id;
            const sourceTypeId = iv.source_type_id || defaultId || "";
            const selected = opt?.allowed_source_types.find((s) => s.id === sourceTypeId);
            return { product_id: pid, quantity: parseFloat(iv.quantity || "0") || 0, source_type_id: sourceTypeId, scheme_id: selected?.requires_scheme ? (iv.scheme_id || null) : null };
          })
          .filter((e) => e.quantity > 0);
        const p = v.primaryOutput;
        const touched = p.planned || p.actual || p.next_plan || p.stock || p.sold_qty || p.sold_rate || p.loss_reason_id || byproducts.length || inputs.length;
        if (!touched) continue;
        entriesArr.push({
          stap_id: stapId, planned: p.planned, actual: p.actual, next_plan: p.next_plan, stock: p.stock,
          sold_qty: p.sold_qty, sold_rate: p.sold_rate, loss_reason_id: p.loss_reason_id || null, byproducts, inputs,
        });
      }
      if (isCorrection) {
        await api.post(`/farmers/me/submissions/${correctSubmissionId}/resubmit`, { entries: entriesArr });
        toast.success("Resubmission sent for review");
      } else {
        await api.post("/farmers/me/submissions", { submission_month: month, entries: entriesArr });
        toast.success("Submitted successfully");
      }
      setSubmitted(true);
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  if (submitted) {
    return (
      <div className="card p-10 text-center">
        <CheckCircle size={56} weight="duotone" color="#2D5134" className="mx-auto" />
        <h2 className="font-heading text-2xl font-bold mt-4">{isCorrection ? "Resubmission sent" : "Submission recorded"}</h2>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          {isCorrection
            ? "Awaiting District Admin review — your original data stays live and unchanged until the resubmission is accepted."
            : "Your monthly production/stock data is now live and visible to your District/State Admin."}
        </p>
      </div>
    );
  }

  if (!me || (isCorrection && !prefilled)) return <div>Loading…</div>;

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">{isCorrection ? "Resubmit monthly data" : "Submit this month's data"}</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{me.first_name} {me.last_name} · {me.farmer_code}</p>
      </div>

      <div className="card p-6">
        <div className="mb-4">
          <label className="label-tag">Month</label>
          <input type="month" className="input mt-1 w-48" value={month} onChange={(e) => setMonth(e.target.value)} disabled={isCorrection} />
        </div>

        {stapIds.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>You have no assigned activities to report against yet — contact your District Admin.</p>
        ) : (
          stapIds.map((stapId, idx) => {
            const opts = optionsByStap[stapId];
            const activity = getEntry(stapId);
            return (
              <div key={stapId} className={idx > 0 ? "border-t pt-3 mt-3" : ""} style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-semibold text-sm">{opts?.primary?.product_name || "Loading activity…"}</span>
                </div>
                {!opts ? (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading options…</p>
                ) : (
                  <>
                    {opts.inputs.length > 0 && (
                      <>
                        <div className="label-tag mb-1">Inputs</div>
                        <InputsTable
                          options={opts.inputs} schemes={schemes} value={activity.inputs}
                          onChange={(productId, field, val) => updateInput(stapId, productId, field, val)}
                          getAutoFillQty={(producingStapId, productId) => {
                            const stock = stockByProduct[productId] || 0;
                            const cycleOutput = producingStapId ? parseFloat(getEntry(producingStapId).primaryOutput.actual || "0") || 0 : 0;
                            const total = stock + cycleOutput;
                            return total > 0 ? total : undefined;
                          }}
                        />
                      </>
                    )}
                    <div className="label-tag mt-3 mb-1">Outputs</div>
                    <OutputsTable
                      primary={opts.primary} primaryValue={activity.primaryOutput}
                      onPrimaryChange={(field, val) => updatePrimaryField(stapId, field, val)}
                      byproductOptions={opts.byproducts}
                      byproductValue={effectiveByproducts(activity.byproducts, opts.byproducts)}
                      onByproductChange={(productId, field, val) => updateByproduct(stapId, productId, field, val)}
                      lossReasons={lossReasons}
                    />
                  </>
                )}
              </div>
            );
          })
        )}

        <div className="flex justify-end mt-6">
          <button data-testid="farmer-submit" className="btn-primary inline-flex items-center gap-2" onClick={submit} disabled={stapIds.length === 0}>
            {isCorrection ? "Submit resubmission for review" : "Submit"}<CheckCircle size={14} weight="bold" />
          </button>
        </div>
      </div>
    </div>
  );
}
