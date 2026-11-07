const statusClasses: Record<string, string> = {
  "Under Review": "is-review",
  Selected: "is-selected",
  Rejected: "is-rejected",
  Open: "is-open",
  "In Progress": "is-progress",
  Draft: "is-draft",
  Completed: "is-completed",
};

export default function Status({ children }: { children: string }) {
  return (
    <span className={`creator-status ${statusClasses[children] || ""}`}>
      {children}
    </span>
  );
}
