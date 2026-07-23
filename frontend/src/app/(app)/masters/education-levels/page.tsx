"use client";
import { MasterCrud } from "@/components/MasterCrud";

interface EducationLevel { id: string; education_level_name: string; is_active: boolean }

export default function EducationLevelsPage() {
  return (
    <MasterCrud<EducationLevel>
      title="Education Level"
      description="Education level values used for farmer profile fields."
      endpoint="education-levels"
      queryKey="master-education-levels"
      searchOn={["education_level_name"]}
      addLabel="Add Education Level"
      columns={[{ key: "education_level_name", label: "Education Level", render: (r) => <span className="font-semibold">{r.education_level_name}</span> }]}
      fields={[{ name: "education_level_name", label: "Education Level Name", type: "text", required: true, placeholder: "e.g. Graduate" }]}
      emptyForm={{ education_level_name: "" }}
      toForm={(r) => ({ education_level_name: r.education_level_name })}
      buildPayload={(f) => ({ education_level_name: f.education_level_name })}
    />
  );
}
