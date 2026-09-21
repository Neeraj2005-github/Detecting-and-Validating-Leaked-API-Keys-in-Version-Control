import { CheckCircle2, CircleDashed, ShieldAlert } from 'lucide-react';

type Transition = {
  state: 'LEAKED_VALID' | 'ROTATED' | 'CONFIRMED_REMEDIATED';
  timestamp: string;
};

const stateOrdering = ['LEAKED_VALID', 'ROTATED', 'CONFIRMED_REMEDIATED'];

export default function StateTimeline({ transitions }: { transitions: Transition[] }) {
  const ordered = [...(transitions || [])].sort((a, b) =>
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  const getIcon = (state: string) => {
    if (state === 'CONFIRMED_REMEDIATED') return <CheckCircle2 size={16} />;
    if (state === 'ROTATED') return <ShieldAlert size={16} />;
    return <CircleDashed size={16} />;
  };

  return (
    <div className="state-timeline">
      {stateOrdering.map((stateName, index) => {
        const match = ordered.find((item) => item.state === stateName);
        if (!match) return null;
        return (
          <div key={stateName} className="state-step">
            <div className="state-step__marker">{getIcon(stateName)}</div>
            <div className="state-step__content">
              <div className="state-step__label">{stateName}</div>
              <div className="state-step__time">{new Date(match.timestamp).toLocaleString()}</div>
            </div>
            {index < stateOrdering.length - 1 && <div className="state-step__line" />}
          </div>
        );
      })}
    </div>
  );
}
