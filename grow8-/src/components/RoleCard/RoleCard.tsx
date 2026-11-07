
import React from "react";
import "./RoleCard.css";

export default function RoleCard({
  icon: Icon,
  title,
  description,
  color = "blue",
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
