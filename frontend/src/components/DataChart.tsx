'use client';

import { VisualizationConfig } from '@/lib/types';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface DataChartProps {
  visualization: VisualizationConfig;
}

export function DataChart({ visualization }: DataChartProps) {
  const { type, title, data, colors } = visualization;

  // Custom tooltip styling
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-zinc-900/95 border border-violet-500/30 rounded-lg px-3 py-2 shadow-xl">
          <p className="text-violet-300 text-xs font-medium mb-1">{label || payload[0]?.name}</p>
          <p className="text-white text-sm font-semibold">
            {typeof payload[0]?.value === 'number'
              ? payload[0].value.toLocaleString()
              : payload[0]?.value}
          </p>
        </div>
      );
    }
    return null;
  };

  // Format large numbers for axis
  const formatAxisValue = (value: number) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
  };

  // Render bar chart
  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
        <XAxis
          dataKey="name"
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
        />
        <YAxis
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickFormatter={formatAxisValue}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );

  // Render horizontal bar chart
  const renderHorizontalBarChart = () => (
    <ResponsiveContainer width="100%" height={Math.max(250, data.length * 35)}>
      <BarChart data={data} layout="vertical" margin={{ top: 10, right: 10, left: 40, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
        <XAxis
          type="number"
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickFormatter={formatAxisValue}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          width={80}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );

  // Render line chart
  const renderLineChart = () => (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" />
        <XAxis
          dataKey="name"
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
        />
        <YAxis
          tick={{ fill: '#a78bfa', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickLine={{ stroke: 'rgba(139, 92, 246, 0.3)' }}
          tickFormatter={formatAxisValue}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={colors[0]}
          strokeWidth={2}
          dot={{ fill: colors[0], strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, fill: colors[0], stroke: '#fff', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );

  // Render pie chart
  const renderPieChart = () => (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
          label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
          labelLine={{ stroke: '#a78bfa', strokeWidth: 1 }}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '11px', color: '#a78bfa' }}
          formatter={(value) => <span className="text-violet-300">{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );

  return (
    <div className="w-full mt-3 mb-2">
      {title && (
        <h3 className="text-sm font-medium text-violet-300 mb-3 text-center">
          {title}
        </h3>
      )}
      <div className="bg-zinc-900/50 rounded-lg p-3 border border-violet-500/20">
        {type === 'bar' && renderBarChart()}
        {type === 'horizontal_bar' && renderHorizontalBarChart()}
        {type === 'line' && renderLineChart()}
        {type === 'pie' && renderPieChart()}
      </div>
    </div>
  );
}
