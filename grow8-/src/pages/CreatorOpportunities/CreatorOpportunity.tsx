
import {
  useEffect,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, BriefcaseBusiness, Save, Send } from "lucide-react";
import "./CreatorOpportunity.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type Category = {
  code: string;
  name: string;
  description: string;
};

type OpportunityForm = {
  title: string;
  category_id: string;
  description: string;
  requirements: string;
  location: string;
  work_mode: string;
  start_date: string;
  end_date: string;
  application_deadline: string;
  expected_hours: string;
  applicant_limit: string;
  compensation_type: string;
  compensation_amount: string;
  compensation_currency: string;
  working_conditions: string;
  safety_information: string;
  accessibility_details: string;
};

const initialForm: OpportunityForm = {
  title: "",
  category_id: "",
  description: "",
  requirements: "",
  location: "",
  work_mode: "remote",
  start_date: "",
  end_date: "",
  application_deadline: "",
  expected_hours: "",
  applicant_limit: "",
  compensation_type: "unpaid",
  compensation_amount: "",
  compensation_currency: "CAD",
  working_conditions: "",
  safety_information: "",
  accessibility_details: "",
};

function getErrorMessage(data: unknown): string {
  if (!data || typeof data !== "object") {
    return "The server could not complete your request.";
  }

  const obj = data as {
    detail?: unknown;
    message?: unknown;
    error?: { message?: unknown; details?: unknown };
  };

  if (typeof obj.detail === "string") {
    return obj.detail;
  }

  if (typeof obj.message === "string") {
    return obj.message;
  }

  if (typeof obj.error?.message === "string") {
    const details = obj.error.details;

    if (Array.isArray(details)) {
      const messages = details
        .map((item) => {
          if (item && typeof item === "object" && "message" in item) {
            return String(item.message);
          }
          return "";
        })
        .filter(Boolean);

      return messages.length
        ? `${obj.error.message}: ${messages.join("; ")}`
        : obj.error.message;
    }

    return obj.error.message;
  }

  if (Array.isArray(obj.detail)) {
    return obj.detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String(item.msg)
          : String(item)
      )
      .join("; ");
  }

  return "The server rejected the request. Check the API response.";
}

