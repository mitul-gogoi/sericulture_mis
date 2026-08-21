"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { ViewField } from "@/components/ViewField";
import type { FarmerSelfProfile } from "@/lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5 mb-4">
      <h2 className="font-heading text-lg font-bold mb-4">{title}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{children}</div>
    </div>
  );
}

export default function FarmerProfilePage() {
  const { data: f, isLoading, isError } = useQuery<FarmerSelfProfile>({
    queryKey: ["farmer-me-profile"],
    queryFn: async () => (await api.get("/farmers/me")).data,
  });

  if (isLoading) return <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>Loading your profile…</div>;
  if (isError || !f) return <div className="card p-6 text-sm" style={{ color: "var(--error)" }}>Could not load your profile.</div>;

  const fullName = [f.first_name, f.middle_name, f.last_name].filter(Boolean).join(" ");

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">My profile</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Your registered details. Contact your District Admin if anything here is incorrect.
        </p>
      </div>

      <Section title="Identity">
        <ViewField label="Farmer code" value={<span className="font-mono text-xs">{f.farmer_code}</span>} />
        <ViewField label="Full name" value={fullName} />
        <ViewField label="Gender" value={f.gender} />
        <ViewField label="Date of birth" value={f.date_of_birth ? f.date_of_birth.slice(0, 10) : null} />
        <ViewField label="Mobile" value={f.mobile_no} />
        <div>
          <label className="label-tag">Aadhaar</label>
          <div className="mt-1 text-sm font-mono">{f.aadhaar_full ?? "—"}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Visible only on your own login. Everyone else — including your District Admin — sees
            {" "}{f.aadhaar_masked ?? "a masked value"}.
          </div>
        </div>
        <ViewField label="PAN number" value={f.pan_no} />
      </Section>

      <Section title="Location">
        <ViewField label="Village" value={f.village_name} />
        <ViewField label="Gaon panchayat" value={f.gaon_panchayat} />
        <ViewField label="Development block" value={f.development_block} />
        <ViewField label="Post office" value={f.post_office} />
        <ViewField label="PIN code" value={f.pin_code} />
        <ViewField label="Sericulture circle" value={f.circle_name} />
        <ViewField label="District" value={f.district_name} />
      </Section>

      <Section title="Farming">
        <ViewField label="FIG" value={f.fig_name ?? "Not in a FIG (solo farmer)"} />
        <ViewField label="FIG code" value={f.fig_code ? <span className="font-mono text-xs">{f.fig_code}</span> : null} />
        <ViewField label="Farmer type" value={f.farmer_type} />
        <ViewField label="Experience (years)" value={f.experience_years} />
        <ViewField label="Education" value={f.education_level_name} />
        <ViewField label="Caste" value={f.caste_name} />
        <ViewField label="Religion" value={f.religion_name} />
        <ViewField label="Family members (male)" value={f.family_member_male} />
        <ViewField label="Family members (female)" value={f.family_member_female} />
      </Section>

      <Section title="Bank details">
        <ViewField label="Account number" value={f.account_number} />
        <ViewField label="Bank" value={f.bank_name} />
        <ViewField label="Branch" value={f.branch_name} />
        <ViewField label="IFSC code" value={f.ifsc_code} />
      </Section>
    </div>
  );
}
