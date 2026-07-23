"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export function ProductProductionChart({ data }: { data: { product?: string; planned: number; actual: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid stroke="#E6E4DF" strokeDasharray="3 3" />
        <XAxis dataKey="product" stroke="#5C635B" fontSize={11} angle={-12} dy={8} height={50} />
        <YAxis stroke="#5C635B" fontSize={11} />
        <Tooltip /><Legend />
        <Bar dataKey="planned" fill="#D9A036" />
        <Bar dataKey="actual" fill="#2D5134" />
      </BarChart>
    </ResponsiveContainer>
  );
}
