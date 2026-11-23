import { useEffect, useState } from "react";
import { Star } from "lucide-react";

import { getUserRating } from "../../services/feedback";
import type { UserRating } from "../../services/feedback";
import "./Rating.css";

/** Read-only stars, e.g. for a feedback someone gave. */
export function Stars({ value, size = 15 }: { value: number; size?: number }) {
  return (
    <span className="g8-stars" role="img" aria-label={`${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((index) => (
        <Star
          key={index}
          size={size}
          className={index <= Math.round(value) ? "is-on" : ""}
          aria-hidden="true"
        />
      ))}
    </span>
  );
}

/** 1-5 star picker for the feedback form. */
export function StarInput({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  const [hover, setHover] = useState(0);
  const labels = ["Poor", "Fair", "Good", "Very good", "Excellent"];
  const shown = hover || value;

  return (
    <div className="g8-star-input">
      <div role="radiogroup" aria-label="Rating" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((index) => (
          <button
            key={index}
            type="button"
            role="radio"
            aria-checked={value === index}
            aria-label={`${index} - ${labels[index - 1]}`}
            onMouseEnter={() => setHover(index)}
            onClick={() => onChange(index)}
            disabled={disabled}
          >
            <Star size={24} className={index <= shown ? "is-on" : ""} aria-hidden="true" />
          </button>
        ))}
      </div>
      <span>{shown ? labels[shown - 1] : "Choose a rating"}</span>
    </div>
  );
}

/**
 * A user's public rating from approved feedback (GET /users/{id}/rating).
 * Shows "No ratings yet" when nobody has rated them, and nothing if it can't load.
 */
export function RatingBadge({ userId, compact = false }: { userId: number; compact?: boolean }) {
  const [rating, setRating] = useState<UserRating | null>(null);

  useEffect(() => {
    let active = true;
    getUserRating(userId)
      .then((result) => {
        if (active) setRating(result);
      })
      .catch(() => {
        // A missing rating shouldn't break the page around it.
      });
    return () => {
      active = false;
    };
  }, [userId]);

  if (!rating) {
    return null;
  }

  if (rating.average_rating === null || rating.approved_feedback_count === 0) {
    return <span className="g8-rating is-empty">No ratings yet</span>;
  }

  const average = Number(rating.average_rating);
  return (
    <span
      className="g8-rating"
      title={`${average.toFixed(1)} out of 5 from ${rating.approved_feedback_count} approved review(s)`}
    >
      <Star size={14} className="is-on" aria-hidden="true" />
      <strong>{average.toFixed(1)}</strong>
      {!compact && (
        <span>
          ({rating.approved_feedback_count}{" "}
          {rating.approved_feedback_count === 1 ? "review" : "reviews"})
        </span>
      )}
    </span>
  );
}
