import { AlertTriangle, CheckCircle2, CircleDashed, ShieldAlert } from 'lucide-react';
import type { SeverityLevel } from '../types';

const map: Record<SeverityLevel, { label: string; icon: JSX.Element; classes: string }> = {
  critical: {
    label: 'Critical',
    icon: <AlertTriangle size={12} />,
    classes: 'severity critical',
  },
  high: {
    label: 'High',
    icon: <ShieldAlert size={12} />,
    classes: 'severity high',
  },
  medium: {
    label: 'Medium',
    icon: <CircleDashed size={12} />,
    classes: 'severity medium',
  },
  low: {
    label: 'Low',
    icon: <CheckCircle2 size={12} />,
    classes: 'severity low',
  },
};

export default function SeverityBadge({ level }: { level: SeverityLevel }) {
  const config = map[level];
  return (
    <span className={config.classes}>
      {config.icon}
      {config.label}
    </span>
  );
}
