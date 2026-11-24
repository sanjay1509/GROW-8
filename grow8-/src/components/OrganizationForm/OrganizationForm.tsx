import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useLocation } from "react-router-dom";
import { Building2, ExternalLink, MapPin, Pencil, Save } from "lucide-react";

import {
  ORGANIZATION_MESSAGES,
  ORGANIZATION_TYPES,
  getMyOrganization,
  organizationTypeLabel,
  updateMyOrganization,
} from "../../services/organization";
import type { Organization, OrganizationChanges, OrganizationType } from "../../services/organization";
import { errorMessage, fieldErrorsFrom } from "../../services/formErrors";
import type { FieldErrors } from "../../services/formErrors";
import "./OrganizationForm.css";

type Form = {
  name: string;
  organization_type: OrganizationType | "";
  description: string;
  website: string;
  city: string;
};

const EMPTY: Form = { name: "", organization_type: "", description: "", website: "", city: "" };

function toForm(organization: Organization | null): Form {
  if (!organization) return EMPTY;
  return {
    name: organization.name,
    organization_type: organization.organization_type,
    description: organization.description ?? "",
    website: organization.website ?? "",
    city: organization.city ?? "",
  };
}

function validate(form: Form): FieldErrors {
  const errors: FieldErrors = {};
  if (!form.name.trim()) errors.name = "Your organization needs a name.";
  else if (form.name.trim().length > 150) errors.name = "Keep the name under 150 characters.";
  if (!form.organization_type) errors.organization_type = "Choose a type.";
  if (form.description.trim().length > 5000) errors.description = "Keep this under 5000 characters.";
  if (form.city.trim().length > 100) errors.city = "Keep this under 100 characters.";
  const website = form.website.trim();
  if (website) {
    if (website.length > 255) {
      errors.website = "Keep the address under 255 characters.";
    } else {
      try {
        const url = new URL(website);
        if (!["http:", "https:"].includes(url.protocol) || !url.hostname) throw new Error();
      } catch {
        errors.website = "Use a full address starting with http:// or https://";
      }
    }
  }
  return errors;
}

/**
 * The creator's organization (ADR 0018): shown on every opportunity they publish.
 * With no organization yet, the form starts empty and the first save creates it.
 */
