export type Role = "STATE_ADMIN" | "DISTRICT_ADMIN" | "FIG_PRESIDENT" | "FARMER";

export interface User {
  id: string;
  mobile_no: string;
  role: Role;
  name?: string | null;
  district_id?: string | null;
  fig_id?: string | null;
  farmer_id?: string | null;
  is_active?: boolean;
  /** The permanent super admin. Set by the server, never inferred from the mobile
   *  number here, so there is one source of truth for who is protected. */
  is_protected?: boolean;
}

export interface OfficeFields {
  office_name?: string | null; office_address?: string | null;
  office_contact_no?: string | null; officer_in_charge_name?: string | null;
}
export interface District extends OfficeFields { id: string; district_name: string }
export interface SubdivisionCdc extends OfficeFields {
  id: string; office_type: "Sub-division Office" | "CDC"; district_id: string; is_active: boolean;
}
export interface SericultureCircle extends OfficeFields {
  id: string; circle_name: string; district_id: string; subdivision_cdc_id?: string | null;
}
export interface DirectorateOffice {
  id: string; office_name: string; office_address?: string | null;
  office_contact_no?: string | null; officer_in_charge_name?: string | null;
}
export interface Caste { id: string; caste_name: string }
export interface Religion { id: string; religion_name: string }
export interface EducationLevel { id: string; education_level_name: string }

export interface SilkType { id: string; silk_type_name: string; is_active: boolean }
export interface Activity {
  id: string; activity_name: string; silk_type_id: string;
  step_no: number; description?: string | null; is_active: boolean;
  silk_type_name?: string;
}
export interface Product {
  id: string; product_name: string; unit_of_measure: string;
  silk_type_id?: string | null; silk_type_name?: string | null;
  default_source_category_id?: string | null;
  is_perishable: boolean; is_byproduct: boolean; show_in_dashboard: boolean; is_active: boolean;
}
export type StapRole = "INPUT" | "OUTPUT";
export interface SilkTypeActivityProduct {
  id: string; silk_type_id: string; activity_id: string; product_id: string; role: StapRole;
  input_group?: string | null;
  source_type_ids?: string[]; source_type_names?: string[];
  input_source_category_id?: string | null; input_source_category_name?: string | null;
  is_active: boolean; silk_type_name: string; activity_name: string; step_no?: number;
  product_name: string; unit_of_measure: string; is_perishable: boolean; is_byproduct: boolean;
}

export interface ConversionStandard {
  id: string; silk_type_id: string; silk_type_name: string | null;
  input_product_id: string; input_product_name: string | null; input_unit_of_measure: string | null;
  output_product_id: string; output_product_name: string | null; output_unit_of_measure: string | null;
  standard_input_qty: number; output_min_qty: number; output_max_qty: number;
  min_pct: number; max_pct: number; is_active: boolean;
}

export interface Farmer {
  id: string; farmer_code: string;
  first_name: string; middle_name?: string | null; last_name: string;
  gender: string; date_of_birth?: string | null; mobile_no: string;
  // Display-only, e.g. "********1234". The real number is never sent to an admin client;
  // only the farmer's own GET /farmers/me carries it (see FarmerSelfProfile).
  aadhaar_masked?: string | null;
  pan_no?: string | null;
  photo_path?: string | null; is_pwd?: boolean;
  education_level_id?: string | null; experience_years?: number;
  caste_id?: string | null; religion_id?: string | null;
  family_member_male?: number; family_member_female?: number;
  district_id: string; seri_circle_id: string; village_name: string;
  gaon_panchayat?: string | null; development_block?: string | null; post_office?: string | null;
  pin_code?: string | null;
  stap_ids: string[]; primary_stap_id?: string | null;
  experience_activity_ids?: string[];
  farmer_type?: string | null;
  account_number?: string | null; bank_name?: string | null;
  branch_name?: string | null; ifsc_code?: string | null; passbook_path?: string | null;
  is_active: boolean;
  fig_id?: string | null; fig_name?: string | null;
}

