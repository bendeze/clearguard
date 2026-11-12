import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { type LegacyColumnDef } from "@tanstack/react-table/legacy";
import {
  ArrowLeft,
  History,
  Rocket,
  RotateCcw,
  Trash2,
  Upload,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { toast } from "sonner";

import { blocklistsApi } from "@/api/endpoints";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useAsyncData } from "@/hooks/useAsyncData";
import { formatDateTime } from "@/lib/format";
import type {
  BlocklistVersionResponse,
  DomainCategory,
  DomainResponse,
  FeedIngestResponse,
} from "@/types/api";

const ingestChartConfig = {
  count: {
    label: "Count",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

const versionChartConfig = {
  domain_count: {
    label: "Domains",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig;

export function BlocklistDetailPage() {
  const { id } = useParams<{ id: string }>();

  const fetcher = React.useCallback(async () => {
    if (!id) throw new Error("Missing blocklist ID.");
    const [blocklist, domRes, verRes] = await Promise.all([
      blocklistsApi.getById(id),
      blocklistsApi.listDomains(id, 0, 500),
      blocklistsApi.listVersions(id, 0, 100),
    ]);
    return {
      blocklist,
      domains: domRes.items,
      domainsTotal: domRes.total,
      versions: verRes.items,
    };
  }, [id]);

  const { data, loading, error, reload } = useAsyncData(
    fetcher,
    "Failed to load blocklist details.",
  );

  const blocklist = data?.blocklist ?? null;
  const domains = React.useMemo(() => data?.domains ?? [], [data?.domains]);
  const domainsTotal = data?.domainsTotal ?? 0;
  const versions = React.useMemo(() => data?.versions ?? [], [data?.versions]);

  const [selectedDomainIds, setSelectedDomainIds] = React.useState<Set<string>>(
    () => new Set(),
  );
  const [removingDomains, setRemovingDomains] = React.useState(false);

  // Feed ingest state
  const [feedContent, setFeedContent] = React.useState("");
  const [feedSource, setFeedSource] = React.useState("admin_console");
  const [feedCategory, setFeedCategory] =
    React.useState<DomainCategory>("pornography");
  const [ingesting, setIngesting] = React.useState(false);
  const [ingestResult, setIngestResult] =
    React.useState<FeedIngestResponse | null>(null);

  // Publish modal state
  const [publishOpen, setPublishOpen] = React.useState(false);
  const [pubVersion, setPubVersion] = React.useState("");
  const [pubChangelog, setPubChangelog] = React.useState("");
  const [pubForce, setPubForce] = React.useState(false);
  const [publishing, setPublishing] = React.useState(false);

  // Rollback modal state
  const [rollbackTarget, setRollbackTarget] =
    React.useState<BlocklistVersionResponse | null>(null);
  const [rollbackReason, setRollbackReason] = React.useState("");
  const [rollingBack, setRollingBack] = React.useState(false);

  const toggleDomain = (domainId: string, checked: boolean) => {
    setSelectedDomainIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(domainId);
      else next.delete(domainId);
      return next;
    });
  };

  const handleRemoveSelectedDomains = async () => {
    if (!id || selectedDomainIds.size === 0) return;
    setRemovingDomains(true);
    try {
      const res = await blocklistsApi.removeDomains(
        id,
        Array.from(selectedDomainIds),
      );
      setSelectedDomainIds(new Set());
      toast.success(`Removed ${res.removed} domain(s) from blocklist.`);
      await reload();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to remove domains.",
      );
    } finally {
      setRemovingDomains(false);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !feedContent.trim()) return;
    setIngesting(true);
    try {
      const res = await blocklistsApi.ingestFeed(id, {
        content: feedContent,
        source: feedSource.trim() || "admin_console",
        category: feedCategory,
      });
      setIngestResult(res);
      toast.success(
        `Ingested ${res.parsed_count} entries (${res.domains_associated} associated).`,
      );
      setFeedContent("");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Feed ingestion failed.");
    } finally {
      setIngesting(false);
    }
  };

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setPublishing(true);
    try {
      const res = await blocklistsApi.publishVersion(id, {
        version: pubVersion.trim() || null,
        changelog: pubChangelog.trim() || null,
        force: pubForce,
      });
      toast.success(`Published version ${res.version}.`);
      setPublishOpen(false);
      setPubVersion("");
      setPubChangelog("");
      setPubForce(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Publish failed.");
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !rollbackTarget) return;
    setRollingBack(true);
    try {
      const res = await blocklistsApi.rollbackVersion(id, {
        target_version: rollbackTarget.version,
        reason: rollbackReason.trim() || null,
      });
      toast.success(`Rolled back active version to ${res.version}.`);
      setRollbackTarget(null);
      setRollbackReason("");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Rollback failed.");
    } finally {
      setRollingBack(false);
    }
  };

  const domainColumns = React.useMemo<LegacyColumnDef<DomainResponse, unknown>[]>(
    () => [
      {
        id: "select",
        header: () => <span className="sr-only">Select</span>,
        enableSorting: false,
        cell: ({ row }) => (
          <Checkbox
            checked={selectedDomainIds.has(row.original.id)}
            onCheckedChange={(checked) =>
              toggleDomain(row.original.id, Boolean(checked))
            }
          />
        ),
      },
      {
        accessorKey: "domain",
        header: "Domain",
        cell: ({ row }) => (
          <span className="font-mono text-xs font-medium">
            {row.original.domain}
          </span>
        ),
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: ({ row }) => (
          <Badge variant="outline" className="capitalize">
            {row.original.category}
          </Badge>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "source",
        header: "Source",
      },
    ],
    [selectedDomainIds],
  );

  const versionColumns = React.useMemo<
    LegacyColumnDef<BlocklistVersionResponse, unknown>[]
  >(
    () => [
      {
        accessorKey: "version",
        header: "Version",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="font-mono">
              {row.original.version}
            </Badge>
            {blocklist?.current_version === row.original.version ? (
              <Badge>Active</Badge>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "domain_count",
        header: "Domains",
        cell: ({ row }) => row.original.domain_count.toLocaleString(),
      },
      {
        accessorKey: "content_hash",
        header: "SHA-256",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-muted-foreground">
            {row.original.content_hash.slice(0, 16)}...
          </span>
        ),
      },
      {
        accessorKey: "changelog",
        header: "Changelog",
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground">
            {row.original.changelog || "—"}
          </span>
        ),
      },
      {
        accessorKey: "created_at",
        header: "Released",
        cell: ({ row }) => (
          <span className="text-xs">
            {formatDateTime(row.original.created_at)}
          </span>
        ),
      },
      {
        id: "rollback",
        header: "Action",
        enableSorting: false,
        cell: ({ row }) => (
          <Button
            size="sm"
            variant="outline"
            disabled={blocklist?.current_version === row.original.version}
            onClick={() => {
              setRollbackTarget(row.original);
              setRollbackReason("");
            }}
          >
            <RotateCcw className="mr-1.5 size-3.5" />
            Rollback
          </Button>
        ),
      },
    ],
    [blocklist?.current_version],
  );

  const versionChartData = React.useMemo(
    () =>
      [...versions]
        .reverse()
        .slice(-10)
        .map((v) => ({
          version: v.version,
          domain_count: v.domain_count,
        })),
    [versions],
  );

  const ingestChartData = React.useMemo(() => {
    if (!ingestResult) return [];
    return [
      { metric: "Parsed", count: ingestResult.parsed_count },
      { metric: "New Domains", count: ingestResult.new_domains_created },
      { metric: "Associated", count: ingestResult.domains_associated },
    ];
  }, [ingestResult]);

  if (loading && !blocklist) {
    return (
      <div className="text-muted-foreground py-12 text-center text-sm">
        Loading blocklist workspace...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <Link
            to="/blocklists"
            className="text-muted-foreground hover:text-foreground inline-flex items-center text-xs"
          >
            <ArrowLeft className="mr-1 size-3.5" />
            Back to Blocklists
          </Link>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight">
              {blocklist?.name ?? "Blocklist"}
            </h1>
            {blocklist ? (
              <Badge variant="secondary" className="font-mono">
                v{blocklist.current_version}
              </Badge>
            ) : null}
          </div>
          {blocklist?.description ? (
            <p className="text-muted-foreground text-sm">
              {blocklist.description}
            </p>
          ) : null}
        </div>

        <Button onClick={() => setPublishOpen(true)}>
          <Rocket className="mr-2 size-4" />
          Publish Version
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Error loading blocklist</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Tabs defaultValue="domains" className="space-y-4">
        <TabsList>
          <TabsTrigger value="domains">
            Domains ({domainsTotal.toLocaleString()})
          </TabsTrigger>
          <TabsTrigger value="ingest">
            <Upload className="mr-1.5 size-3.5" />
            Ingest Feed
          </TabsTrigger>
          <TabsTrigger value="versions">
            <History className="mr-1.5 size-3.5" />
            Versions ({versions.length})
          </TabsTrigger>
        </TabsList>

        {/* Domains Tab */}
        <TabsContent value="domains">
          <Card>
            <CardHeader>
              <CardTitle>Associated Domains</CardTitle>
              <CardDescription>
                Showing up to 500 associated domains. Select rows to disassociate them from this list.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={domainColumns}
                data={domains}
                searchPlaceholder="Filter domain names..."
                emptyMessage="No domains associated yet. Use Ingest Feed to add rules."
                toolbarExtra={
                  selectedDomainIds.size > 0 ? (
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={removingDomains}
                      onClick={() => void handleRemoveSelectedDomains()}
                    >
                      <Trash2 className="mr-1.5 size-3.5" />
                      Remove Selected ({selectedDomainIds.size})
                    </Button>
                  ) : null
                }
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Feed Ingest Tab */}
        <TabsContent value="ingest" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ingest Raw Blocklist Feed</CardTitle>
              <CardDescription>
                Paste Hosts (<code className="font-mono text-xs">0.0.0.0 example.com</code>), Adblock (<code className="font-mono text-xs">||example.com^</code>), or plain domain lines.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleIngest} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="feed-source">Feed Source Tag</Label>
                    <Input
                      id="feed-source"
                      value={feedSource}
                      onChange={(e) => setFeedSource(e.target.value)}
                      placeholder="stevenblack_hosts"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select
                      value={feedCategory}
                      onValueChange={(v) =>
                        setFeedCategory(v as DomainCategory)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pornography">Pornography</SelectItem>
                        <SelectItem value="explicit">Explicit</SelectItem>
                        <SelectItem value="erotica">Erotica</SelectItem>
                        <SelectItem value="malware">Malware</SelectItem>
                        <SelectItem value="unspecified">Unspecified</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="feed-content">Raw Feed Content</Label>
                  <Textarea
                    id="feed-content"
                    rows={10}
                    required
                    value={feedContent}
                    onChange={(e) => setFeedContent(e.target.value)}
                    placeholder={"0.0.0.0 example.com\n||adult.example.org^"}
                    className="font-mono text-xs"
                  />
                </div>

                <Button type="submit" disabled={ingesting}>
                  <Upload className="mr-2 size-4" />
                  {ingesting ? "Ingesting Feed..." : "Parse & Associate Domains"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {ingestResult ? (
            <Card>
              <CardHeader>
                <CardTitle>Last Ingestion Breakdown</CardTitle>
                <CardDescription>
                  Total domains in blocklist:{" "}
                  {ingestResult.total_blocklist_domains.toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={ingestChartConfig}
                  className="h-52 w-full"
                >
                  <BarChart data={ingestChartData} accessibilityLayer>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="metric" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar
                      dataKey="count"
                      fill="var(--color-count)"
                      radius={[6, 6, 0, 0]}
                    />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>
          ) : null}
        </TabsContent>

        {/* Versions Tab */}
        <TabsContent value="versions" className="space-y-4">
          {versionChartData.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Release Growth History</CardTitle>
                <CardDescription>
                  Domain counts recorded across published snapshots
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={versionChartConfig}
                  className="h-52 w-full"
                >
                  <BarChart data={versionChartData} accessibilityLayer>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="version" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar
                      dataKey="domain_count"
                      fill="var(--color-domain_count)"
                      radius={[6, 6, 0, 0]}
                    />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Published Snapshots</CardTitle>
              <CardDescription>
                Immutable SHA-256 verified versions available for client sync and rollback.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={versionColumns}
                data={versions}
                searchPlaceholder="Search version or changelog..."
                emptyMessage="No versions published yet."
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Publish Dialog */}
      <Dialog open={publishOpen} onOpenChange={setPublishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Publish New Blocklist Version</DialogTitle>
            <DialogDescription>
              Compiles active domains, computes a SHA-256 content hash, and updates clients on next sync.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handlePublish} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="pub-ver">Semantic Version (optional)</Label>
              <Input
                id="pub-ver"
                value={pubVersion}
                onChange={(e) => setPubVersion(e.target.value)}
                placeholder="Leave blank to auto-increment"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pub-notes">Changelog (optional)</Label>
              <Textarea
                id="pub-notes"
                rows={3}
                value={pubChangelog}
                onChange={(e) => setPubChangelog(e.target.value)}
                placeholder="Added weekly community feed updates..."
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={pubForce}
                onCheckedChange={(checked) => setPubForce(Boolean(checked))}
              />
              <span>Force publish even with empty domain warnings</span>
            </label>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setPublishOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={publishing}>
                {publishing ? "Publishing..." : "Publish Release"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Rollback Dialog */}
      <Dialog
        open={Boolean(rollbackTarget)}
        onOpenChange={(open) => {
          if (!open) setRollbackTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Rollback to v{rollbackTarget?.version}?
            </DialogTitle>
            <DialogDescription>
              Reverts the active release pointer back to snapshot{" "}
              <code className="font-mono">{rollbackTarget?.version}</code>.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleRollback} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rb-reason">Operational Reason (optional)</Label>
              <Textarea
                id="rb-reason"
                rows={3}
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                placeholder="False positive domain reported in latest release..."
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setRollbackTarget(null)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={rollingBack}>
                {rollingBack ? "Rolling back..." : "Confirm Rollback"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
