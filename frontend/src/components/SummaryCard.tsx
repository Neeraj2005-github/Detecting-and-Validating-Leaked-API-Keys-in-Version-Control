type SummaryCardProps = {
  label: string;
  value: string | number;
  secondary?: string;
  tone?: 'default' | 'danger' | 'success';
};

export default function SummaryCard({ label, value, secondary, tone = 'default' }: SummaryCardProps) {
  return (
    <div className={`summary-card tone-${tone}`}>
      <div className="summary-card__label">{label}</div>
      <div className="summary-card__value">{value}</div>
      {secondary && <div className="summary-card__secondary">{secondary}</div>}
    </div>
  );
}