/** GET /farmers/me only — a farmer viewing their own record. This is the sole response
 *  in the app that carries the real 12-digit Aadhaar, plus resolved display names so the
 *  My Profile page never renders raw UUIDs. Kept separate from `Farmer` so nothing can
 *  assume `aadhaar_full` exists on an ordinary list row. */
export interface FarmerSelfProfile extends Farmer {
  aadhaar_full?: string | null;
  fig_code?: string | null;
  district_name?: string | null;
  circle_name?: string | null;
  caste_name?: string | null;
  religion_name?: string | null;
  education_level_name?: string | null;
}

export interface AssetDetail { asset_type_id: string; quantity: number; acquisition_year?: number | null }

export interface Fig {
  id: string; fig_code: string; fig_name: string;
  stap_id: string; district_id: string; seri_circle_id: string;
  formation_date: string; meeting_venue?: string | null;
  village_name?: string | null; panchayat_name?: string | null;
  post_office?: string | null; pin_code?: string | null;
  address?: string | null; contact_no?: string | null; remarks?: string | null;
  minutes_path?: string | null; group_photo_path?: string | null;
  total_members: number; member_names?: string[]; is_active: boolean;
}

export interface FigMember { id: string; fig_id: string; farmer_id: string; role: string; is_active: boolean; farmer?: Farmer | null }
export interface FigDetail extends Fig { members: FigMember[] }
export interface FigSettings { id: string; min_members: number; updated_at: string }

export interface Meeting {
  id: string; fig_id: string; meeting_title: string; meeting_date: string;
  meeting_venue: string; meeting_month: string; submitted_at: string;
  minutes_path?: string | null;
}

export interface MeetingDetailOutput {
  product_name: string; planned_yield: number; actual_yield: number; next_month_plan: number;
  stock_balance: number; sold_quantity: number; sold_rate: number; earning: number;
  loss_reason_id?: string | null; loss_reason_name?: string | null;
}
export interface MeetingDetailByproduct {
  product_id: string; product_name: string; quantity: number; planned_quantity: number; next_month_plan: number;
  stock_balance: number; sold_quantity: number; sold_rate: number; earning: number;
  loss_reason_id?: string | null; loss_reason_name?: string | null;
}
export interface MeetingDetailInput {
  product_id: string; product_name: string; quantity: number; unit_of_measure: string;
  source_type_id?: string | null; source_type_name?: string | null;
  scheme_id?: string | null; scheme_name?: string | null;
}
export interface MeetingDetailEntry {
  farmer_id: string; farmer_name: string; stap_id: string; activity_name: string;
  is_primary_stage: boolean; output: MeetingDetailOutput;
  byproducts: MeetingDetailByproduct[]; inputs: MeetingDetailInput[];
}
export interface MeetingDetailAttendance { farmer_id: string; farmer_name: string; mobile: string; is_present: boolean }
export interface MeetingDetail {
  meeting: {
    id: string; fig_id: string; fig_name: string; meeting_title: string; meeting_date: string;
    meeting_time?: string | null; meeting_venue: string; meeting_details?: string | null;
    minutes_path?: string | null; next_meeting_date?: string | null; meeting_month: string;
    submitted_at: string;
  };
  attendance: MeetingDetailAttendance[];
  entries: MeetingDetailEntry[];
}

export interface MeetingCorrection {
  id: string; meeting_id: string; fig_id: string; submitted_by_user_id: string; submitted_at: string;
  status: "PENDING" | "ACCEPTED" | "REJECTED";
  reviewed_by_user_id?: string | null; reviewed_at?: string | null; rejection_reason?: string | null;
}

