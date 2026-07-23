"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DirectorateOffice } from "@/lib/types";

export default function DirectorateOfficePage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [form, setForm] = useState({ office_name: "", office_address: "", office_contact_no: "", officer_in_charge_name: "" });

  const { data } = useQuery<DirectorateOffice>({
    queryKey: ["directorate-office"],
    queryFn: async () => (await api.get("/master/directorate-office")).data,
  });

  useEffect(() => {
    if (data) {
      setForm({
        office_name: data.office_name || "",
        office_address: data.office_address || "",
        office_contact_no: data.office_contact_no || "",
        officer_in_charge_name: data.officer_in_charge_name || "",
      });
    }
  }, [data]);

  const saveMut = useMutation({
    mutationFn: (payload: typeof form) => api.patch("/master/directorate-office", payload),
    onSuccess: () => { toast.success("Directorate office updated"); qc.invalidateQueries({ queryKey: ["directorate-office"] }); },
    onError: (e: any) => toast.error(fmtErr(e.response?.data?.detail)),
  });

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6">Only State Admins can access this page.</div>;
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    saveMut.mutate(form);
  };

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Directorate Office</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          State-level office details for the Directorate of Sericulture — the top of the three-level office
          structure (Directorate → District Sericulture Office → Sericulture Circle Office).
        </p>
      </div>

      <div className="card p-5 max-w-xl">
        <form onSubmit={submit} className="grid gap-3">
          <div>
            <label className="label-tag block mb-1">Office Name *</label>
            <input required className="input w-full" value={form.office_name}
                   onChange={(e) => setForm({ ...form, office_name: e.target.value })} />
          </div>
          <div>
            <label className="label-tag block mb-1">Office Address</label>
            <input className="input w-full" value={form.office_address}
                   onChange={(e) => setForm({ ...form, office_address: e.target.value })} />
          </div>
          <div>
            <label className="label-tag block mb-1">Office Contact Number</label>
            <input className="input w-full" value={form.office_contact_no}
                   onChange={(e) => setForm({ ...form, office_contact_no: e.target.value })} />
          </div>
          <div>
            <label className="label-tag block mb-1">Officer-in-Charge</label>
            <input className="input w-full" value={form.officer_in_charge_name}
                   onChange={(e) => setForm({ ...form, officer_in_charge_name: e.target.value })} />
          </div>
          <div className="flex justify-end mt-2">
            <button type="submit" disabled={saveMut.isPending} className="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  );
}
