import * as React from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Database,
  ListFilter,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { adminApi, blocklistsApi, healthApi } from "@/api/endpoints";
import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useAsyncData } from "@/hooks/useAsyncData";
import { computeCooloffMetrics, formatDateTime } from "@/lib/format";

const blocklistChartConfig = {
  domain_count: {
    label: "Domains",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

const cooloffChartConfig = {
  elapsedDays: {
    label: "Elapsed Days",
    color: "var(--chart-2)",
  },
  remainingDays: {
    label: "Remaining Days",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig;

export function DashboardPage() {
  const fetcher = React.useCallback(async () => {
    const [health, readiness, pending, blocklistsPage] = await Promise.all([
      healthApi.getHealth(),
      healthApi.getReadiness(),
      adminApi.listPendingOverrides(),
      blocklistsApi.list(0, 50),
    ]);
    return {
      health,
      readiness,
      pending,
      blocklists: blocklistsPage.items,
    };
  }, []);

  const { data, loading, error, reload } = useAsyncData(
    fetcher,
    "Failed to load dashboard overview.",
  );

  const health = data?.health ?? null;
  const readiness = data?.readiness ?? null;
  const pending = React.useMemo(() => data?.pending ?? [], [data?.pending]);
  const blocklists = React.useMemo(
    () => data?.blocklists ?? [],
    [data?.blocklists],
  );

  const totalDomains = React.useMemo(
    () => blocklists.reduce((sum, item) => sum + item.domain_count, 0),
    [blocklists],
  );

  const blocklistChartData = React.useMemo(
    () =>
      blocklists.slice(0, 8).map((item) => ({
        name:
          item.name.length > 14 ? `${item.name.slice(0, 14)}…` : item.name,
        domain_count: item.domain_count,
      })),
    [blocklists],
  );

  const cooloffChartData = React.useMemo(
    () =>
      pending.slice(0, 8).map((item) => {
        const metrics = computeCooloffMetrics(item.started_at, item.cooloff_days);
        return {
          username: item.username,
          elapsedDays: metrics.elapsedDays,
          remainingDays: metrics.remainingDays,
        };
      }),
    [pending],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="text-muted-foreground text-sm">
            Real-time service health, accountability countdowns, and blocklist telemetry.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void reload()}
          disabled={loading}
        >
          <RefreshCw className="mr-2 size-4" />
          Refresh
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Failed to load telemetry</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">API Service</CardTitle>
            <Activity className="text-muted-foreground size-4" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <StatusBadge status={health?.status ?? "unhealthy"} />
              <span className="font-mono text-xs text-muted-foreground">
                v{health?.version ?? "—"}
              </span>
            </div>
            <p className="text-muted-foreground mt-2 text-xs">
              Env: <span className="font-medium">{health?.environment ?? "—"}</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Database</CardTitle>
            <Database className="text-muted-foreground size-4" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <StatusBadge
                status={
                  readiness?.database === "connected" ? "connected" : "unhealthy"
                }
              />
            </div>
            <p className="text-muted-foreground mt-2 truncate text-xs">
              Checked {formatDateTime(readiness?.timestamp)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Overrides
            </CardTitle>
            <ShieldAlert className="text-muted-foreground size-4" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pending.length}</div>
            <Link
              to="/overrides"
              className="text-primary mt-1 inline-flex items-center text-xs hover:underline"
            >
              Review queue
              <ArrowRight className="ml-1 size-3" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Active Blocklists
            </CardTitle>
            <ListFilter className="text-muted-foreground size-4" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{blocklists.length}</div>
            <p className="text-muted-foreground mt-1 text-xs">
              {totalDomains.toLocaleString()} total indexed domains
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Domains per Blocklist</CardTitle>
            <CardDescription>
              Published domain counts across registered filtering collections
            </CardDescription>
          </CardHeader>
          <CardContent>
            {blocklistChartData.length ? (
              <ChartContainer
                config={blocklistChartConfig}
                className="h-64 w-full"
              >
                <BarChart data={blocklistChartData} accessibilityLayer>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                  />
                  <YAxis tickLine={false} axisLine={false} width={48} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="domain_count"
                    fill="var(--color-domain_count)"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="text-muted-foreground flex h-64 items-center justify-center text-sm">
                No blocklists created yet.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>60-Day Deactivation Countdowns</CardTitle>
            <CardDescription>
              Elapsed vs. remaining cool-off days for active deactivation requests
            </CardDescription>
          </CardHeader>
          <CardContent>
            {cooloffChartData.length ? (
              <ChartContainer
                config={cooloffChartConfig}
                className="h-64 w-full"
              >
                <BarChart data={cooloffChartData} accessibilityLayer>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="username"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                  />
                  <YAxis tickLine={false} axisLine={false} width={40} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ChartLegend content={<ChartLegendContent />} />
                  <Bar
                    dataKey="elapsedDays"
                    stackId="a"
                    fill="var(--color-elapsedDays)"
                    radius={[0, 0, 4, 4]}
                  />
                  <Bar
                    dataKey="remainingDays"
                    stackId="a"
                    fill="var(--color-remainingDays)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="text-muted-foreground flex h-64 items-center justify-center text-sm">
                No active deactivation requests pending.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Pending Queue Preview */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Pending Override Requests</CardTitle>
            <CardDescription>
              Users currently inside the mandatory cool-off or partner approval window
            </CardDescription>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/overrides">Manage All</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {pending.length ? (
            <div className="divide-y">
              {pending.slice(0, 5).map((item) => {
                const { remainingDays } = computeCooloffMetrics(
                  item.started_at,
                  item.cooloff_days,
                );
                return (
                  <div
                    key={item.request_id}
                    className="flex flex-col justify-between gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center"
                  >
                    <div className="space-y-0.5">
                      <p className="text-sm font-medium">{item.username}</p>
                      <p className="text-muted-foreground text-xs">
                        Partner: {item.partner_email} &bull; Started{" "}
                        {formatDateTime(item.started_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">
                        {remainingDays}d remaining
                      </span>
                      <StatusBadge status={item.status} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">
              No active requests awaiting review.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
