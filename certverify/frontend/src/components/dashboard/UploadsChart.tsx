import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface UploadsChartProps {
  data: Array<{ date: string; count: number }>;
}

export const UploadsChart: React.FC<UploadsChartProps> = ({ data }) => {
  return (
    <div className="h-64 w-full pt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tick={{ fontSize: 12, fill: '#64748b' }}
          />
          <YAxis
            allowDecimals={false}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tick={{ fontSize: 12, fill: '#64748b' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              borderRadius: '8px',
              border: 'none',
              color: '#ffffff',
              fontSize: '12px',
            }}
            cursor={{ fill: 'rgba(59, 130, 246, 0.05)' }}
          />
          <Bar
            dataKey="count"
            name="Uploads"
            fill="#3b82f6"
            radius={[6, 6, 0, 0]}
            maxBarSize={48}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

