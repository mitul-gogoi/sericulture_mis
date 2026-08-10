"use client";
import { useEffect, useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueries } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CheckCircle, ArrowRight, ArrowLeft } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { FigDetail, Yield, ByproductEntry, Scheme, StapOptions, LossReason, StapOption, Stock, SilkTypeActivityProduct, MeetingDetail } from "@/lib/types";
import FileUpload from "@/components/FileUpload";
import { OutputsTable, OutputRowState, ByproductRowState } from "@/components/OutputsTable";
import { InputsTable, InputRowState } from "@/components/InputsTable";

const STEPS = ["Meeting", "Attendance", "Submission", "Review"];

type ActivityState = {
  primaryOutput: OutputRowState;
  byproducts: ByproductRowState;
  inputs: InputRowState;
};

function emptyActivity(): ActivityState {
  return { primaryOutput: {}, byproducts: {}, inputs: {} };
}

function prevMonthOf(dateStr: string): string | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 7);
}

type FarmerStatus = "not-started" | "in-progress" | "done";

function farmerStatus(farmerId: string, stapIds: string[], entries: Record<string, Record<string, ActivityState>>): FarmerStatus {
  const byStap = entries[farmerId];
  if (!byStap || Object.keys(byStap).length === 0) return "not-started";
  const anyTouched = stapIds.some((sid) => {
    const a = byStap[sid];
    if (!a) return false;
    return !!(a.primaryOutput.actual || a.primaryOutput.planned || Object.keys(a.inputs).length || Object.keys(a.byproducts).length);
  });
  if (!anyTouched) return "not-started";
  const allDone = stapIds.length > 0 && stapIds.every((sid) => !!byStap[sid]?.primaryOutput.actual);
  return allDone ? "done" : "in-progress";
}

