import { createContext, useContext } from "react";
import type { Application, Opportunity } from "../data/creatorDashboardData";
import type { Application as ApiApplication } from "../services/applications";
import type { CreatorOpportunity as ApiOpportunity } from "../services/creatorWorkspace";
import type { Submission } from "../services/submissions";

interface CreatorWorkspace {
  /** Dashboard-shaped data for the existing dashboard components. */
  opportunities: Opportunity[];
  applications: Application[];
  /** The same data as the API returns it, for pages that need every field. */
  apiOpportunities: ApiOpportunity[];
  apiApplications: ApiApplication[];
  approvedSubmissions: Submission[];
  creatorName: string;
  loading: boolean;
  error: string;
  /** Reload opportunities and applications, e.g. after a decision or a close. */
  refresh: () => Promise<void>;
}

export const CreatorWorkspaceContext = createContext<CreatorWorkspace | null>(null);

export function useCreatorWorkspace() {
  const workspace = useContext(CreatorWorkspaceContext);
  if (!workspace) {
    throw new Error("Creator pages must be rendered inside CreatorLayout.");
  }
  return workspace;
}