export interface FarmerSubmission {
  id: string; farmer_id: string; submission_code: string; submission_month: string;
  submitted_at: string; created_at: string;
}
export interface FarmerSubmissionDetailEntry {
  stap_id: string; activity_name: string; is_primary_stage: boolean;
  output: MeetingDetailOutput; byproducts: MeetingDetailByproduct[]; inputs: MeetingDetailInput[];
}
export interface FarmerSubmissionDetail {
  submission: {
    id: string; submission_code: string; submission_month: string; submitted_at: string;
    farmer_id: string; farmer_name: string; farmer_code?: string | null;
  };
  entries: FarmerSubmissionDetailEntry[];
}
export interface FarmerSubmissionCorrection {
  id: string; farmer_submission_id: string; farmer_id: string; submitted_by_user_id: string; submitted_at: string;
  status: "PENDING" | "ACCEPTED" | "REJECTED";
  reviewed_by_user_id?: string | null; reviewed_at?: string | null; rejection_reason?: string | null;
}
export interface FarmerSubmissionListRow {
  submission_id: string; submission_code: string; farmer_id: string; farmer_name: string;
  farmer_code?: string | null; district_name: string | null; month: string; submitted_on: string;
}
export interface PendingFarmerCorrectionRow {
  correction_id: string; farmer_submission_id: string; farmer_name: string;
  farmer_code?: string | null; district_name: string | null; month: string | null; submitted_on: string;
}

export interface SubmissionStatusRow {
  fig_id: string; fig_name: string; district_name: string | null;
  status: "Submitted" | "Pending"; submitted_on: string | null; meeting_id: string | null;
}
export interface FpSubmissionHistoryRow {
  meeting_id: string; month: string; meeting_title: string; submitted_on: string;
  venue: string; re_submitted: "Yes" | "No"; minutes_path: string | null;
}
export interface PendingCorrectionRow {
  correction_id: string; meeting_id: string; fig_name: string | null;
  district_name: string | null; month: string | null; submitted_on: string;
}

export interface InputSourceCategory { id: string; category_name: string; is_active: boolean }

export interface InputSourceType {
  id: string; source_name: string; category_id: string; category_name?: string | null;
  requires_scheme: boolean; is_own_source: boolean; is_active: boolean;
}

export interface StapOption { product_id: string; product_name: string; unit_of_measure: string }
export interface StapInputOption extends StapOption {
  input_group?: string | null;
  is_chain_internal: boolean;
  producing_stap_id?: string | null;
  allowed_source_types: InputSourceType[];
}
export interface StapOptions {
  primary: StapOption | null;
  byproducts: StapOption[];
  inputs: StapInputOption[];
}

export interface Yield {
  id: string; fig_id: string; farmer_id: string; stap_id: string;
  activity_id?: string | null; product_id?: string | null;
  yield_month: string; is_primary_stage: boolean;
  planned_yield: number; actual_yield: number; next_month_plan: number; stock_balance: number;
  sold_quantity: number; sold_rate: number; earning: number;
  loss_reason_id?: string | null;
}

export interface ByproductEntry {
  id: string; parent_yield_id: string; farmer_id: string; fig_id: string; product_id: string;
  yield_month: string; unit_of_measure: string; quantity: number;
  planned_quantity: number; next_month_plan: number; stock_balance: number;
  sold_quantity: number; sold_rate: number; earning: number;
  loss_reason_id?: string | null; remarks?: string | null;
}

export interface LossReason { id: string; reason_name: string; is_active: boolean }

export interface Stock {
  id: string; farmer_id: string; fig_id: string; product_id: string;
  opening_balance: number; closing_balance: number; is_perishable: boolean;
  last_produced_month?: string | null; last_entry_at: string; age_days?: number | null;
}

export type YieldMatrixLevel = "state" | "district" | "sericulture_circle" | "fig" | "farmer" | "meeting";

