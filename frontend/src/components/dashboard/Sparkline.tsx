"use client";

import { useMemo, type SVGProps } from "react";
import { cn } from "@/lib/utils";

export interface SparklineProps extends Omit<SVGProps<SVGSVGElement>, "data" | "fill"> {
  /** Array of numeric values to plot */
  data: readonly number[];
  /** Width of the sparkline */
  width?: number;
  /** Height of the sparkline */
  height?: number;
  /** Stroke color */
  stroke?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Whether to fill the area under the line */
  showFill?: boolean;
  /** Fill color (defaults to stroke with opacity) */
  fillColor?: string;
  /** Whether to show a dot at the last data point */
  showEndDot?: boolean;
  /** Trend direction for color styling */
  trend?: "up" | "down" | "neutral";
}

/**
 * A simple inline SVG sparkline chart.
 * Displays a small line chart for visualizing trends.
 */
export function Sparkline({
  data,
  width = 80,
  height = 24,
  stroke,
  strokeWidth = 1.5,
  showFill = true,
  fillColor,
  showEndDot = true,
  trend = "neutral",
  className,
  ...props
}: SparklineProps) {
  const { path, fillPath, lastPoint } = useMemo(() => {
    if (!data.length) {
      return { path: "", fillPath: "", lastPoint: null };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const points = data.map((value, index) => {
      const x = padding + (index / (data.length - 1 || 1)) * chartWidth;
      const y = padding + chartHeight - ((value - min) / range) * chartHeight;
      return { x, y };
    });

    const linePath = points
      .map((point, index) => (index === 0 ? `M ${point.x} ${point.y}` : `L ${point.x} ${point.y}`))
      .join(" ");

    const lastPt = points[points.length - 1];
    const firstPt = points[0];
    const areaPath =
      points.length > 0 && lastPt && firstPt
        ? `${linePath} L ${lastPt.x} ${height - padding} L ${firstPt.x} ${height - padding} Z`
        : "";

    return {
      path: linePath,
      fillPath: areaPath,
      lastPoint: lastPt ?? null,
    };
  }, [data, width, height]);

  const strokeColor = useMemo(() => {
    if (stroke) return stroke;
    switch (trend) {
      case "up":
        return "var(--color-success)";
      case "down":
        return "var(--color-error)";
      default:
        return "var(--color-primary)";
    }
  }, [stroke, trend]);

  const computedFillColor = fillColor ?? `${strokeColor}`;

  if (!data.length) {
    return (
      <svg
        width={width}
        height={height}
        className={cn("text-[var(--color-muted)]", className)}
        aria-label="No data available"
        role="img"
        {...props}
      >
        <line
          x1={2}
          y1={height / 2}
          x2={width - 2}
          y2={height / 2}
          stroke="currentColor"
          strokeWidth={1}
          strokeDasharray="4 2"
          opacity={0.3}
        />
      </svg>
    );
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label={`Sparkline chart showing ${data.length} data points`}
      {...props}
    >
      {showFill && <path d={fillPath} fill={computedFillColor} opacity={0.15} />}
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showEndDot && lastPoint && (
        <circle cx={lastPoint.x} cy={lastPoint.y} r={2.5} fill={strokeColor} />
      )}
    </svg>
  );
}

export interface SparklineSkeletonProps {
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Skeleton loader for Sparkline component.
 */
export function SparklineSkeleton({ width = 80, height = 24, className }: SparklineSkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded bg-[var(--color-card-hover)]", className)}
      style={{ width, height }}
    />
  );
}
