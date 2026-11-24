import { useEffect, useState } from "react";
import { BadgeCheck, Plus, RefreshCw, X } from "lucide-react";

import { errorMessage } from "../../services/formErrors";
import { MAX_LISTED_SKILLS, getMyProfile, getSkills, setMySkills } from "../../services/profile";
import type { ContributorProfile, ProfileSkill, Skill } from "../../services/profile";
import "./ContributorActivity.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

export default function ContributorSkills() {
  const [profile, setProfile] = useState<ContributorProfile | null>(null);
  const [allSkills, setAllSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [skillToAdd, setSkillToAdd] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([getMyProfile(), getSkills()])
      .then(([nextProfile, skills]) => {
        if (!active) return;
        setProfile(nextProfile);
        setAllSkills(skills);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your skills could not be loaded."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [reload]);

  const listedSkills = profile?.skills.filter((skill) => skill.listed) ?? [];
  const earnedOnly = profile?.skills.filter((skill) => !skill.listed && skill.verified) ?? [];
  const listedCodes = listedSkills.map((skill) => skill.code);
  const addable = allSkills.filter((skill) => !listedCodes.includes(skill.code));

  async function saveSkills(codes: string[], successMessage: string) {
    if (codes.length > MAX_LISTED_SKILLS) {
      setError(`You can list up to ${MAX_LISTED_SKILLS} skills.`);
      return;
    }
    setError("");
    setNotice("");
    setSaving(true);
    try {
      const saved = await setMySkills(codes);
      setProfile(saved);
      setNotice(successMessage);
    } catch (err) {
      const unknown = (err as { details?: { unknown_skills?: string[] } }).details?.unknown_skills;
      setError(unknown?.length
        ? `These skills don't exist any more: ${unknown.join(", ")}.`
        : errorMessage(err, "Your skills could not be saved."));
    } finally {
      setSaving(false);
    }
  }

  function addSkill(code: string) {
    if (!code) return;
    const name = allSkills.find((skill) => skill.code === code)?.name ?? code;
    void saveSkills([...listedCodes, code], `${name} was added to your skills.`);
    setSkillToAdd("");
  }

  function removeSkill(skill: ProfileSkill) {
    void saveSkills(
      listedCodes.filter((code) => code !== skill.code),
      skill.verified
        ? `${skill.name} was removed from your list. It stays as a verified skill.`
        : `${skill.name} was removed.`
    );
  }

  return (
    <div className="act-page">
      <header className="act-header">
        <div>
          <span className="act-eyebrow">CONTRIBUTOR WORKSPACE</span>
          <h1>My Skills</h1>
          <p>List skills to find matching opportunities. Skills are verified when an organization approves your work.</p>
        </div>
        <button type="button" className="act-button" onClick={() => setReload((n) => n + 1)} disabled={loading}>
          <RefreshCw size={15} className={loading ? "act-spin" : ""} /> Refresh
        </button>
      </header>

      {error && <p className="act-error" role="alert">{error}</p>}
      {notice && <p className="act-notice" role="status">{notice}</p>}
      {loading && <p className="act-muted">Loading...</p>}

      {!loading && profile && (
        <>
          <section className="act-card">
            <h2>Your skills</h2>
            {listedSkills.length === 0 ? (
              <p className="act-muted">You haven't listed any skills yet.</p>
            ) : (
              <ul className="act-chips">
                {listedSkills.map((skill) => (
                  <li key={skill.code}>
                    {skill.verified && <BadgeCheck size={14} />}{skill.name}
                    {skill.verified && <small>Verified {formatDate(skill.verified_at)}</small>}
                    <button type="button" aria-label={`Remove ${skill.name}`} onClick={() => removeSkill(skill)} disabled={saving}>
                      <X size={13} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="act-skill-add">
              <select value={skillToAdd} onChange={(event) => setSkillToAdd(event.target.value)} disabled={saving || addable.length === 0} aria-label="Choose a skill to add">
                <option value="">{addable.length === 0 ? "No more skills to add" : "Choose a skill..."}</option>
                {addable.map((skill) => <option key={skill.code} value={skill.code}>{skill.name}</option>)}
              </select>
              <button type="button" className="act-button" onClick={() => addSkill(skillToAdd)} disabled={!skillToAdd || saving}>
                <Plus size={15} /> Add
              </button>
              <span className="act-muted">{listedSkills.length} / {MAX_LISTED_SKILLS}</span>
            </div>
          </section>

          {earnedOnly.length > 0 && (
            <section className="act-card">
              <h2>Verified through work</h2>
              <p className="act-muted">You earned these through approved work. Add one to your list to hear about matching opportunities.</p>
              <ul className="act-chips">
                {earnedOnly.map((skill) => (
                  <li key={skill.code}>
                    <BadgeCheck size={14} />{skill.name}<small>Verified {formatDate(skill.verified_at)}</small>
                    <button type="button" onClick={() => addSkill(skill.code)} disabled={saving}><Plus size={13} /> Add</button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {saving && <p className="act-muted">Saving...</p>}
        </>
      )}
    </div>
  );
}