export interface YieldMatrixProduct { id: string; product_name: string; unit_of_measure: string }
export interface YieldMatrixInputProduct extends YieldMatrixProduct { sources: string[] }
export interface YieldMatrixInputCell { total: number; by_source: Record<string, number> }
export interface YieldMatrixExpectedRange {
  standard_id: string; input_product_id: string; input_product_name: string;
  min_pct: number; max_pct: number;
}
export interface YieldMatrixOutputProduct extends YieldMatrixProduct {
  expected_ranges: YieldMatrixExpectedRange[];
}
export interface YieldMatrixExpectedValue { min: number; max: number; input_qty: number }
export interface YieldMatrixOutputCell {
  planned: number; actual: number;
  expected_ranges: Record<string, YieldMatrixExpectedValue | null>;
  next_month_plan: number; sold_quantity: number; earning: number;
  sold_rate: number | null; loss_reason_name: string | null;
}
export interface YieldMatrixItem {
  id: string; name: string;
  district_name?: string | null; seri_circle_name?: string | null; fig_name?: string | null;
  fig_code?: string | null; farmer_code?: string | null;
  // "meeting" level only — the raw-record identity/context fields.
  meeting_id?: string | null; meeting_month?: string | null;
  meeting_title?: string | null; meeting_date?: string | null;
  meeting_venue?: string | null; farmer_mobile?: string | null;
  input: Record<string, YieldMatrixInputCell>;
  output: Record<string, YieldMatrixOutputCell>;
  stock: Record<string, number>;
}
export interface YieldMatrixResponse {
  level: YieldMatrixLevel; months: string[];
  input_products: YieldMatrixInputProduct[];
  output_products: YieldMatrixOutputProduct[];
  stock_products: YieldMatrixProduct[];
  available_products: { input: string[]; output: string[]; stock: string[] };
  items: YieldMatrixItem[];
  page: number; page_size: number; total: number;
}

export interface Land {
  id: string; farmer_id: string; dag_no?: string | null; patta_no?: string | null;
  land_type: string; land_area_sqm?: number | null; land_area_bigha?: number | null;
  land_area_hectare?: number | null; gps_verified: string;
  gps_points?: { latitude: number; longitude: number }[] | null;
  overlap_detected: boolean; overlapping_parcel_ids: string[];
  failure_reason?: string | null; farmer?: Partial<Farmer>;
  // Flat fields populated by the paginated GET /lands (page param) and the lands export —
  // the legacy nested `farmer` above is only populated by the unpaginated fallback shape.
  farmer_code?: string | null; farmer_name?: string | null;
  village_name?: string | null; gaon_panchayat?: string | null; development_block?: string | null;
  district_name?: string | null; circle_name?: string | null;
  // Present for FIG_PRESIDENT/DISTRICT_ADMIN/STATE_ADMIN callers only — true when a FIG-member
  // farmer has self-captured GPS for this parcel, staged as a private draft awaiting the FIG
  // President to review/submit (see GET /lands/{id}/gps/draft).
  has_gps_draft?: boolean;
}

export interface LandGpsDraft {
  points: { latitude: number; longitude: number }[]; updated_at: string; farmer_id: string;
}

export interface LandsPage {
  items: Land[]; total: number; pending_count: number; overlap_count: number;
}

export const LAND_TYPES = ["Owned", "Leased", "Community", "Government", "Forest"] as const;
export const MIN_GPS_POINTS = 5;

export type AssetCategory = "STRUCTURE" | "SHARED_INFRASTRUCTURE" | "EQUIPMENT";
export type AssetOwnershipLevel = "INDIVIDUAL" | "FIG" | "EITHER";
export const ASSET_CATEGORIES: AssetCategory[] = ["STRUCTURE", "SHARED_INFRASTRUCTURE", "EQUIPMENT"];

export interface AssetType {
  id: string; name: string; category: AssetCategory; silk_types: string[];
  ownership_level: AssetOwnershipLevel; useful_life_years: number;
  typically_scheme_funded: boolean; is_active: boolean;
}

export type AssetOwnerType = "FARMER" | "FIG";
export type AssetAcquisitionMode =
  | "SCHEME_DISBURSEMENT" | "SELF_PROCURED" | "SELF_DECLARED_AT_REGISTRATION" | "LEGACY_SELF_DECLARED";
export type AssetStatus = "FUNCTIONAL" | "NON_FUNCTIONAL" | "UNDER_REPAIR" | "DECOMMISSIONED";
export type AssetVerificationStatus = "UNVERIFIED" | "CIRCLE_VERIFIED" | "DISPUTED";
export type AssetConfidence =
  "FARMER_SELF_DECLARED" | "CIRCLE_OFFICER_RECOLLECTION" | "DOCUMENTARY_EVIDENCE_SEEN";

export type AssetGpsStatus = "Not Submitted" | "Pending" | "Verified" | "Failed";

