
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  Clock3,
  Database,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import StatCard from "./components/StatCard";
import PipelineActivity from "./components/PipelineActivity";
import QuickActions from "./components/QuickActions";
import { getDashboardSummary } from "../../services/dashboard";
import type { DashboardSummary } from "../../types/dashboard";
import "./DashboardPage.css";

const numberFormatter = new Intl.NumberFormat();

function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getDashboardSummary();
      setSummary(data);
    } catch {
      setError("Unable to load dashboard metrics. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const statistics = [
    {
      label: "Pipeline runs",
      value: summary
        ? numberFormatter.format(summary.total_runs)
        : loading
          ? "..."
          : "—",
      description: "Total processing runs",
      icon: Activity,
      color: "bg-blue-50 text-blue-600",
    },
    {
      label: "Records processed",
      value: summary
        ? numberFormatter.format(summary.records_processed)
        : loading
          ? "..."
          : "—",
      description: "Across all executions",
      icon: Database,
      color: "bg-teal-50 text-teal-700",
    },
    {
      label: "Successful runs",
      value: summary
        ? numberFormatter.format(summary.successful_runs)
        : loading
          ? "..."
          : "—",
      description: "Completed successfully",
      icon: ShieldCheck,
      color: "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Pending executions",
      value: summary
        ? numberFormatter.format(summary.pending_executions)
        : loading
          ? "..."
          : "—",
      description: "Currently running",
      icon: Clock3,
      color: "bg-orange-50 text-orange-700",
    },
  ];

  return (
    <>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm text-slate-500">
            Welcome to your financial data workspace.
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Dashboard overview
          </h1>
        </div>

        <Link
          to="/ingestion"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700"
        >
          <ArrowDownToLine size={17} />
          Upload financial data
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-7 flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="font-semibold hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {statistics.map((statistic) => (
          <StatCard key={statistic.label} {...statistic} />
        ))}
      </div>

      <div className="mt-7 grid gap-6 xl:grid-cols-3">
        <PipelineActivity />
        <QuickActions />
      </div>

      <div className="mt-6 rounded-xl bg-[#101c35] p-6 text-white sm:flex sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-teal-400/15 p-3 text-teal-300">
            <Zap size={22} />
          </div>

          <div>
            <h3 className="font-semibold">
              Your financial data, organized.
            </h3>
            <p className="mt-1 max-w-xl text-xs leading-5 text-slate-400">
              Hazina provides structured ingestion, validation,
              deduplication and monitoring for your financial data.
            </p>
          </div>
        </div>

        <span className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-teal-300 sm:mt-0">
          <ShieldCheck size={16} />
          Organization-aware processing
        </span>
      </div>
    </>
  );
}

export default DashboardPage;
