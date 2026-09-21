type BreakdownProps = {
  breakdown: {
    validity: number;
    blastRadius: number;
    exposure: number;
    criticality: number;
  };
};

export default function RiskScoreBreakdown({ breakdown }: BreakdownProps) {
  const values = [
    { label: 'Validity', value: breakdown.validity, className: 'bar-validity' },
    { label: 'Blast Radius', value: breakdown.blastRadius, className: 'bar-blast' },
    { label: 'Exposure Context', value: breakdown.exposure, className: 'bar-exposure' },
    { label: 'Secret-Class Criticality', value: breakdown.criticality, className: 'bar-criticality' },
  ];

  const total = values.reduce((sum, item) => sum + item.value, 0) || 1;

  return (
    <div className="risk-breakdown">
      <div className="risk-breakdown__bar">
        {values.map((item) => (
          <div
            key={item.label}
            className={`risk-breakdown__segment ${item.className}`}
            style={{ width: `${(item.value / total) * 100}%` }}
            title={`${item.label}: ${item.value}%`}
          />
        ))}
      </div>
      <div className="risk-breakdown__list">
        {values.map((item) => (
          <div key={item.label} className="risk-breakdown__row">
            <span>{item.label}</span>
            <strong>{item.value}%</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
