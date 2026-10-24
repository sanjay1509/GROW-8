
import React, { useEffect, useRef, useState } from "react";
import "./SlideIn.css";

export default function SlideIn({
  children,
  direction = "up",
  delay = 0,
  className = "",
  threshold = 0.15,
}) {
  const elementRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Animate in when entering the viewport
        // Reset the animation when leaving it
        setIsVisible(entry.isIntersecting);
      },
      {
        threshold,
        rootMargin: "0px 0px -30px 0px",
      }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [threshold]);

  return (
    <div
      ref={elementRef}
      className={[
        "grow8-slide-in",
        `grow8-slide-${direction}`,
        isVisible ? "grow8-slide-visible" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ "--grow8-slide-delay": `${delay}ms` }}
    >
      {children}
    </div>
  );
}
