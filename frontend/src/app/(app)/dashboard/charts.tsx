"use client";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, BarChart, Bar } from "recharts";

const DOT_STYLE = { r: 3 };
const SERIES_COLORS = ["#2D5134", "#D9A036", "#8B5E3C", "#4A7A8C", "#9B4D6B", "#5C8C3E"];

export function SilkTypeBarChart({ data }: { data: { silk_type_name: string; figs: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid stroke="#E6E4DF" strokeDasharray="3 3" />
        <XAxis dataKey="silk_type_name" stroke="#5C635B" fontSize={12} />
        <YAxis stroke="#5C635B" fontSize={12} />
        <Tooltip />
        <Bar dataKey="figs" fill="#2D5134" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function YieldTrendChart({ data }: { data: { month: string; planned: number; actual: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E6E4DF" />
        <XAxis dataKey="month" stroke="#5C635B" fontSize={12} />
        <YAxis stroke="#5C635B" fontSize={12} />
        <Tooltip />
        <Line type="monotone" dataKey="planned" stroke="#D9A036" strokeWidth={2} dot={DOT_STYLE} />
        <Line type="monotone" dataKey="actual" stroke="#2D5134" strokeWidth={2} dot={DOT_STYLE} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SingleTrendChart({ data, colorVar }: { data: { month: string; value: number }[]; colorVar: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E6E4DF" />
        <XAxis dataKey="month" stroke="#5C635B" fontSize={12} />
        <YAxis stroke="#5C635B" fontSize={12} />
        <Tooltip />
        <Line type="monotone" dataKey="value" stroke={colorVar} strokeWidth={2} dot={DOT_STYLE} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DistrictCompareBarChart({ data, colorVar }: { data: { name: string; value: number }[]; colorVar: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid stroke="#E6E4DF" strokeDasharray="3 3" />
        <XAxis dataKey="name" stroke="#5C635B" fontSize={11} angle={-20} textAnchor="end" height={60} />
        <YAxis stroke="#5C635B" fontSize={12} />
        <Tooltip />
        <Bar dataKey="value" fill={colorVar} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MultiSeriesTrendChart({ data, seriesKeys }: { data: Record<string, string | number>[]; seriesKeys: string[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E6E4DF" />
        <XAxis dataKey="label" stroke="#5C635B" fontSize={12} />
        <YAxis stroke="#5C635B" fontSize={12} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {seriesKeys.map((k, i) => (
          <Line key={k} type="monotone" dataKey={k} stroke={SERIES_COLORS[i % SERIES_COLORS.length]} strokeWidth={2} dot={DOT_STYLE} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