export default function OrganizationForm() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [form, setForm] = useState<Form>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    getMyOrganization()
      .then((result) => {
        if (!active) return;
        setOrganization(result);
        setForm(toForm(result));
        setEditing(result === null);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your organization could not be loaded.", ORGANIZATION_MESSAGES));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // /creator/profile#organization (from "Set up your organization") scrolls here.
  const { hash } = useLocation();
  useEffect(() => {
    if (!loading && hash === "#organization") {
      document.getElementById("organization")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [hash, loading]);

  const changes = useMemo(() => {
    const original = toForm(organization);
    const result: OrganizationChanges = {};
    if (form.name.trim() !== original.name.trim()) result.name = form.name.trim();
    if (form.organization_type && form.organization_type !== original.organization_type) {
      result.organization_type = form.organization_type;
    }
    (["description", "website", "city"] as const).forEach((field) => {
      const after = form[field].trim();
      if (after !== original[field].trim()) result[field] = after === "" ? null : after;
    });
    return result;
  }, [form, organization]);

  function update<K extends keyof Form>(field: K, value: Form[K]) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
    setNotice("");
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    const found = validate(form);
    setErrors(found);
    if (Object.values(found).some(Boolean)) return;
    if (Object.keys(changes).length === 0) {
      setEditing(false);
      return;
    }

    setSaving(true);
    try {
      // Creating it needs both name and type, even if only one was typed this time.
      const body: OrganizationChanges = organization
        ? changes
        : { ...changes, name: form.name.trim(), organization_type: form.organization_type as OrganizationType };
      const saved = await updateMyOrganization(body);
      setNotice(organization ? "Your organization was saved." : "Your organization was created. You can now publish opportunities.");
      setOrganization(saved);
      setForm(toForm(saved));
      setEditing(false);
      window.dispatchEvent(new Event("grow8:organization-changed"));
    } catch (err) {
      setErrors(fieldErrorsFrom(err));
      setError(errorMessage(err, "Your organization could not be saved.", ORGANIZATION_MESSAGES));
    } finally {
      setSaving(false);
    }
  }

  function field(name: "name" | "city" | "website", label: string, placeholder: string) {
    return (
      <label className={`org-field ${errors[name] ? "has-error" : ""}`}>
        <span>{label}</span>
        <input
          type={name === "website" ? "url" : "text"}
          value={form[name]}
          placeholder={placeholder}
          onChange={(event) => update(name, event.target.value)}
          disabled={saving}
        />
        {errors[name] && <em>{errors[name]}</em>}
      </label>
    );
  }

  return (
    <section className="org-card" id="organization" aria-labelledby="org-title">
      <div className="org-heading">
        <span className="org-icon">
          <Building2 size={20} />
        </span>
        <div>
          <h2 id="org-title">Organization</h2>
          <p>Shown on every opportunity you publish. Changes appear on all of them straight away.</p>
        </div>
        {organization && !editing && (
          <button type="button" className="org-button" onClick={() => setEditing(true)}>
            <Pencil size={15} /> Edit
          </button>
        )}
      </div>

      {loading && <p className="org-muted">Loading...</p>}

      {!loading && !organization && (
        <p className="org-callout" role="status">
          You haven't set up your organization yet. Add its name and type to start publishing
          opportunities.
        </p>
      )}

      {!loading && organization && !editing && (
        <dl className="org-view">
          <div>
            <dt>Name</dt>
            <dd>{organization.name}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{organizationTypeLabel(organization.organization_type)}</dd>
          </div>
          <div>
            <dt>City</dt>
            <dd>
              {organization.city ? (
                <>
                  <MapPin size={14} /> {organization.city}
                </>
              ) : (
                "—"
              )}
            </dd>
          </div>
          <div>
            <dt>Website</dt>
            <dd>
              {organization.website ? (
                <a href={organization.website} target="_blank" rel="noopener noreferrer">
                  {organization.website.replace(/^https?:\/\//, "")} <ExternalLink size={13} />
                </a>
              ) : (
                "—"
              )}
            </dd>
          </div>
          <div className="org-wide">
            <dt>About</dt>
            <dd>{organization.description || "—"}</dd>
          </div>
        </dl>
      )}

      {!loading && editing && (
        <form className="org-form" onSubmit={(event) => void handleSave(event)} noValidate>
          <div className="org-grid">
            {field("name", "Organization name", "e.g. Maple Street Bakery")}
            <label className={`org-field ${errors.organization_type ? "has-error" : ""}`}>
              <span>Type</span>
              <select
                value={form.organization_type}
                onChange={(event) => update("organization_type", event.target.value as OrganizationType)}
                disabled={saving}
              >
                <option value="">Choose a type...</option>
                {ORGANIZATION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {errors.organization_type && <em>{errors.organization_type}</em>}
            </label>
            {field("city", "City", "e.g. Calgary")}
            {field("website", "Website", "https://example.com")}
          </div>
          <label className={`org-field ${errors.description ? "has-error" : ""}`}>
            <span>About the organization</span>
            <textarea
              rows={4}
              value={form.description}
              placeholder="What you do, and the kind of help you look for."
              onChange={(event) => update("description", event.target.value)}
              disabled={saving}
            />
            <small>{form.description.length} / 5000</small>
            {errors.description && <em>{errors.description}</em>}
          </label>
          <p className="org-muted">Leave City, Website or About empty to clear them.</p>
          <div className="org-actions">
            {organization && (
              <button
                type="button"
                className="org-button"
                onClick={() => {
                  setForm(toForm(organization));
                  setErrors({});
                  setEditing(false);
                }}
                disabled={saving}
              >
                Cancel
              </button>
            )}
            <button type="submit" className="org-button is-primary" disabled={saving}>
              <Save size={15} /> {saving ? "Saving..." : organization ? "Save organization" : "Create organization"}
            </button>
          </div>
        </form>
      )}

      {notice && (
        <p className="org-notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="org-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
