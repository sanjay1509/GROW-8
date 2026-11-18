import { Link } from "react-router-dom";
import { Award, GraduationCap, MessageCircle } from "lucide-react";
import "../ContributorProfile/ContributorProfile.css";
import "./ContributorComingSoon.css";

type Section = "experience" | "skills" | "feedback";

// What each page will show, and what the backend still needs before it can.
const SECTIONS = {
  experience: {
    icon: Award,
    title: "My Experience",
    description: "Your completed opportunities and verified hours, confirmed by the organizations you worked with.",
    needs: "This page needs the work submission and verification endpoints, which the backend doesn't have yet.",
  },
  skills: {
    icon: GraduationCap,
    title: "My Skills",
    description: "The skills on your profile, and which ones were verified through approved work.",
    needs: "This page needs the contributor profile and skills endpoints (issue #19).",
  },
  feedback: {
    icon: MessageCircle,
    title: "Feedback",
    description: "Ratings and comments from organizations after your work, and the feedback you gave them.",
    needs: "This page needs the feedback endpoints, which the backend doesn't have yet.",
  },
} satisfies Record<Section, { icon: typeof Award; title: string; description: string; needs: string }>;

/** Placeholder for contributor pages that are waiting on backend endpoints. */
export default function ContributorComingSoon({ section }: { section: Section }) {
  const { icon: Icon, title, description, needs } = SECTIONS[section];

  return (
    <div className="cp-page">
      <header className="cp-header">
        <span className="cp-eyebrow">CONTRIBUTOR WORKSPACE</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>

      <section className="cp-card ccs-card">
        <span className="ccs-icon">
          <Icon size={26} />
        </span>
        <strong>Coming soon</strong>
        <p className="cp-muted">{needs}</p>
        <Link className="cp-button is-primary" to="/opportunities">
          Browse opportunities
        </Link>
      </section>
    </div>
  );
}
