import { createContext, useContext } from "react";
import type { Application, Opportunity } from "../data/creatorDashboardData";

interface CreatorWorkspace {
  opportunities: Opportunity[];
  applications: Application[];
}

export const CreatorWorkspaceContext = createContext<CreatorWorkspace | null>(null);

export function useCreatorWorkspace() {
  const workspace = useContext(CreatorWorkspaceContext);
  if (!workspace) {
    throw new Error("Creator pages must be rendered inside CreatorLayout.");
  }
  return workspace;
}
