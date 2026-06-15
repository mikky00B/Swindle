type StoryBadgeProps = {
  label: string;
  emoji: string;
};

export function StoryBadge({ label, emoji }: StoryBadgeProps) {
  return (
    <div className="story-badge">
      <span aria-hidden="true">{emoji}</span>
      <strong>{label}</strong>
    </div>
  );
}
