'use client';

import { useMemo, useCallback } from 'react';
import { VisualizationConfig, VisualizationDataPoint } from '@/lib/types';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';

interface DataChartProps {
  visualization: VisualizationConfig;
}

export function DataChart({ visualization }: DataChartProps) {
  const { type, title, data, colors } = visualization;

  // Memoize formatLabel function to avoid recreation on every render
  const formatLabel = useCallback((label: string) => {
    if (!label) return '';

    // Check if it's a date string (contains date patterns)
    const datePatterns = [
      /^\d{4}-\d{2}-\d{2}/, // 2025-09-30
      /^\d{2}\/\d{2}\/\d{4}/, // 09/30/2025
      /^\d{4}\/\d{2}\/\d{2}/, // 2025/09/30
    ];

    for (const pattern of datePatterns) {
      if (pattern.test(label)) {
        try {
          const date = new Date(label.split(' ')[0]); // Remove time part
          if (!isNaN(date.getTime())) {
            // Format as "MMM 'YY" (e.g., "Sep '25")
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const month = months[date.getMonth()];
            const year = date.getFullYear().toString().slice(-2);
            return `${month} '${year}`;
          }
        } catch {
          // Fall through to default
        }
      }
    }

    // Truncate long labels
    if (label.length > 12) {
      return label.substring(0, 10) + '...';
    }
    return label;
  }, []);

  // Memoize aggregated data to avoid recalculation on every render
  const aggregatedData = useMemo(() => {
    if (data.length <= 12) return data;

    // Group data into buckets (aim for ~8-12 points)
    const bucketSize = Math.ceil(data.length / 10);
    const aggregated: typeof data = [];

    for (let i = 0; i < data.length; i += bucketSize) {
      const bucket = data.slice(i, i + bucketSize);
      const avgValue = bucket.reduce((sum, item) => sum + (item.value || 0), 0) / bucket.length;
      aggregated.push({
        name: bucket[0].name, // Use first item's label
        value: Math.round(avgValue * 100) / 100
      });
    }

    return aggregated;
  }, [data]);

  // Custom tooltip styling with projection support
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      // Check if this is a projection chart with both actual and projected
      const actualPayload = payload.find((p: any) => p.dataKey === 'actual' && p.value !== null);
      const projectedPayload = payload.find((p: any) => p.dataKey === 'projected' && p.value !== null);
      const isProjected = projectedPayload && !actualPayload;
      const displayValue = actualPayload?.value ?? projectedPayload?.value ?? payload[0]?.value;

      return (
        <div className={`bg-zinc-900/95 border rounded-lg px-3 py-2 shadow-xl ${
          isProjected ? 'border-amber-500/30' : 'border-violet-500/30'
        }`}>
          <p className={`text-xs font-medium mb-1 ${
            isProjected ? 'text-amber-300' : 'text-violet-300'
          }`}>
            {formatLabel(label) || payload[0]?.name}
            {isProjected && <span className="ml-1 text-[10px] opacity-70">(projected)</span>}
          </p>
          <p className="text-white text-sm font-semibold">
            {typeof displayValue === 'number'
              ? displayValue.toLocaleString('en-IN')
              : displayValue}
          </p>
        </div>
      );
    }
    return null;
  };

  // Memoize formatAxisValue to avoid recreation on every render
  const formatAxisValue = useCallback((value: number) => {
    if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
  }, []);

  // Render bar chart
  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: '#a78bfa', fontSize: 10 }}
          axisLine={{ stroke: 'rgba(139, 92, 246, 0.2)' }}
          tickLine={false}
          tickFormatter={formatLabel}
          interval={0}
          angle={data.length > 5 ? -20 : 0}
          textAnchor={data.length > 5 ? "end" : "middle"}
          height={data.length > 5 ? 50 : 30}
        />
        <YAxis
          tick={{ fill: '#a78bfa', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatAxisValue}
          width={45}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(139, 92, 246, 0.1)' }} />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );

  // Render horizontal bar chart
  const renderHorizontalBarChart = () => (
    <ResponsiveContainer width="100%" height={Math.min(300, Math.max(180, data.length * 40))}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#a78bfa', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatAxisValue}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: '#a78bfa', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={70}
          tickFormatter={(v) => v.length > 10 ? v.substring(0, 10) + '...' : v}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(139, 92, 246, 0.1)' }} />
        <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={30}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );

  // Render line/area chart (cleaner for trends)
  // Supports projection data with dotted lines
  const renderLineChart = () => {
    // Use pre-aggregated data (memoized)
    const chartData = aggregatedData;
    const showDots = chartData.length <= 15;

    // Check if this chart has projection data
    const hasProjection = visualization.isProjection || chartData.some((d: VisualizationDataPoint) => d.projected);

    // If has projection, split data for dual rendering
    if (hasProjection) {
      // Find the split point (last actual data point)
      const lastActualIndex = chartData.findIndex((d: VisualizationDataPoint) => d.projected) - 1;
      const splitIndex = lastActualIndex >= 0 ? lastActualIndex : Math.floor(chartData.length * 0.7);

      // Create data arrays: actual has nulls for projected, projected has nulls for actual
      // Include one overlapping point for smooth connection
      const actualData = chartData.map((d: VisualizationDataPoint, i: number) => ({
        ...d,
        actual: i <= splitIndex ? d.value : null,
        projected: i >= splitIndex ? d.value : null,
      }));

      return (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={actualData} margin={{ top: 10, right: 10, left: -5, bottom: 5 }}>
            <defs>
              {/* Gradient for actual data */}
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors[0]} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={colors[0]} stopOpacity={0}/>
              </linearGradient>
              {/* Gradient for projected data - lighter/different shade */}
              <linearGradient id="colorProjected" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: '#a78bfa', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatLabel}
              interval={Math.max(0, Math.floor(chartData.length / 6) - 1)}
            />
            <YAxis
              tick={{ fill: '#a78bfa', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatAxisValue}
              width={45}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* Actual data - solid line */}
            <Area
              type="monotone"
              dataKey="actual"
              stroke={colors[0]}
              strokeWidth={2}
              fill="url(#colorActual)"
              dot={showDots ? { fill: colors[0], strokeWidth: 0, r: 3 } : false}
              activeDot={{ r: 5, fill: colors[0], stroke: '#fff', strokeWidth: 2 }}
              connectNulls={false}
              name="Actual"
            />
            {/* Projected data - dotted line with different color */}
            <Area
              type="monotone"
              dataKey="projected"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              fill="url(#colorProjected)"
              dot={showDots ? { fill: '#f59e0b', strokeWidth: 0, r: 3 } : false}
              activeDot={{ r: 5, fill: '#f59e0b', stroke: '#fff', strokeWidth: 2 }}
              connectNulls={false}
              name="Projected"
            />
            {/* Legend to show actual vs projected */}
            <Legend
              verticalAlign="top"
              height={24}
              formatter={(value) => (
                <span style={{ color: value === 'Actual' ? colors[0] : '#f59e0b', fontSize: '10px' }}>
                  {value === 'Actual' ? '● Actual' : '◌ Projected'}
                </span>
              )}
            />
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    // Standard chart without projection
    return (
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -5, bottom: 5 }}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors[0]} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={colors[0]} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.1)" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: '#a78bfa', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatLabel}
            interval={Math.max(0, Math.floor(chartData.length / 6) - 1)}
          />
          <YAxis
            tick={{ fill: '#a78bfa', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatAxisValue}
            width={45}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={colors[0]}
            strokeWidth={2}
            fill="url(#colorValue)"
            dot={showDots ? { fill: colors[0], strokeWidth: 0, r: 3 } : false}
            activeDot={{ r: 5, fill: colors[0], stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  // Render pie chart
  const renderPieChart = () => {
    // Limit to top items for readability
    const chartData = data.length > 6
      ? [...data].sort((a, b) => b.value - a.value).slice(0, 6)
      : data;

    return (
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={75}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) =>
              `${name.length > 8 ? name.substring(0, 8) + '..' : name} ${(percent * 100).toFixed(0)}%`
            }
            labelLine={{ stroke: '#a78bfa', strokeWidth: 1 }}
          >
            {chartData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="w-full mt-2">
      {title && (
        <h3 className="text-xs font-medium text-violet-400 mb-2 text-center uppercase tracking-wide">
          {title}
        </h3>
      )}
      <div className="bg-zinc-900/40 rounded-xl p-2 border border-violet-500/10">
        {type === 'bar' && renderBarChart()}
        {type === 'horizontal_bar' && renderHorizontalBarChart()}
        {type === 'line' && renderLineChart()}
        {type === 'pie' && renderPieChart()}
      </div>
    </div>
  );
}
