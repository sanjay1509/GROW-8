
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  ClipboardList,
  Award,
  GraduationCap,
  MessageCircle,
  UserRound,
  Settings,
  HomeIcon,
} from "lucide-react";
import "./ContributorSidebar.css";

const navigation = [
  { label: "Home", path: "/", icon: HomeIcon },
  { label: "Dashboard", path: "/contributor-dashboard", icon: LayoutDashboard , end:"True"},
  { label: "Browse Opportunities", path: "/opportunities", icon: Search },
  { label: "My Applications", path: "/contributor/applications", icon: ClipboardList },
  { label: "My Experience", path: "/contributor/experience", icon: Award },
  { label: "My Skills", path: "/contributor/skills", icon: GraduationCap },
  { label: "Feedback", path: "/contributor/feedback", icon: MessageCircle },
  { label: "Profile", path: "/contributor/profile", icon: UserRound },
  { label: "Settings", path: "/contributor/settings", icon: Settings },
];

export default function ContributorSidebar() {
  return (
    <aside className="contributor-sidebar">
      <nav className="contributor-sidebar-nav" aria-label="Contributor navigation">
        {navigation.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={label}
            to={path}
            end={path === "/contributor-dashboard"}
            className={({ isActive }) =>
              `contributor-nav-link${isActive ? " active" : ""}`
            }
          >
            <Icon size={19} strokeWidth={2} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
