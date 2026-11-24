
import React from "react";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import "./RoleCard.css";

export default function RoleCard({
  icon: Icon,
  title,
  description,
  color = "blue",
}: {
  icon: LucideIcon;
  title: string;
  description: ReactNode;
  color?: string;
}) {
  return (
    <article className={`grow8-role-card ${color}`}>
      <div className="grow8-role-icon">
        <Icon size={29} strokeWidth={2.2} />
      </div>

      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  );
}
