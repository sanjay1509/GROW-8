import { Link, NavLink } from "react-router-dom";
import {
  ArrowLeft,
  BriefcaseBusiness,
  CircleUserRound,
  ClipboardCheck,
  HomeIcon,
  LayoutDashboard,
  MessageSquareText,
  Settings,
  UsersRound,
} from "lucide-react";
import "./CreatorSidebar.css";

const navigation = [
  { path: "/", label: "Home", icon: HomeIcon},
  { path: "/creator/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { path: "/creator/opportunities", label: "My Opportunities", icon: BriefcaseBusiness },
  { path: "/creator/applications", label: "Applications", icon: UsersRound },
  { path: "/creator/submissions", label: "Submissions", icon: ClipboardCheck },
  { path: "/creator/feedback", label: "Feedback", icon: MessageSquareText },
  { path: "/creator/profile", label: "Profile", icon: CircleUserRound },
  { path: "/creator/settings", label: "Settings", icon: Settings },
];

export default function CreatorSidebar() {
  return (
    <aside className="creator-sidebar">
      <nav className="creator-nav" aria-label="Creator navigation">
        {navigation.map(({ path, label, icon: Icon, end }) => (
          <NavLink
            key={path}
            to={path}
            end={end}
            className={({ isActive }) => `creator-nav-item${isActive ? " is-active" : ""}`}
          >
            <Icon size={18} strokeWidth={1.9} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <Link className="creator-sidebar-footer" to="/">
        <ArrowLeft size={16} />Back to Grow8
      </Link>
    </aside>
  );
}
