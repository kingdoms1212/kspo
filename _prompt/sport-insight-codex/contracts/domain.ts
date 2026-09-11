/**
 * SPORT INSIGHT internal domain contract DRAFT.
 * These names are NOT verified source CSV headers.
 * Map raw columns only after inspecting the actual files and definitions.
 * All counts and flags require the validations in docs/02-data-contract.md.
 */
export type DataMode = "demo" | "real";
export type Availability = "available" | "partial" | "unavailable" | "unverified";
export type Nullable<T> = T | null;

export interface ReferencePeriod {
  label: string;
  startDate: Nullable<string>; // YYYY-MM-DD
  endDate: Nullable<string>;   // YYYY-MM-DD
}

export interface SourceRef {
  datasetId: string;
  snapshotId: string;
  rowKey: string;
}

export interface FieldMapping {
  rawField: string;
  domainField: string;
  unit: Nullable<string>;
  verified: boolean;
  evidenceNote: string;
}

export interface DatasetManifest {
  datasetId: string;
  snapshotId: string;
  title: string;
  sourceUrl: string;
  sourceFileName: string;
  sourceChecksum: Nullable<string>;
  portalUpdatedAt: Nullable<string>;
  referencePeriod: Nullable<ReferencePeriod>;
  collectedAt: string;
  rowCount: number;
  geoCodeSystem: Nullable<string>;
  geoBoundaryYear: Nullable<number>;
  aggregationUnit: string;
  cohortDefinition: Nullable<string>;
  licenseNote: Nullable<string>;
  status: Availability;
  fieldMappings: FieldMapping[];
}

export interface Capability {
  status: Availability;
  reason: string;
  sourceDatasetIds: string[];
}

export interface DataCapabilities {
  coverageRate: Capability;
  comparableYearOnYear: Capability;
  monthlyPerPersonFee: Capability;
  programPeriod: Capability;
  facilityCoordinates: Capability;
  transitWalkingTime: Capability;
  facilityPhotos: Capability;
}

export interface Region {
  id: string; // canonical internal key, never infer code systems by length alone
  name: string;
  level: "country" | "sido" | "sigungu";
  parentId: Nullable<string>;
  sourceCodes: Array<{ system: string; code: string; year: Nullable<number> }>;
}

export type VoucherState = "registered" | "not_registered" | "unknown";

export interface VerifiedLocation {
  latitude: number;
  longitude: number;
  crs: "EPSG:4326";
  verified: true;
  sourceRefs: SourceRef[];
}

export interface Facility {
  id: string;
  regionId: Nullable<string>;
  name: string;
  address: Nullable<string>;
  phone: Nullable<string>;
  facilityType: Nullable<string>;
  sportCodes: string[];
  voucherStatus: {
    sports: VoucherState;
    disability: VoucherState;
  };
  location: Nullable<VerifiedLocation>;
  photo: Nullable<{ url: string; attribution: string; rightsVerified: true }>;
  openingHours: Nullable<{ text: string; sourceRefs: SourceRef[] }>;
  sourceRefs: SourceRef[];
}

export interface ProgramFee {
  amountKrw: Nullable<number>;
  periodUnit: "month" | "session" | "course" | "unknown";
  chargeBasis: "per_person" | "per_group" | "unknown";
  verified: boolean;
  rawLabel: Nullable<string>;
  sourceRefs: SourceRef[];
}

export interface ProgramSchedule {
  weekdays: Nullable<Array<1 | 2 | 3 | 4 | 5 | 6 | 7>>; // Monday=1
  startTime: Nullable<string>; // HH:mm
  endTime: Nullable<string>;
  startDate: Nullable<string>;
  endDate: Nullable<string>;
}

export interface Program {
  id: string;
  facilityId: Nullable<string>;
  facilityLinkStatus: "matched" | "unmatched" | "ambiguous";
  sourceFacilityName: Nullable<string>;
  regionId: Nullable<string>;
  name: string;
  sportCode: Nullable<string>;
  targetGroups: Nullable<string[]>; // only verified source categories
  voucherType: "sports" | "disability" | "unknown";
  schedule: ProgramSchedule;
  fee: ProgramFee;
  recruitmentCapacity: Nullable<number>; // NOT live remaining seats
  sourceRefs: SourceRef[];
}

