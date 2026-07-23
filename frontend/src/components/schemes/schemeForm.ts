import type { SchemeBeneficiaryKind } from "@/lib/types";

export interface SchemeFormState {
  scheme_name: string;
  description: string;
  silk_type_id: string;
  activity_ids: string[];
  total_budget_rs: number;
  disbursement_type: string;
  support_type: string;
  eligible_farmer_type: string;
  beneficiary_kind: SchemeBeneficiaryKind;
  target_all_districts: boolean;
  target_district_ids: string[];
  target_silk_type_ids: string[];
  target_genders: string[];
  target_farmer_types: string[];
  target_caste_ids: string[];
  target_religion_ids: string[];
  target_education_level_ids: string[];
  target_pwd_only: boolean;
  grants_asset_type_id: string;
}

export const EMPTY_SCHEME_FORM: SchemeFormState = {
  scheme_name: "", description: "", silk_type_id: "", activity_ids: [],
  total_budget_rs: 0, disbursement_type: "DBT", support_type: "Cash", eligible_farmer_type: "All",
  beneficiary_kind: "FARMER", target_all_districts: true, target_district_ids: [],
  target_silk_type_ids: [], target_genders: [], target_farmer_types: [],
  target_caste_ids: [], target_religion_ids: [], target_education_level_ids: [], target_pwd_only: false,
  grants_asset_type_id: "",
};

export function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((x) => x !== value) : [...list, value];
}
