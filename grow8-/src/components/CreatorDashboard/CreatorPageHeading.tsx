import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

interface Props {
  title: string;
  description: string;
  children?: ReactNode;
}

export default function CreatorPageHeading({ title, description, children }: Props) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      headingRef.current?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="creator-page-heading">
      <div>
        <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