export interface AssetInstance {
  id: string; asset_type_id: string; asset_type_name?: string | null;
  category?: AssetCategory | null; ownership_level?: AssetOwnershipLevel | null;
  useful_life_years?: number | null;
  owner_type: AssetOwnerType; owner_id: string; owner_name?: string | null;
  quantity: number; acquisition_date?: string | null; acquisition_mode: AssetAcquisitionMode;
  scheme_id?: string | null; beneficiary_id?: string | null;
  status: AssetStatus; verification_status: AssetVerificationStatus;
  confidence?: AssetConfidence | null; photo_path?: string | null; remarks?: string | null;
  last_verified_by?: string | null; last_verified_by_name?: string | null;
  last_verified_at?: string | null; created_at: string;
  // Flat fields populated by the paginated GET /assets (page param) and the assets export —
  // asset_code/gps_status/latitude/longitude are also present on the legacy unpaginated shape.
  asset_code: string; owner_code?: string | null;
  district_name?: string | null; circle_name?: string | null; scheme_name?: string | null;
  age_left_days?: number | null;
  latitude?: number | null; longitude?: number | null;
  gps_status: AssetGpsStatus; gps_failure_reason?: string | null;
  // Present for FIG_PRESIDENT/DISTRICT_ADMIN/STATE_ADMIN callers only — true when a FIG-member
  // farmer has self-captured GPS for this asset, staged as a private draft awaiting the FIG
  // President to review/submit (see GET /assets/{id}/gps/draft).
  has_gps_draft?: boolean;
}

export interface AssetsPage {
  items: AssetInstance[]; total: number;
}

export interface AssetGpsDraft {
  latitude: number; longitude: number; updated_at: string; farmer_id: string;
}

export type AssetVerifyResult = "CONFIRMED_PRESENT" | "NOT_FOUND" | "PARTIALLY_FUNCTIONAL";
export interface AssetVerificationLog {
  id: string; result: AssetVerifyResult; photo_url?: string | null; remarks?: string | null;
  checked_at: string; checked_by?: string | null;
}
export interface AssetCooldownCheck {
  eligible: boolean; last_acquired?: string | null; cooldown_until?: string | null;
  reason?: string | null; asset_type_name?: string | null;
}

export type SchemeBeneficiaryKind = "FARMER" | "FIG";
export interface Scheme {
  id: string; scheme_name: string; description?: string | null; silk_type_id?: string | null;
  activity_ids: string[]; eligible_farmer_type?: string; total_budget_rs: number;
  disbursement_type: string; support_type: string; is_active?: boolean;
  start_date?: string | null; end_date?: string | null;
  beneficiary_kind: SchemeBeneficiaryKind;
  target_all_districts: boolean; target_district_ids: string[];
  target_silk_type_ids: string[]; target_genders: string[]; target_farmer_types: string[];
  target_caste_ids: string[]; target_religion_ids: string[]; target_education_level_ids: string[];
  target_pwd_only: boolean;
  grants_asset_type_id?: string | null;
  is_archived: boolean; archived_at?: string | null; notified_at?: string | null;
}

export type BeneficiaryStatus = "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
export interface Beneficiary {
  id: string; scheme_id: string; beneficiary_type: SchemeBeneficiaryKind;
  farmer_id?: string | null; fig_id?: string | null;
  benefit_amount: number; benefit_material?: string | null; disbursement_date?: string | null;
  cooldown_override_reason?: string | null;
  status: BeneficiaryStatus; created_by_user_id?: string | null;
  approved_by_user_id?: string | null; approved_at?: string | null; rejection_reason?: string | null;
  farmer?: Partial<Farmer>; fig?: Partial<Fig>;
}

export interface SchemeCandidate {
  id: string; name: string; already_beneficiary: boolean;
  cooldown?: AssetCooldownCheck | null;
  // Farmer-only
  farmer_code?: string; gender?: string; farmer_type?: string | null;
  // FIG-only
  fig_code?: string; total_members?: number;
}
export interface SchemeCandidatesResponse { beneficiary_kind: SchemeBeneficiaryKind; candidates: SchemeCandidate[] }
export interface Training {
  id: string; topic: string; description?: string | null;
  proposed_from_date: string; proposed_to_date: string;
  proposed_venue: string; status: string;
  scheme_id?: string | null;
}