export interface UsageRecord {
  id: string;
  programId: Nullable<string>;
  facilityId: Nullable<string>;
  regionId: Nullable<string>;
  sportCode: Nullable<string>;
  voucherType: "sports" | "disability";
  period: ReferencePeriod;
  applicationCount: Nullable<number>; // NOT deduplicated unique persons
  sourceRefs: SourceRef[];
}

export interface RegionalCoverage {
  id: string;
  regionId: string;
  period: ReferencePeriod;
  cohortKey: string;
  targetCount: Nullable<number>;
  beneficiaryCount: Nullable<number>;
  population: Nullable<number>;
  eligibleFacilityCount: Nullable<number>;
  cohortAggregationApproved: boolean;
  numeratorDenominatorCompatible: boolean;
  validationNote: string;
  sourceRefs: SourceRef[];
}

export interface TransitLink {
  id: string;
  facilityId: string;
  stopName: string;
  mode: "bus" | "subway" | "unknown";
  straightDistanceMeters: Nullable<number>;
  walkingDistanceMeters: Nullable<number>;
  walkingSeconds: Nullable<number>;
  sourceRefs: SourceRef[];
}

export interface DataPackage {
  mode: DataMode;
  manifests: DatasetManifest[];
  regions: Region[];
  facilities: Facility[];
  programs: Program[];
  usage: UsageRecord[];
  coverage: RegionalCoverage[];
  transit: TransitLink[];
  capabilities: DataCapabilities;
}

export interface SnapshotSelection {
  // Multiple sources may have different reference dates; never fake one date.
  byDatasetId: Record<string, string>;
}

export interface DataProvider {
  mode: DataMode;
  load(selection: SnapshotSelection): Promise<DataPackage>;
}

export interface BudgetInput {
  totalKrw: number;       // non-negative integer
  plannedPeople: number; // positive integer
  months: number;        // positive integer
}

export type BudgetEvaluation =
  | { status: "not_requested" }
  | { status: "not_calculable"; reason: string }
  | {
      status: "calculated";
      input: BudgetInput;
      monthlyPerPersonKrw: number;
      plannedTuitionKrw: number;
      withinBudget: boolean;
      arithmeticSupportedPeople: Nullable<number>; // null for verified free fee
      note: string;
    };

export interface ProgramQuery {
  snapshots: SnapshotSelection;
  regionId: Nullable<string>;
  facilityId: Nullable<string>;
  targetGroup: Nullable<string>;
  sportCodes: string[];
  voucherType: "all" | "sports" | "disability";
  weekdays: Array<1 | 2 | 3 | 4 | 5 | 6 | 7>;
  timeWindow: Nullable<{ startTime: string; endTime: string }>;
  dateWindow: Nullable<{ startDate: string; endDate: string }>;
  budget: Nullable<BudgetInput>;
  sortBy: "program_name" | "monthly_fee" | "stop_walking_time";
}

export interface ProgramResultRow {
  program: Program;
  facility: Nullable<Facility>;
  nearestStopWalkingSeconds: Nullable<number>;
  budget: BudgetEvaluation;
  rank: number;
}

export interface ProgramSearchResult {
  appliedQuery: ProgramQuery;
  allRows: ProgramResultRow[];
  topThree: ProgramResultRow[];
  matchedFacilityIds: string[];
  excludedCounts: Record<string, number>;
  createdAt: string;
}

export interface MetricValue {
  value: Nullable<number>;
  unit: "people" | "facilities" | "programs" | "ratio" | "krw" | "seconds";
  status: Availability;
  label: string;
  reason: Nullable<string>;
  coverage: Nullable<{ observed: number; expected: number }>;
  sourceRefs: SourceRef[];
}
