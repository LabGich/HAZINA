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
import "./DashboardPage.css";

const statistics = [
  {
    label: "Pipeline runs",
    value: "—",
    description: "Total processing runs",
    icon: Activity,
    color: "bg-blue-50 text-blue-600",
  },
  {
    label: "Records processed",
    value: "—",
    description: "Across all executions",
    icon: Database,
    color: "bg-teal-50 text-teal-700",
  },
  {
    label: "Successful runs",
    value: "—",
    description: "Completed successfully",
    icon: ShieldCheck,
    color: "bg-emerald-50 text-emerald-700",
  },
  {
    label: "Pending executions",
    value: "—",
    description: "Awaiting completion",
    icon: Clock3,
    color: "bg-orange-50 text-orange-700",
  },
];

function DashboardPage() {
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

      <div className="mb-7 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
        <Clock3 size={16} />
        Preview mode — live organization data will appear after API integration.
      </div>

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
            <h3 className="font-semibold">Your financial data, organized.</h3>
            <p className="mt-1 max-w-xl text-xs leading-5 text-slate-400">
              Hazina provides structured ingestion, validation, deduplication
              and monitoring for your financial data.
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
