import * as React from "react";
import { type LegacyColumnDef } from "@tanstack/react-table/legacy";
import { Check, Copy, RefreshCw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { adminApi } from "@/api/endpoints";
import { DataTable } from "@/components/DataTable";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAsyncData } from "@/hooks/useAsyncData";
import { computeCooloffMetrics, formatDateTime } from "@/lib/format";
import type {
  AdminOverrideResponse,
  AdminPendingRequestItem,
} from "@/types/api";

export function OverridesPage() {
  const fetcher = React.useCallback(
    () => adminApi.listPendingOverrides(),
    [],
  );
  const { data, loading, error, reload } = useAsyncData(
    fetcher,
    "Failed to fetch override queue.",
  );
  const requests = React.useMemo(() => data ?? [], [data]);

  const [selected, setSelected] =
    React.useState<AdminPendingRequestItem | null>(null);
  const [reason, setReason] = React.useState("");
  const [approving, setApproving] = React.useState(false);

  const [issuedCertificate, setIssuedCertificate] =
    React.useState<AdminOverrideResponse | null>(null);
  const [copiedToken, setCopiedToken] = React.useState(false);

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;

    const trimmed = reason.trim();
    if (trimmed.length < 10) {
      toast.error("Justification must be at least 10 characters.");
      return;
    }

    setApproving(true);
    try {
      const response = await adminApi.approveOverride({
        request_id: selected.request_id,
        reason: trimmed,
      });
      setIssuedCertificate(response);
      setSelected(null);
      setReason("");
      toast.success("Emergency Ed25519 override certificate issued.");
      await reload();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to issue override.",
      );
    } finally {
      setApproving(false);
    }
  };

  const handleCopyToken = async () => {
    if (!issuedCertificate) return;
    await navigator.clipboard.writeText(issuedCertificate.signed_token);
    setCopiedToken(true);
    toast.success("Signed override certificate copied.");
    setTimeout(() => setCopiedToken(false), 2000);
  };

  const columns = React.useMemo<
    LegacyColumnDef<AdminPendingRequestItem, unknown>[]
  >(
    () => [
      {
        accessorKey: "username",
        header: "User",
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.username}</p>
            <p className="text-muted-foreground font-mono text-[11px]">
              {row.original.request_id.slice(0, 8)}...
            </p>
          </div>
        ),
      },
      {
        accessorKey: "partner_email",
        header: "Trusted Partner",
      },
      {
        accessorKey: "started_at",
        header: "Started",
        cell: ({ row }) => (
          <span className="text-xs">
            {formatDateTime(row.original.started_at)}
          </span>
        ),
      },
      {
        id: "countdown",
        header: "Countdown",
        cell: ({ row }) => {
          const { remainingDays, elapsedDays } = computeCooloffMetrics(
            row.original.started_at,
            row.original.cooloff_days,
          );
          return (
            <div className="text-xs">
              <span className="font-medium">{remainingDays}d left</span>{" "}
              <span className="text-muted-foreground">
                ({elapsedDays}/{row.original.cooloff_days}d)
              </span>
            </div>
          );
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "actions",
        header: "Action",
        enableSorting: false,
        cell: ({ row }) => (
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setSelected(row.original);
              setReason("");
            }}
          >
            <ShieldCheck className="mr-1.5 size-3.5" />
            Approve Override
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Emergency Overrides
          </h1>
          <p className="text-muted-foreground text-sm">
            Review active 60-day deactivation requests and issue Ed25519 signed early-release tokens.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void reload()}
          disabled={loading}
        >
          <RefreshCw className="mr-2 size-4" />
          Refresh Queue
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Error loading override requests</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Pending Deactivation Queue</CardTitle>
          <CardDescription>
            Requests in <code className="font-mono text-xs">pending_partner_approval</code> or{" "}
            <code className="font-mono text-xs">partner_approved</code> state.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={requests}
            searchPlaceholder="Search by username or partner email..."
            emptyMessage={
              loading
                ? "Loading pending requests..."
                : "No pending deactivation requests."
            }
          />
        </CardContent>
      </Card>

      {/* Approve Override Dialog */}
      <Dialog
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Issue Emergency Override</DialogTitle>
            <DialogDescription>
              This signs an immutable Ed25519 certificate for{" "}
              <span className="font-semibold text-foreground">
                {selected?.username}
              </span>{" "}
              and marks their deactivation request as overridden.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleApprove} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="override-reason">
                Audit Justification (10–1000 chars)
              </Label>
              <Textarea
                id="override-reason"
                required
                minLength={10}
                maxLength={1000}
                rows={4}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Document verified identity check or emergency support approval reason..."
              />
              <p className="text-muted-foreground text-xs">
                {reason.trim().length} / 1000 characters
              </p>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setSelected(null)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={approving}>
                {approving ? "Signing Token..." : "Sign & Approve"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Issued Certificate Dialog */}
      <Dialog
        open={Boolean(issuedCertificate)}
        onOpenChange={(open) => {
          if (!open) setIssuedCertificate(null);
        }}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Signed Override Certificate Issued</DialogTitle>
            <DialogDescription>
              Issued at {formatDateTime(issuedCertificate?.issued_at)}. Provide this signed certificate payload if offline client entry is needed.
            </DialogDescription>
          </DialogHeader>

          <pre className="bg-muted max-h-64 overflow-auto rounded-lg border p-3 font-mono text-xs break-all whitespace-pre-wrap">
            {issuedCertificate?.signed_token}
          </pre>

          <DialogFooter>
            <Button variant="outline" onClick={() => void handleCopyToken()}>
              {copiedToken ? (
                <>
                  <Check className="mr-2 size-4 text-emerald-500" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="mr-2 size-4" />
                  Copy Signed Token
                </>
              )}
            </Button>
            <Button onClick={() => setIssuedCertificate(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