export interface TrainingRosterEntry {
  beneficiary_id: string; name: string; code: string; beneficiary_type: SchemeBeneficiaryKind;
  is_present: boolean;
}
export interface TrainingCertificate {
  id: string; certificate_number: string; beneficiary_name: string;
  issued_at: string; pdf_path?: string | null;
  revoked: boolean; revoked_at?: string | null; revoked_reason?: string | null;
}
export interface ThreadListItem {
  thread_id: string; notification_code: string; title: string; other_party_name: string | null;
  latest_details_snippet: string; latest_sent_at: string; latest_sent_by_role: string;
  latest_reply_seq: number; is_read: boolean;
}
export interface ThreadMessage {
  id: string; notification_code: string; reply_seq: number; title: string; details: string;
  sent_at: string; sent_by_user_id: string; sent_by_name: string | null; sent_by_role: string;
  attachment_path?: string | null; in_reply_to_id?: string | null; recipient_names: string[];
}
export interface ThreadDetail {
  ancestor: ThreadMessage | null;
  messages: ThreadMessage[];
}
export interface PaginatedThreads { items: ThreadListItem[]; total: number }
export interface NotificationRecipientRow {
  id: string; recipient_user_id: string; is_read: boolean; read_at: string | null;
  user_name: string | null; user_mobile: string | null;
}
export interface NotificationCandidate {
  id: string; name: string | null; mobile_no: string;
  district_id: string | null; district_name: string | null;
  fig_id: string | null; fig_name: string | null;
}

export type AnalyticsLevel = "district" | "sericulture_circle" | "fig" | "farmer";
export interface AnalyticsCountRow { id: string; name: string; count: number }
/** FIGs drill-down — `count` at district/sericulture_circle levels, the rest only at the terminal FIG level. */
export interface AnalyticsFigRow {
  id: string; name: string; count?: number;
  fig_code?: string; silk_type_name?: string; member_count?: number; formation_date?: string;
}
export interface AnalyticsLandRow { id: string; name: string; parcels: number; bigha: number; hectare: number; verified: number; pending: number }
export interface AnalyticsYieldRow { id: string; name: string; planned: number; actual: number; stock: number; earning: number; farmer_count?: number }
/** Production — time-bound, no stock field (stock is reported separately, see AnalyticsStockRow). */
export interface AnalyticsProductionRow { id: string; name: string; planned: number; actual: number; earning: number; farmer_count?: number }
/** Current stock — point-in-time, no planned/actual/earning fields. */
export interface AnalyticsStockRow { id: string; name: string; stock: number; farmer_count?: number }
/** Input consumption — time-bound like production, broken down by source_type. */
export interface AnalyticsInputRow {
  id: string; name: string; total_qty: number; farmer_count?: number;
  by_source: Record<string, number>;
}
export interface AnalyticsResponse<T> {
  level: AnalyticsLevel;
  rows: T[];
  product?: { id: string; product_name: string; unit_of_measure: string };
  months?: string[];
}

export interface ProductMonthlyTrendResponse {
  months: string[]; metric: "output" | "input";
  data: { month: string; value: number }[];
}

export interface DashboardStats {
  farmers?: number; figs?: number; districts?: number;
  lands_pending?: number; assets_gps_pending?: number; pending_trainings?: number;
  members?: number; meetings?: number;
  lands_needing_gps?: number; assets_needing_gps?: number;
  submitted_this_month?: boolean; current_month?: string;
  fig_name?: string | null; fig_code?: string | null; district_name?: string | null;
}

export interface ActivityOnboardingItem {
  activity_id: string; silk_type_name: string; activity_name: string; step_no: number; farmers: number;
}
export interface ActivityOnboardingResponse {
  items: ActivityOnboardingItem[];
  /** Headcount. Lower than the sum of `farmers` whenever anyone does more than one activity. */
  distinct_farmers: number;
}
