// Shapes used by the creator dashboard components. The data now comes from the API
// (see services/creatorWorkspace.ts and CreatorLayout); the preview records that used
// to live here were removed.

export type ApplicantStatus = "Under Review" | "Selected" | "Rejected" | "Withdrawn";
export type OpportunityStatus = "Open" | "In Progress" | "Draft" | "Completed" | "Cancelled";

export interface Opportunity {
  id: number;
  title: string;
  description: string;
  applications: number;
  status: OpportunityStatus;
  category: "digital" | "community" | "creative";
  location: string;
  deadline: string;
  expectedHours: number;
  compensation: string;
}

export interface Application {
  id: number;
  name: string;
  initials: string;
  email: string;
  opportunityId: number;
  appliedDate: string;
  status: ApplicantStatus;
  bio: string;
  skills: string[];
}
