import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Ban, Flag, RefreshCw, ShieldAlert, X } from "lucide-react";

import { ADMIN_MESSAGES, getReportQueue, reviewReport } from "../../services/admin";
import type { AdminReport } from "../../services/admin";
import { reasonLabel } from "../../services/reports";
import type { ReportStatus } from "../../services/reports";
import { errorMessage } from "../../services/formErrors";
import "./AdminPages.css";

type Tab = ReportStatus | "all";

const TABS: { value: Tab; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "upheld", label: "Taken down" },
  { value: "dismissed", label: "Dismissed" },
  { value: "all", label: "All" },
];

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

type Group = { opportunityId: number; title: string; status: string; open: number; reports: AdminReport[] };

/** Dismiss one report, or take the whole opportunity down. */
function ReportActions({
  report,
  onDone,
}: {
  report: AdminReport;
  onDone: (message: string) => void;
}) {
  const [mode, setMode] = useState<"dismiss" | "takedown" | null>(null);
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [onlyDismiss, setOnlyDismiss] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (mode === "takedown" && !reason.trim()) {
      setError(ADMIN_MESSAGES.TAKEDOWN_REASON_REQUIRED);
      return;
    }
    if (reason.trim().length > 500) {
      setError("Keep the reason under 500 characters.");
      return;
    }
    if (mode === "takedown" && !confirming) {
      setConfirming(true);
      return;
    }

    setSaving(true);
    try {
      await reviewReport(report.report_id, mode === "takedown" ? "upheld" : "dismissed", reason);
      onDone(
        mode === "takedown"
          ? `“${report.opportunity.title}” was taken down. Its applicants, the organization and the reporters have been told.`
          : `The report from ${report.reporter.full_name} was dismissed.`
      );
    } catch (err) {
      const code = (err as { code?: string }).code;
      if (code === "REPORT_ALREADY_REVIEWED") {
        onDone(ADMIN_MESSAGES.REPORT_ALREADY_REVIEWED);
        return;
      }
      if (code === "WORK_ALREADY_SUBMITTED") {
        setOnlyDismiss(true);
        setMode(null);
      }
      setConfirming(false);
      setError(errorMessage(err, "The decision could not be saved.", ADMIN_MESSAGES));
    } finally {
      setSaving(false);
    }
  }

  if (report.status !== "pending") {
    return null;
  }

  return (
    <div className="adm-report-actions">
      {mode === null ? (
        <div className="adm-actions">
          <button type="button" className="adm-button" onClick={() => setMode("dismiss")}>
            <X size={15} /> Dismiss
          </button>
          {!onlyDismiss && report.opportunity.status !== "cancelled" && (
            <button type="button" className="adm-button is-danger-outline" onClick={() => setMode("takedown")}>
              <Ban size={15} /> Take down opportunity
            </button>
          )}
        </div>
      ) : (
        <form className="adm-form" onSubmit={(event) => void submit(event)}>
          <label>
            <span>
              {mode === "takedown"
                ? "Reason for taking it down (required, the organization sees it)"
                : "Note to the reporter (optional)"}
            </span>
            <textarea
              rows={2}
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                setConfirming(false);
              }}
              disabled={saving}
            />
          </label>

          {mode === "takedown" && confirming && (
            <p className="adm-warning" role="alert">
              <ShieldAlert size={15} /> This cancels “{report.opportunity.title}”, notifies its
              applicants and the organization, and upholds every pending report on it. It can't be
              undone.
            </p>
          )}

          <div className="adm-actions">
            <button
              type="button"
              className="adm-button"
              onClick={() => {
                setMode(null);
                setConfirming(false);
                setError("");
              }}
              disabled={saving}
            >
              Cancel
            </button>
            <button type="submit" className={`adm-button ${mode === "takedown" ? "is-danger" : "is-primary"}`} disabled={saving}>
              {saving
                ? "Saving..."
                : mode === "dismiss"
                  ? "Dismiss report"
                  : confirming
                    ? "Yes, take it down"
                    : "Take down"}
            </button>
          </div>
        </form>
      )}
      {error && (
        <p className="adm-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

/** /admin/reports: reported opportunities, most-reported first (ADR 0016). */
export default function AdminReports() {
  const [tab, setTab] = useState<Tab>("pending");
  const [items, setItems] = useState<AdminReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await getReportQueue({ status: tab === "all" ? undefined : [tab], limit: 100 });
      setItems(result.items);
    } catch (err) {
      setError(errorMessage(err, "Reports could not be loaded.", ADMIN_MESSAGES));
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    void load();
  }, [load]);

  // The API already sorts most-reported first; keep that order while grouping.
  const groups = useMemo(() => {
    const result: Group[] = [];
    items.forEach((report) => {
      let group = result.find((item) => item.opportunityId === report.opportunity.opportunity_id);
      if (!group) {
        group = {
          opportunityId: report.opportunity.opportunity_id,
          title: report.opportunity.title,
          status: report.opportunity.status,
          open: report.open_reports_on_opportunity,
          reports: [],
        };
        result.push(group);
      }
      group.reports.push(report);
    });
    return result;
  }, [items]);

  return (
    <section className="adm-page">
      <header className="adm-head">
        <div>
          <span className="adm-eyebrow">ADMIN</span>
          <h1>Reported opportunities</h1>
          <p>
            Contributors report opportunities that look misleading, unsafe, discriminatory or
            fake. The organization never learns who reported.
          </p>
        </div>
        <button type="button" className="adm-button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={15} className={loading ? "adm-spin" : ""} /> Refresh
        </button>
      </header>

      <div className="adm-tabs" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={tab === item.value}
            className={tab === item.value ? "is-active" : ""}
            onClick={() => setTab(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {notice && (
        <p className="adm-notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="adm-error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="adm-muted">Loading...</p>
      ) : groups.length === 0 ? (
        <div className="adm-empty">
          <Flag size={28} />
          <h2>{tab === "pending" ? "No open reports" : "Nothing here"}</h2>
          <p>{tab === "pending" ? "Nobody has reported an opportunity that's waiting for review." : "Try another filter."}</p>
        </div>
      ) : (
        <div className="adm-list">
          {groups.map((group) => (
            <article key={group.opportunityId} className="adm-card adm-report-group">
              <div className="adm-fb-head">
                <div>
                  <h2>{group.title}</h2>
                  <p className="adm-muted">
                    Opportunity #{group.opportunityId} · published by {group.reports[0]?.creator.full_name ?? "Unknown creator"} · currently {group.status}
                  </p>
                </div>
                {group.open > 0 && (
                  <span className="adm-pill is-flag">
                    <Flag size={13} /> {group.open} open {group.open === 1 ? "report" : "reports"}
                  </span>
                )}
              </div>

              {group.reports.map((report) => (
                <div key={`${report.report_id}-${report.status}`} className="adm-report">
                  <div className="adm-fb-head">
                    <div>
                      <strong>{reasonLabel(report.reason)}</strong>
                      <p className="adm-muted">
                        Reported by {report.reporter.full_name} · {formatDate(report.created_at)}
                      </p>
                    </div>
                    <span className={`adm-pill is-${report.status}`}>
                      {report.status === "upheld" ? "taken down" : report.status}
                    </span>
                  </div>
                  {report.details && <p className="adm-report-details">“{report.details}”</p>}
                  {report.review && (
                    <p className="adm-muted">
                      Decided {formatDate(report.review.reviewed_at)}
                      {report.review.reason ? `: “${report.review.reason}”` : ""}
                    </p>
                  )}
                  <ReportActions
                    report={report}
                    onDone={(message) => {
                      setNotice(message);
                      void load();
                    }}
                  />
                </div>
              ))}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
