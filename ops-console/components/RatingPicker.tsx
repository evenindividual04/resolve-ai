"use client";

interface RatingPickerProps {
  value: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
}

const RATINGS = [1, 2, 3, 4, 5];

function ratingClass(rating: number): string {
  if (rating <= 2) return "danger";
  if (rating === 3) return "warn";
  return "";
}

export function RatingPicker({ value, onChange, disabled }: RatingPickerProps) {
  return (
    <div className="rating-group" role="group" aria-label="Rating 1 to 5">
      {RATINGS.map((r) => (
        <button
          key={r}
          type="button"
          className={`rating-segment${value === r ? ` selected ${ratingClass(r)}` : ""}`}
          onClick={() => !disabled && onChange(r)}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight" && r < 5) onChange(r + 1);
            if (e.key === "ArrowLeft" && r > 1) onChange(r - 1);
          }}
          aria-pressed={value === r}
          aria-label={`Rating ${r}`}
          disabled={disabled}
        >
          {r}
        </button>
      ))}
    </div>
  );
}