export default function MonthlySubmissionPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const correctMeetingId = searchParams.get("correctMeetingId");
  const isCorrection = !!correctMeetingId;
  const [step, setStep] = useState(0);
  const [meeting, setMeeting] = useState({
    meeting_title: "", meeting_date: "", meeting_time: "", meeting_venue: "",
    meeting_details: "", next_meeting_date: "", minutes_path: null as string | null,
  });
  const [attendance, setAttendance] = useState<Record<string, boolean>>({});
  const [entries, setEntries] = useState<Record<string, Record<string, ActivityState>>>({});
  const [submitted, setSubmitted] = useState(false);
  const [selectedFarmerId, setSelectedFarmerId] = useState<string | null>(null);

  useEffect(() => { if (user && user.role !== "FIG_PRESIDENT") router.replace("/dashboard"); }, [user, router]);

  const { data: fig } = useQuery<FigDetail>({
    queryKey: ["fig", user?.fig_id], queryFn: async () => (await api.get(`/figs/${user!.fig_id}`)).data,
    enabled: !!user?.fig_id,
  });

  useEffect(() => {
    if (fig) {
      setMeeting((m) => ({ ...m, meeting_venue: m.meeting_venue || fig.meeting_venue || "" }));
      if (!isCorrection) {
        const att: Record<string, boolean> = {};
        fig.members.forEach((mm) => { att[mm.farmer_id] = true; });
        setAttendance(att);
      }
    }
  }, [fig, isCorrection]);

  const { data: correctionSource } = useQuery<MeetingDetail>({
    queryKey: ["meeting-correction-source", correctMeetingId],
    queryFn: async () => (await api.get(`/meetings/${correctMeetingId}`)).data,
    enabled: isCorrection,
  });

  const [prefilledFromCorrection, setPrefilledFromCorrection] = useState(false);
  useEffect(() => {
    if (!correctionSource || prefilledFromCorrection) return;
    const cm = correctionSource.meeting;
    setMeeting({
      meeting_title: cm.meeting_title, meeting_date: cm.meeting_date, meeting_time: cm.meeting_time || "",
      meeting_venue: cm.meeting_venue, meeting_details: cm.meeting_details || "",
      next_meeting_date: cm.next_meeting_date || "", minutes_path: cm.minutes_path || null,
    });

    const att: Record<string, boolean> = {};
    correctionSource.attendance.forEach((a) => { att[a.farmer_id] = a.is_present; });
    setAttendance(att);

    const newEntries: Record<string, Record<string, ActivityState>> = {};
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
        inputs[i.product_id] = {
          quantity: String(i.quantity), source_type_id: i.source_type_id || undefined, scheme_id: i.scheme_id || undefined,
        };
      }
      newEntries[e.farmer_id] = {
        ...(newEntries[e.farmer_id] || {}),
        [e.stap_id]: {
          primaryOutput: {
            planned: String(e.output.planned_yield), actual: String(e.output.actual_yield),
            next_plan: String(e.output.next_month_plan), stock: String(e.output.stock_balance),
            sold_qty: String(e.output.sold_quantity), sold_rate: String(e.output.sold_rate),
            loss_reason_id: e.output.loss_reason_id || undefined,
          },
          byproducts, inputs,
        },
      };
    }
    setEntries(newEntries);
    setPrefilledFromCorrection(true);
  }, [correctionSource, prefilledFromCorrection]);

  const meetingMonth = meeting.meeting_date ? meeting.meeting_date.slice(0, 7) : undefined;

  const { data: drafts } = useQuery<Record<string, { stap_id: string; [k: string]: unknown }[]>>({
    queryKey: ["fig-drafts", user?.fig_id, meetingMonth],
    queryFn: async () => (await api.get("/meetings/drafts", { params: { fig_id: user!.fig_id, month: meetingMonth } })).data,
    enabled: !!user?.fig_id && !!meetingMonth && !isCorrection,
  });

  const [draftsApplied, setDraftsApplied] = useState<string | null>(null);
  useEffect(() => {
    if (!drafts || isCorrection || draftsApplied === meetingMonth) return;
    setEntries((prev) => {
      const next = { ...prev };
      for (const [farmerId, draftEntries] of Object.entries(drafts)) {
        const farmerEntries = { ...(next[farmerId] || {}) };
        for (const e of draftEntries as any[]) {
          if (farmerEntries[e.stap_id]) continue; // never clobber a value the FIG President already typed
          const byproducts: ByproductRowState = {};
          for (const b of e.byproducts || []) {
            byproducts[b.product_id] = {
              actual: String(b.quantity), planned: String(b.planned_quantity),
              next_plan: String(b.next_month_plan), stock: String(b.stock_balance),
              sold_qty: String(b.sold_quantity), sold_rate: String(b.sold_rate),
              loss_reason_id: b.loss_reason_id || undefined,
            };
          }
          const inputs: InputRowState = {};
          for (const i of e.inputs || []) {
            inputs[i.product_id] = { quantity: String(i.quantity), source_type_id: i.source_type_id || undefined, scheme_id: i.scheme_id || undefined };
          }
          farmerEntries[e.stap_id] = {
            primaryOutput: {
              planned: e.planned, actual: e.actual, next_plan: e.next_plan, stock: e.stock,
              sold_qty: e.sold_qty, sold_rate: e.sold_rate, loss_reason_id: e.loss_reason_id || undefined,
            },
            byproducts, inputs,
          };
        }
        next[farmerId] = farmerEntries;
      }
      return next;
    });
    setDraftsApplied(meetingMonth || null);
  }, [drafts, isCorrection, meetingMonth, draftsApplied]);

  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1));
  const prev = () => setStep((s) => Math.max(0, s - 1));

  const presentMembers = useMemo(
    () => (fig ? fig.members.filter((m) => attendance[m.farmer_id]) : []),
    [fig, attendance],
  );

  useEffect(() => {
    if (step === 2 && presentMembers.length > 0 && !selectedFarmerId) {
      setSelectedFarmerId(presentMembers[0].farmer_id);
    }
  }, [step, presentMembers, selectedFarmerId]);

  const { data: allStaps = [] } = useQuery<SilkTypeActivityProduct[]>({
    queryKey: ["master-stap-all"],
    queryFn: async () => (await api.get("/master/silk-type-activity-products?all=true")).data,
  });
  const stepNoByStap = useMemo(
    () => Object.fromEntries(allStaps.map((s) => [s.id, s.step_no ?? 0])),
    [allStaps],
  );

  const activityStapIds = (farmerStapIds: string[]) =>
    [...farmerStapIds].sort((a, b) => (stepNoByStap[a] ?? 0) - (stepNoByStap[b] ?? 0));

  const prevMonth = useMemo(() => prevMonthOf(meeting.meeting_date), [meeting.meeting_date]);

  const { data: prevYields = [] } = useQuery<Yield[]>({
    queryKey: ["yields-prev", user?.fig_id, prevMonth],
    queryFn: async () => (await api.get(`/yields?fig_id=${user!.fig_id}&month=${prevMonth}`)).data,
    enabled: !!user?.fig_id && !!prevMonth,
  });

  const { data: prevByproducts = [] } = useQuery<ByproductEntry[]>({
    queryKey: ["byproducts-prev", user?.fig_id, prevMonth],
    queryFn: async () => (await api.get(`/byproducts?fig_id=${user!.fig_id}&month=${prevMonth}`)).data,
    enabled: !!user?.fig_id && !!prevMonth,
  });

  useEffect(() => {
    if (!prevYields.length) return;
    setEntries((prev) => {
      const next = { ...prev };
      for (const py of prevYields) {
        const farmerEntries = { ...(next[py.farmer_id] || {}) };
        const existing = farmerEntries[py.stap_id] || emptyActivity();
        if (existing.primaryOutput.planned === undefined || existing.primaryOutput.planned === "") {
          farmerEntries[py.stap_id] = { ...existing, primaryOutput: { ...existing.primaryOutput, planned: String(py.next_month_plan ?? "") } };
          next[py.farmer_id] = farmerEntries;
        }
      }
      return next;
    });
  }, [prevYields]);

  const prevByproductPlan = useMemo(() => {
    const m: Record<string, number> = {};
    for (const bp of prevByproducts) m[`${bp.farmer_id}:${bp.product_id}`] = bp.next_month_plan;
    return m;
  }, [prevByproducts]);

  const distinctStapIds = useMemo(
    () => Array.from(new Set(presentMembers.flatMap((m) => m.farmer?.stap_ids || []))),
    [presentMembers],
  );

  const optionsQueries = useQueries({
    queries: distinctStapIds.map((stapId) => ({
      queryKey: ["stap-options", stapId],
      queryFn: async () => (await api.get(`/master/silk-type-activity-products/${stapId}/options`)).data as StapOptions,
    })),
  });

  const optionsByStap = useMemo(() => {
    const m: Record<string, StapOptions> = {};
    distinctStapIds.forEach((id, i) => { if (optionsQueries[i]?.data) m[id] = optionsQueries[i].data as StapOptions; });
    return m;
  }, [distinctStapIds, optionsQueries]);

  const { data: schemes = [] } = useQuery<Scheme[]>({
    queryKey: ["schemes"],
    queryFn: async () => (await api.get(`/schemes`)).data,
  });

  const { data: lossReasons = [] } = useQuery<LossReason[]>({
    queryKey: ["loss-reasons"],
    queryFn: async () => (await api.get(`/master/loss-reasons`)).data,
  });

  const { data: stockRows = [] } = useQuery<Stock[]>({
    queryKey: ["stock-fig", user?.fig_id],
    queryFn: async () => (await api.get(`/stock?fig_id=${user!.fig_id}`)).data,
    enabled: !!user?.fig_id,
  });

  const stockByFarmerProduct = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of stockRows) m[`${s.farmer_id}:${s.product_id}`] = s.closing_balance;
    return m;
  }, [stockRows]);

  function getEntry(farmerId: string, stapId: string): ActivityState {
    return entries[farmerId]?.[stapId] || emptyActivity();
  }

  function updatePrimaryField(farmerId: string, stapId: string, field: string, val: string) {
    setEntries((prev) => {
      const activity = getEntry(farmerId, stapId);
      return {
        ...prev,
        [farmerId]: { ...prev[farmerId], [stapId]: { ...activity, primaryOutput: { ...activity.primaryOutput, [field]: val } } },
      };
    });
  }

  function updateByproduct(farmerId: string, stapId: string, productId: string, field: string, val: string) {
    setEntries((prev) => {
      const activity = getEntry(farmerId, stapId);
      return {
        ...prev,
        [farmerId]: {
          ...prev[farmerId],
          [stapId]: { ...activity, byproducts: { ...activity.byproducts, [productId]: { ...activity.byproducts[productId], [field]: val } } },
        },
      };
    });
  }

  function updateInput(farmerId: string, stapId: string, productId: string, field: string, val: string) {
    setEntries((prev) => {
      const activity = getEntry(farmerId, stapId);
      return {
        ...prev,
        [farmerId]: {
          ...prev[farmerId],
          [stapId]: { ...activity, inputs: { ...activity.inputs, [productId]: { ...activity.inputs[productId], [field]: val } } },
        },
      };
    });
  }

  function effectiveByproducts(farmerId: string, state: ByproductRowState, options: StapOption[]): ByproductRowState {
    const out: ByproductRowState = {};
    for (const o of options) {
      const existing = state[o.product_id] || {};
      const fallback = prevByproductPlan[`${farmerId}:${o.product_id}`];
      out[o.product_id] = {
        ...existing,
        planned: existing.planned !== undefined ? existing.planned : (fallback !== undefined ? String(fallback) : undefined),
      };
    }
    return out;
  }

  const flatEntries = useMemo(
    () => Object.values(entries).flatMap((byStap) => Object.values(byStap)),
    [entries],
  );
  const byproductEntryCount = flatEntries.reduce((n, a) => n + Object.keys(a.byproducts).length, 0);
  const inputEntryCount = flatEntries.reduce((n, a) => n + Object.keys(a.inputs).length, 0);

  const submit = async () => {
    try {
      const entriesArr: Record<string, unknown>[] = [];
      for (const [farmerId, byStap] of Object.entries(entries)) {
        for (const [stapId, v] of Object.entries(byStap)) {
          const byproducts = Object.entries(v.byproducts)
            .map(([pid, bv]) => {
              const fallback = prevByproductPlan[`${farmerId}:${pid}`];
              const planned = bv.planned !== undefined ? bv.planned : (fallback !== undefined ? String(fallback) : "");
              return {
                product_id: pid,
                quantity: parseFloat(bv.actual || "0") || 0,
                planned_quantity: parseFloat(planned || "0") || 0,
                next_month_plan: parseFloat(bv.next_plan || "0") || 0,
                stock_balance: parseFloat(bv.stock || "0") || 0,
                sold_quantity: parseFloat(bv.sold_qty || "0") || 0,
                sold_rate: parseFloat(bv.sold_rate || "0") || 0,
                loss_reason_id: bv.loss_reason_id || null,
              };
            })
            .filter((e) => e.quantity > 0);
          const inputOpts = optionsByStap[stapId]?.inputs || [];
          const inputs = Object.entries(v.inputs)
            .map(([pid, iv]) => {
              const opt = inputOpts.find((o) => o.product_id === pid);
              const defaultId = opt?.allowed_source_types.find((s) => s.is_own_source)?.id ?? opt?.allowed_source_types[0]?.id;
              const sourceTypeId = iv.source_type_id || defaultId || "";
              const selected = opt?.allowed_source_types.find((s) => s.id === sourceTypeId);
              return {
                product_id: pid,
                quantity: parseFloat(iv.quantity || "0") || 0,
                source_type_id: sourceTypeId,
                scheme_id: selected?.requires_scheme ? (iv.scheme_id || null) : null,
              };
            })
            .filter((e) => e.quantity > 0);
          const p = v.primaryOutput;
          const touched = p.planned || p.actual || p.next_plan || p.stock || p.sold_qty || p.sold_rate
            || p.loss_reason_id || byproducts.length || inputs.length;
          if (!touched) continue;
          entriesArr.push({
            farmer_id: farmerId, stap_id: stapId,
            planned: p.planned, actual: p.actual, next_plan: p.next_plan, stock: p.stock,
            sold_qty: p.sold_qty, sold_rate: p.sold_rate, loss_reason_id: p.loss_reason_id || null,
            byproducts, inputs,
          });
        }
      }
      const body = {
        ...meeting, next_meeting_date: meeting.next_meeting_date || null,
        attendance: Object.entries(attendance).map(([fid, p]) => ({ farmer_id: fid, is_present: p })),
        entries: entriesArr,
      };
      if (isCorrection) {
        await api.post(`/meetings/${correctMeetingId}/corrections`, body);
        toast.success("Correction submitted for review");
      } else {
        await api.post("/meetings", { fig_id: user!.fig_id, ...body });
        toast.success("Submitted successfully");
      }
      setSubmitted(true);
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  if (submitted) {
    return (
      <div className="card p-10 text-center">
        <CheckCircle size={56} weight="duotone" color="#2D5134" className="mx-auto" />
        <h2 className="font-heading text-2xl font-bold mt-4">{isCorrection ? "Correction submitted" : "Submission recorded"}</h2>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          {isCorrection
            ? "Awaiting State Admin review — your original submission stays live and unchanged until the correction is accepted."
            : "Your meeting and yield data is locked for this month."}
        </p>
      </div>
    );
  }

  if (!fig || (isCorrection && !prefilledFromCorrection)) return <div>Loading…</div>;

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">{isCorrection ? "Correct monthly meeting & yield" : "Monthly meeting & yield"}</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{fig.fig_name} · {fig.fig_code}</p>
        {isCorrection && (
          <p className="text-xs mt-1" style={{ color: "var(--warning)" }}>
            Editing an already-submitted month for {correctionSource?.meeting.meeting_month} — this won&apos;t take effect until your State Admin accepts it.
          </p>
        )}
      </div>

      <div className="flex gap-1 mb-6">
        {STEPS.map((label, i) => (
          <div key={label} className={`wizard-step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>
            <span className="num">{i < step ? "✓" : i + 1}</span><span>{label}</span>
          </div>
        ))}
      </div>

      <div className="card p-6">
        {step === 0 && (
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2"><label className="label-tag">Meeting title</label><input data-testid="meeting-title" className="input mt-1" value={meeting.meeting_title} onChange={(e) => setMeeting({ ...meeting, meeting_title: e.target.value })} /></div>
            <div><label className="label-tag">Date</label><input type="date" data-testid="meeting-date" className="input mt-1" value={meeting.meeting_date} onChange={(e) => setMeeting({ ...meeting, meeting_date: e.target.value })} /></div>
            <div><label className="label-tag">Time</label><input type="time" className="input mt-1" value={meeting.meeting_time} onChange={(e) => setMeeting({ ...meeting, meeting_time: e.target.value })} /></div>
            <div className="col-span-2"><label className="label-tag">Venue</label><input className="input mt-1" value={meeting.meeting_venue} onChange={(e) => setMeeting({ ...meeting, meeting_venue: e.target.value })} /></div>
            <div className="col-span-2"><label className="label-tag">Details</label><textarea className="input mt-1" rows={3} value={meeting.meeting_details} onChange={(e) => setMeeting({ ...meeting, meeting_details: e.target.value })} /></div>
            <div className="col-span-2">
              <label className="label-tag">Minutes of meeting</label>
              <div className="mt-1">
                <FileUpload label="Upload minutes of meeting" testId="meeting-minutes-upload"
                  value={meeting.minutes_path} onChange={(p) => setMeeting({ ...meeting, minutes_path: p })}
                  category="fig_minutes" month={meeting.meeting_date ? meeting.meeting_date.slice(0, 7) : undefined} />
              </div>
            </div>
            <div><label className="label-tag">Next meeting</label><input type="date" className="input mt-1" value={meeting.next_meeting_date} onChange={(e) => setMeeting({ ...meeting, next_meeting_date: e.target.value })} /></div>
          </div>
        )}

        {step === 1 && (
          <table className="seri-table">
            <thead><tr><th>Member</th><th>Mobile</th><th>Present</th></tr></thead>
            <tbody>
              {fig.members.map((m) => (
                <tr key={m.farmer_id}>
                  <td className="font-semibold">{m.farmer?.first_name} {m.farmer?.last_name}</td>
                  <td>{m.farmer?.mobile_no}</td>
                  <td><input type="checkbox" data-testid={`attendance-${m.farmer_id}`} checked={!!attendance[m.farmer_id]} onChange={(e) => setAttendance({ ...attendance, [m.farmer_id]: e.target.checked })} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Record every activity each present member is doing this month — inputs consumed and outputs (primary + byproducts) produced.
            </p>
            <div className="flex flex-col md:flex-row gap-4" style={{ minHeight: 400 }}>
              <div className="w-full md:w-56 flex-shrink-0 border rounded overflow-y-auto max-h-48 md:max-h-[600px]" style={{ borderColor: "var(--border)" }} data-testid="submission-farmer-sidebar">
                {presentMembers.map((m) => {
                  const farmer = m.farmer;
                  const stapIds = activityStapIds(farmer?.stap_ids || []);
                  const status = farmerStatus(m.farmer_id, stapIds, entries);
                  const isSelected = m.farmer_id === selectedFarmerId;
                  return (
                    <button key={m.farmer_id} type="button" onClick={() => setSelectedFarmerId(m.farmer_id)}
                      className="w-full text-left px-3 py-2 text-sm border-b last:border-b-0 flex items-center gap-2"
                      style={{ borderColor: "var(--border)", background: isSelected ? "var(--primary)" : "transparent", color: isSelected ? "white" : "inherit" }}
                      data-testid={`submission-farmer-tab-${m.farmer_id}`}
                    >
                      <span style={{
                        width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                        background: status === "done" ? "#2D5134" : status === "in-progress" ? "#D9A441" : "var(--border)",
                      }} />
                      <span className="truncate">{farmer?.first_name} {farmer?.last_name}</span>
                    </button>
                  );
                })}
              </div>

              <div className="flex-1 min-w-0" data-testid="submission-farmer-detail">
                {(() => {
                  const m = presentMembers.find((mm) => mm.farmer_id === selectedFarmerId);
                  if (!m) return <p className="text-sm p-4" style={{ color: "var(--text-muted)" }}>Select a member to begin.</p>;
                  const farmer = m.farmer;
                  const stapIds = activityStapIds(farmer?.stap_ids || []);
                  return (
                    <div className="card p-4">
                      <div className="font-semibold mb-3">{farmer?.first_name} {farmer?.last_name}</div>
                      {stapIds.map((stapId, idx) => {
                        const opts = optionsByStap[stapId];
                        const isPrimary = stapId === farmer?.primary_stap_id;
                        const activity = getEntry(m.farmer_id, stapId);
                        return (
                          <div key={stapId} className={idx > 0 ? "border-t pt-3 mt-3" : ""} style={{ borderColor: "var(--border)" }}>
                            <div className="flex items-center gap-2 mb-2">
                              <span className="font-semibold text-sm">{opts?.primary?.product_name || "Loading activity…"}</span>
                              <span className={`badge ${isPrimary ? "badge-success" : "badge-muted"}`}>
                                {isPrimary ? "Primary Activity" : "Secondary Activity"}
                              </span>
                            </div>
                            {!opts ? (
                              <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading options…</p>
                            ) : (
                              <>
                                {opts.inputs.length > 0 && (
                                  <>
                                    <div className="label-tag mb-1">Inputs</div>
                                    <InputsTable
                                      options={opts.inputs}
                                      schemes={schemes}
                                      value={activity.inputs}
                                      onChange={(productId, field, val) => updateInput(m.farmer_id, stapId, productId, field, val)}
                                      getAutoFillQty={(producingStapId, productId) => {
                                        const stock = stockByFarmerProduct[`${m.farmer_id}:${productId}`] || 0;
                                        const cycleOutput = producingStapId
                                          ? parseFloat(getEntry(m.farmer_id, producingStapId).primaryOutput.actual || "0") || 0
                                          : 0;
                                        const total = stock + cycleOutput;
                                        return total > 0 ? total : undefined;
                                      }}
                                    />
                                  </>
                                )}

                                <div className="label-tag mt-3 mb-1">Outputs</div>
                                <OutputsTable
                                  primary={opts.primary}
                                  primaryValue={activity.primaryOutput}
                                  onPrimaryChange={(field, val) => updatePrimaryField(m.farmer_id, stapId, field, val)}
                                  byproductOptions={opts.byproducts}
                                  byproductValue={effectiveByproducts(m.farmer_id, activity.byproducts, opts.byproducts)}
                                  onByproductChange={(productId, field, val) => updateByproduct(m.farmer_id, stapId, productId, field, val)}
                                  lossReasons={lossReasons}
                                />
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="card p-4" style={{ background: "var(--bg)" }}><div className="label-tag">Meeting</div><div className="font-semibold text-lg mt-1">{meeting.meeting_title}</div><div className="text-sm">{meeting.meeting_date} · {meeting.meeting_venue}</div></div>
            <div className="card p-4" style={{ background: "var(--bg)" }}><div className="label-tag">Attendance</div><div className="font-semibold text-lg mt-1">{Object.values(attendance).filter(Boolean).length} present / {fig.members.length} total</div></div>
            <div className="card p-4" style={{ background: "var(--bg)" }}><div className="label-tag">Yield entries</div><div className="font-semibold text-lg mt-1">{flatEntries.length}</div></div>
            <div className="card p-4" style={{ background: "var(--bg)" }}><div className="label-tag">Input entries</div><div className="font-semibold text-lg mt-1">{inputEntryCount}</div></div>
            <div className="card p-4" style={{ background: "var(--bg)" }}><div className="label-tag">Byproduct entries</div><div className="font-semibold text-lg mt-1">{byproductEntryCount}</div></div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              {isCorrection
                ? "This correction will be sent to your State Admin for review — nothing changes until it's accepted."
                : "Once submitted, this monthly report becomes immutable."}
            </div>
          </div>
        )}

        <div className="flex justify-between mt-6">
          <button className="btn-secondary inline-flex items-center gap-2" onClick={prev} disabled={step === 0}><ArrowLeft size={14} weight="bold" />Back</button>
          {step < STEPS.length - 1 ? (
            <button data-testid="wizard-next" className="btn-primary inline-flex items-center gap-2" onClick={next}>Next<ArrowRight size={14} weight="bold" /></button>
          ) : (
            <button data-testid="wizard-submit" className="btn-primary inline-flex items-center gap-2" onClick={submit}>
              {isCorrection ? "Submit correction for review" : "Submit final"}<CheckCircle size={14} weight="bold" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
