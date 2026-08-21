"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin } from "@phosphor-icons/react";
import api, { DISTRICT_KEY } from "@/lib/api";
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
  const { user } = useAuth();
  const qc = useQueryClient();
  const ids = user?.district_ids || [];
  const multi = user?.role === "DISTRICT_ADMIN" && ids.length > 1;

  const [active, setActive] = useState<string>("");

  useEffect(() => {
    if (!multi) return;
    const saved = localStorage.getItem(DISTRICT_KEY);
    // Fall back to the primary if nothing is stored, or if a stored district was since
    // taken away — otherwise every request would 403 with no obvious cause.
    const next = saved && ids.includes(saved) ? saved : ids[0];
    localStorage.setItem(DISTRICT_KEY, next);
    setActive(next);
  }, [multi, ids.join(",")]);

  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts-for-switcher"],
    queryFn: async () => (await api.get("/master/districts")).data,
    enabled: multi,
  });

  if (!multi) return null;

  function change(id: string) {
    localStorage.setItem(DISTRICT_KEY, id);
    setActive(id);
    // Every cached list was fetched under the previous district, so none of it is valid
    // any more.
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
        value={active}
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
