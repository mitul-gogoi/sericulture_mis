"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { FigSettings } from "@/lib/types";

export default function FigSettingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [minMembers, setMinMembers] = useState(1);

  const { data } = useQuery<FigSettings>({
    queryKey: ["fig-settings"],
    queryFn: async () => (await api.get("/master/fig-settings")).data,
  });

  useEffect(() => {
    if (data) setMinMembers(data.min_members);
  }, [data]);

  const saveMut = useMutation({
    mutationFn: (payload: { min_members: number }) => api.patch("/master/fig-settings", payload),
    onSuccess: () => { toast.success("FIG settings updated"); qc.invalidateQueries({ queryKey: ["fig-settings"] }); },
    onError: (e: any) => toast.error(fmtErr(e.response?.data?.detail)),
  });

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6">Only State Admins can access this page.</div>;
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    saveMut.mutate({ min_members: minMembers });
  };

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Minimum FIG Members</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          The minimum number of farmer members a FIG must have at registration. District Admin's
          Register FIG form will not allow creating a FIG with fewer members than this.
        </p>
      </div>

      <div className="card p-5 max-w-xl">
        <form onSubmit={submit} className="grid gap-3">
          <div>
            <label className="label-tag block mb-1">Minimum FIG Members *</label>
            <input required type="number" min={1} className="input w-full" value={minMembers}
                   onChange={(e) => setMinMembers(Number(e.target.value))} />
          </div>
          <div className="flex justify-end mt-2">
            <button type="submit" disabled={saveMut.isPending} className="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  );
}
