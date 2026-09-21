import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function MTTRTrendChart({ data }: { data: { date: string; avg_mttr_hours: number }[] }) {
  return (
    <div className="mttr-chart">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2c3b42" />
          <XAxis dataKey="date" stroke="#8ea0a8" />
          <YAxis stroke="#8ea0a8" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#111920',
              border: '1px solid #27343c',
              borderRadius: '8px',
              color: '#e8eef2',
            }}
          />
          <Line type="monotone" dataKey="avg_mttr_hours" stroke="#f3bc57" strokeWidth={3} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
