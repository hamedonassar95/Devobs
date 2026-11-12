import React, { useState } from 'react';
import { MetricPoint } from '../../types/serverDashboard';
import { Activity, Clock } from 'lucide-react';

interface InteractiveMetricsChartProps {
  metrics: MetricPoint[];
}

export const InteractiveMetricsChart: React.FC<InteractiveMetricsChartProps> = ({ metrics }) => {
  const [selectedMetric, setSelectedMetric] = useState<'cpu' | 'memory' | 'requests' | 'latency'>('cpu');
  const [timeRange, setTimeRange] = useState<'24h' | '12h' | '6h'>('24h');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const displayedMetrics =
    timeRange === '6h'
      ? metrics.slice(-4)
      : timeRange === '12h'
      ? metrics.slice(-7)
      : metrics;

  const getMetricConfig = () => {
    switch (selectedMetric) {
      case 'cpu':
        return {
          title: 'استهلاك المعالج المركزي (CPU Load)',
          unit: '%',
          color: '#6366f1', // Indigo
          gradientId: 'gradCpu',
          getValue: (m: MetricPoint) => m.cpu,
          maxVal: 100,
        };
      case 'memory':
        return {
          title: 'استهلاك الذاكرة العشوائية (RAM Usage)',
          unit: '%',
          color: '#10b981', // Emerald
          gradientId: 'gradMem',
          getValue: (m: MetricPoint) => m.memory,
          maxVal: 100,
        };
      case 'requests':
        return {
          title: 'كثافة الطلبات المباشرة (Active RPS)',
          unit: 'req/s',
          color: '#38bdf8', // Sky
          gradientId: 'gradReq',
          getValue: (m: MetricPoint) => m.requests,
          maxVal: Math.max(...metrics.map((m) => m.requests)) * 1.15,
        };
      case 'latency':
        return {
          title: 'متوسط زمن الاستجابة (Avg Latency)',
          unit: 'ms',
          color: '#f59e0b', // Amber
          gradientId: 'gradLat',
          getValue: (m: MetricPoint) => m.latencyMs,
          maxVal: 100,
        };
    }
  };

  const config = getMetricConfig();

  // SVG Geometry calculations
  const width = 800;
  const height = 220;
  const paddingX = 40;
  const paddingY = 30;

  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  const points = displayedMetrics.map((m, idx) => {
    const val = config.getValue(m);
    const x = paddingX + (idx / (displayedMetrics.length - 1 || 1)) * chartWidth;
    const y = height - paddingY - (val / config.maxVal) * chartHeight;
    return { x, y, val, time: m.time, raw: m };
  });

  const pathD = points.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, '');

  const areaD =
    points.length > 0
      ? `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${
          height - paddingY
        } Z`
      : '';

  const activePoint = hoveredIndex !== null ? points[hoveredIndex] : points[points.length - 1];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
      {/* Chart Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 mb-1">
            <Activity className="w-4 h-4" />
            <span>المؤشرات البيانية الحية</span>
            <span aria-hidden="true">·</span>
            <span className="font-mono tabular-nums text-slate-300">
              القيمة الحالية: {activePoint?.val.toLocaleString()} {config.unit}
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-white">{config.title}</h3>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Metric Selector */}
          <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setSelectedMetric('cpu')}
              className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                selectedMetric === 'cpu'
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              المعالج CPU
            </button>
            <button
              onClick={() => setSelectedMetric('memory')}
              className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                selectedMetric === 'memory'
                  ? 'bg-emerald-600 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              الذاكرة RAM
            </button>
            <button
              onClick={() => setSelectedMetric('requests')}
              className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                selectedMetric === 'requests'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              الطلبات RPS
            </button>
            <button
              onClick={() => setSelectedMetric('latency')}
              className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                selectedMetric === 'latency'
                  ? 'bg-amber-600 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              زمن الاستجابة
            </button>
          </div>

          {/* Time range selector */}
          <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <Clock className="w-3.5 h-3.5 text-slate-500 mr-1.5 ml-1" />
            <button
              onClick={() => setTimeRange('24h')}
              className={`px-2 py-0.5 rounded text-[11px] ${
                timeRange === '24h' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              24س
            </button>
            <button
              onClick={() => setTimeRange('12h')}
              className={`px-2 py-0.5 rounded text-[11px] ${
                timeRange === '12h' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              12س
            </button>
            <button
              onClick={() => setTimeRange('6h')}
              className={`px-2 py-0.5 rounded text-[11px] ${
                timeRange === '6h' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              6س
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-52 sm:h-64 overflow-visible select-none"
        >
          <defs>
            <linearGradient id={config.gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={config.color} stopOpacity="0.4" />
              <stop offset="100%" stopColor={config.color} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Horizontal grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = height - paddingY - pct * chartHeight;
            const gridVal = Math.round(pct * config.maxVal);
            return (
              <g key={i}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#334155"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                  strokeOpacity="0.4"
                />
                <text
                  x={width - paddingX + 8}
                  y={y + 4}
                  fill="#94a3b8"
                  fontSize="10"
                  fontFamily="monospace"
                  textAnchor="start"
                >
                  {gridVal}
                </text>
              </g>
            );
          })}

          {/* Shaded Area */}
          <path d={areaD} fill={`url(#${config.gradientId})`} />

          {/* Line Stroke */}
          <path
            d={pathD}
            fill="none"
            stroke={config.color}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Data Points */}
          {points.map((pt, idx) => {
            const isHovered = hoveredIndex === idx;
            return (
              <g key={idx} className="cursor-pointer" onMouseEnter={() => setHoveredIndex(idx)}>
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? 6 : 3.5}
                  fill="#0f172a"
                  stroke={config.color}
                  strokeWidth={isHovered ? 3 : 2}
                  className="transition-all duration-150"
                />
                {/* Invisible larger hover target */}
                <rect
                  x={pt.x - 15}
                  y={paddingY}
                  width="30"
                  height={chartHeight}
                  fill="transparent"
                />
                {/* X-axis time label */}
                <text
                  x={pt.x}
                  y={height - 8}
                  fill="#94a3b8"
                  fontSize="11"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  {pt.time}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Details Floating Banner */}
        {activePoint && (
          <div className="mt-3 pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-400 font-mono">
            <span>التوقيت: {activePoint.time}</span>
            <span>المعالج: {activePoint.raw.cpu}%</span>
            <span>الذاكرة: {activePoint.raw.memory}%</span>
            <span>الطلبات: {activePoint.raw.requests.toLocaleString()} req/s</span>
            <span>الاستجابة: {activePoint.raw.latencyMs}ms</span>
          </div>
        )}
      </div>
    </div>
  );
};