export default function CreateOpportunity() {
  const navigate = useNavigate();

  const [form, setForm] = useState<OpportunityForm>(initialForm);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadCategories() {
      try {
        const response = await fetch(`${API_BASE_URL}/categories`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Unable to load categories from the backend.");
        }

        const result: unknown = await response.json();

        const rows = Array.isArray(result)
          ? result
          : result &&
              typeof result === "object" &&
              "items" in result &&
              Array.isArray(result.items)
            ? result.items
            : result &&
                typeof result === "object" &&
                "categories" in result &&
                Array.isArray(result.categories)
              ? result.categories
              : [];

        setCategories(
          rows.filter(
            (item): item is Category =>
              !!item &&
              typeof item === "object" &&
              "code" in item &&
              typeof item.code === "string" &&
              "name" in item &&
              typeof item.name === "string"
          )
        );
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Could not load opportunity categories."
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoadingCategories(false);
        }
      }
    }

    void loadCategories();

    return () => controller.abort();
  }, []);

  function handleChange(
    event: ChangeEvent<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >
  ) {
    const { name, value } = event.target;

    setForm((previous) => ({ ...previous, [name]: value }));
    setError("");
    setSuccess("");
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
    saveAsDraft: boolean
  ) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!form.title.trim()) {
      setError("Please enter an opportunity title.");
      return;
    }

    if (!form.category_id) {
      setError("Please select a category.");
      return;
    }

    if (!form.description.trim()) {
      setError("Please enter an opportunity description.");
      return;
    }

    if (
      form.start_date &&
      form.end_date &&
      form.end_date < form.start_date
    ) {
      setError("The end date cannot be earlier than the start date.");
      return;
    }

    if (
      form.application_deadline &&
      form.start_date &&
      form.application_deadline > form.start_date
    ) {
      setError("The application deadline should not be after the start date.");
      return;
    }

    if (
      form.compensation_type === "paid" &&
      (!form.compensation_amount ||
        !Number.isFinite(Number(form.compensation_amount)) ||
        Number(form.compensation_amount) < 0)
    ) {
      setError("Enter a valid compensation amount.");
      return;
    }

    const token = localStorage.getItem("access_token");

    if (!token) {
      setError("Please sign in as a creator before continuing.");
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        title: form.title.trim(),
        category: form.category_id,
        description: form.description.trim(),
        requirements: form.requirements.trim() || null,
        location: form.location.trim() || null,
        work_mode: form.work_mode,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        application_deadline: form.application_deadline
          ? `${form.application_deadline}T23:59:59Z`
          : null,
        expected_hours: form.expected_hours
          ? Number(form.expected_hours)
          : null,
        applicant_limit: form.applicant_limit
          ? Number(form.applicant_limit)
          : null,
        compensation_type:
          form.compensation_type === "paid" ? "stipend" : "unpaid",
        compensation_amount:
          form.compensation_type === "paid"
            ? Number(form.compensation_amount)
            : null,
        working_conditions: form.working_conditions.trim() || null,
        safety_information: form.safety_information.trim() || null,
        accessibility_details:
          form.accessibility_details.trim() || null,
      };

      // First create the opportunity.
      const response = await fetch(`${API_BASE_URL}/opportunities`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(getErrorMessage(data));
      }

      const created = data as {
        opportunity_id?: number;
        status?: string;
      };

      // Publish only when the user clicked Publish Opportunity.
      if (!saveAsDraft) {
        if (!created.opportunity_id) {
          throw new Error(
            "The opportunity was created, but its ID was not returned. Check the create API response."
          );
        }

        const publishResponse = await fetch(
          `${API_BASE_URL}/opportunities/${created.opportunity_id}/publish`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const publishData: unknown = await publishResponse
          .json()
          .catch(() => null);

        if (!publishResponse.ok) {
          throw new Error(
            `The opportunity was created, but publishing failed (HTTP ${publishResponse.status}): ${getErrorMessage(publishData)}`
          );
        }
      }

      setSuccess(
        saveAsDraft
          ? "Your opportunity draft was saved."
          : "Your opportunity was published successfully."
      );

      window.setTimeout(() => {
        navigate("/creator/opportunities");
      }, 900);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while creating the opportunity."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="create-opportunity-page">
      <div className="create-opportunity-container">
        <Link to="/creator/dashboard" className="co-back-link">
          <ArrowLeft size={16} />
          Back to Dashboard
        </Link>

        <header className="co-header">
          <div>
            <span className="co-eyebrow">CREATOR WORKSPACE</span>
            <h1>Create an Opportunity</h1>
            <p>
              Share meaningful work and help contributors learn, contribute,
              and grow.
            </p>
          </div>

          <span className="co-header-icon">
            <BriefcaseBusiness size={29} />
          </span>
        </header>

        {error && (
          <div className="co-alert co-alert-error" role="alert">
            <strong>Unable to continue</strong>
            <p>{error}</p>
          </div>
        )}

        {success && (
          <div className="co-alert co-alert-success" role="status">
            {success}
          </div>
        )}

        <form
          className="co-form"
          onSubmit={(event) => void handleSubmit(event, false)}
        >
          <section className="co-card">
            <div className="co-section-heading">
              <span className="co-section-number">01</span>
              <div>
                <h2>Basic information</h2>
                <p>Describe the opportunity and what it offers.</p>
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="title">Opportunity title *</label>
              <input
                id="title"
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="e.g. Frontend Developer Volunteer"
                maxLength={200}
                required
              />
            </div>

            <div className="co-form-grid">
              <div className="co-field">
                <label htmlFor="category_id">Category *</label>
                <select
                  id="category_id"
                  name="category_id"
                  value={form.category_id}
                  onChange={handleChange}
                  disabled={loadingCategories}
                  required
                >
                  <option value="">
                    {loadingCategories
                      ? "Loading categories..."
                      : "Choose a category"}
                  </option>

                  {categories.map((category) => (
                    <option key={category.code} value={category.code}>
                      {category.name}
                    </option>
                  ))}
                </select>

                {!loadingCategories && categories.length === 0 && (
                  <small>
                    No categories found. Check GET /api/v1/categories.
                  </small>
                )}
              </div>

              <div className="co-field">
                <label htmlFor="location">Location</label>
                <input
                  id="location"
                  name="location"
                  value={form.location}
                  onChange={handleChange}
                  placeholder="e.g. Calgary, Alberta"
                />
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="description">Description *</label>
              <textarea
                id="description"
                name="description"
                value={form.description}
                onChange={handleChange}
                placeholder="Explain the purpose, responsibilities, and expected outcomes..."
                rows={6}
                required
              />
            </div>

            <div className="co-field">
              <label htmlFor="requirements">Requirements and skills</label>
              <textarea
                id="requirements"
                name="requirements"
                value={form.requirements}
                onChange={handleChange}
                placeholder="List useful skills, experience, or qualifications..."
                rows={4}
              />
            </div>
          </section>

          <section className="co-card">
            <div className="co-section-heading">
              <span className="co-section-number">02</span>
              <div>
                <h2>Work arrangement</h2>
                <p>Set expectations for location, timing, and workload.</p>
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="work_mode">Work mode *</label>
              <select
                id="work_mode"
                name="work_mode"
                value={form.work_mode}
                onChange={handleChange}
                required
              >
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
              </select>
            </div>

            <div className="co-form-grid">
              <div className="co-field">
                <label htmlFor="start_date">Start date</label>
                <input
                  id="start_date"
                  name="start_date"
                  type="date"
                  value={form.start_date}
                  onChange={handleChange}
                />
              </div>

              <div className="co-field">
                <label htmlFor="end_date">End date</label>
                <input
                  id="end_date"
                  name="end_date"
                  type="date"
                  min={form.start_date || undefined}
                  value={form.end_date}
                  onChange={handleChange}
                />
              </div>

              <div className="co-field">
                <label htmlFor="application_deadline">
                  Application deadline
                </label>
                <input
                  id="application_deadline"
                  name="application_deadline"
                  type="date"
                  value={form.application_deadline}
                  onChange={handleChange}
                />
              </div>

              <div className="co-field">
                <label htmlFor="expected_hours">Expected hours</label>
                <input
                  id="expected_hours"
                  name="expected_hours"
                  type="number"
                  min="1"
                  step="1"
                  value={form.expected_hours}
                  onChange={handleChange}
                  placeholder="e.g. 40"
                />
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="applicant_limit">Applicant limit</label>
              <input
                id="applicant_limit"
                name="applicant_limit"
                type="number"
                min="1"
                step="1"
                value={form.applicant_limit}
                onChange={handleChange}
                placeholder="Leave blank for no limit"
              />
            </div>
          </section>

          <section className="co-card">
            <div className="co-section-heading">
              <span className="co-section-number">03</span>
              <div>
                <h2>Compensation</h2>
                <p>Explain whether the opportunity is paid or voluntary.</p>
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="compensation_type">Compensation type *</label>
              <select
                id="compensation_type"
                name="compensation_type"
                value={form.compensation_type}
                onChange={handleChange}
              >
                <option value="unpaid">Unpaid / Volunteer</option>
                <option value="paid">Paid</option>
              </select>
            </div>

            {form.compensation_type === "paid" && (
              <div className="co-form-grid">
                <div className="co-field">
                  <label htmlFor="compensation_amount">Amount *</label>
                  <input
                    id="compensation_amount"
                    name="compensation_amount"
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.compensation_amount}
                    onChange={handleChange}
                    required
                    placeholder="e.g. 25"
                  />
                </div>

                <div className="co-field">
                  <label htmlFor="compensation_currency">Currency</label>
                  <select
                    id="compensation_currency"
                    name="compensation_currency"
                    value={form.compensation_currency}
                    onChange={handleChange}
                  >
                    <option value="CAD">CAD — Canadian Dollar</option>
                    <option value="USD">USD — US Dollar</option>
                  </select>
                </div>
              </div>
            )}
          </section>

          <section className="co-card">
            <div className="co-section-heading">
              <span className="co-section-number">04</span>
              <div>
                <h2>Safety and accessibility</h2>
                <p>Help contributors understand the work environment.</p>
              </div>
            </div>

            <div className="co-field">
              <label htmlFor="working_conditions">Working conditions</label>
              <textarea
                id="working_conditions"
                name="working_conditions"
                value={form.working_conditions}
                onChange={handleChange}
                rows={3}
                placeholder="Describe hours, supervision, equipment, and expectations..."
              />
            </div>

            <div className="co-field">
              <label htmlFor="safety_information">Safety information</label>
              <textarea
                id="safety_information"
                name="safety_information"
                value={form.safety_information}
                onChange={handleChange}
                rows={3}
                placeholder="Include relevant safety guidance and precautions..."
              />
            </div>

            <div className="co-field">
              <label htmlFor="accessibility_details">
                Accessibility arrangements
              </label>
              <textarea
                id="accessibility_details"
                name="accessibility_details"
                value={form.accessibility_details}
                onChange={handleChange}
                rows={3}
                placeholder="Describe accessibility features or accommodations..."
              />
            </div>
          </section>

          <div className="co-actions">
            <Link
              to="/creator/dashboard"
              className="co-button co-button-light"
            >
              Cancel
            </Link>

            <button
              type="button"
              className="co-button co-button-outline"
              disabled={submitting}
              onClick={(event) => {
                const formElement = event.currentTarget.form;

                if (formElement && formElement.reportValidity()) {
                  void handleSubmit(
                    {
                      preventDefault: () => {},
                    } as FormEvent<HTMLFormElement>,
                    true
                  );
                }
              }}
            >
              <Save size={17} />
              Save Draft
            </button>

            <button
              type="submit"
              className="co-button co-button-primary"
              disabled={submitting}
            >
              <Send size={17} />
              {submitting ? "Submitting..." : "Publish Opportunity"}
            </button>
          </div>

          <p className="co-required-note">
            Fields marked * are required. The backend determines which
            opportunities are publicly visible.
          </p>
        </form>
      </div>
    </main>
  );
}
