"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin } from "@phosphor-icons/react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { District } from "@/lib/types";

/**
 * Lets a District Admin who holds additional charge of several districts choose which one
 * they are acting as. Renders nothing at all for anyone with a single district, so the
 * common case is completely unchanged.
 *
 * The chosen district is stored in localStorage and attached to every request by the axios
 * interceptor. The server re-validates it against the admin's real assignments on each
 * call, so this control is a convenience, not the security boundary.
 */
export function DistrictSwitcher() {
  const { user, activeDistrictId, setActiveDistrict } = useAuth();
  const qc = useQueryClient();
  const ids = user?.district_ids || [];
  const multi = user?.role === "DISTRICT_ADMIN" && ids.length > 1;

  // Choosing and validating the active district lives in AuthProvider, not here: this
  // component does not render for a single-district officer, and if the correction lived
  // here a stale district would survive being relieved of additional charge and lock them
  // out of every page.

  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts-for-switcher"],
    queryFn: async () => (await api.get("/master/districts")).data,
    enabled: multi,
  });

  if (!multi) return null;

  function change(id: string) {
    setActiveDistrict(id);
    // activeDistrictId is part of every district-scoped query key, so those refetch on
    // their own. This sweeps up anything not keyed on it.
    qc.invalidateQueries();
  }

  const name = (id: string) =>
    districts.find((d) => d.id === id)?.district_name || "…";

  return (
    <div className="px-2 py-2 mb-2 rounded-lg" style={{ background: "rgba(45,81,52,0.06)" }}>
      <div className="text-xs label-tag flex items-center gap-1">
        <MapPin size={12} weight="bold" /> Acting as district
      </div>
      <select
        className="input mt-1 text-sm"
        value={activeDistrictId || ""}
        data-testid="district-switcher"
        onChange={(e) => change(e.target.value)}
      >
        {ids.map((id) => (
          <option key={id} value={id}>
            {name(id)}
            {id === ids[0] ? " (primary)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
