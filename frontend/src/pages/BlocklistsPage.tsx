import * as React from "react";
import { Link } from "react-router-dom";
import { type LegacyColumnDef } from "@tanstack/react-table/legacy";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAsyncData } from "@/hooks/useAsyncData";
import { formatDateTime } from "@/lib/format";
import type { BlocklistResponse } from "@/types/api";

export function BlocklistsPage() {
  const fetcher = React.useCallback(async () => {
    const res = await blocklistsApi.list(0, 200);
    return res.items;
  }, []);
  const { data, loading, error, reload } = useAsyncData(
    fetcher,
    "Failed to load blocklists.",
  );
  const blocklists = React.useMemo(() => data ?? [], [data]);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<BlocklistResponse | null>(null);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [isDefault, setIsDefault] = React.useState(false);
  const [isActive, setIsActive] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  const [deleteTarget, setDeleteTarget] =
    React.useState<BlocklistResponse | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const openCreate = () => {
    setEditing(null);
    setName("");
    setDescription("");
    setIsDefault(false);
    setIsActive(true);
    setFormOpen(true);
  };

  const openEdit = (item: BlocklistResponse) => {
    setEditing(item);
    setName(item.name);
    setDescription(item.description ?? "");
    setIsDefault(item.is_default);
    setIsActive(item.is_active);
    setFormOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await blocklistsApi.update(editing.id, {
          name: name.trim(),
          description: description.trim() || null,
          is_default: isDefault,
          is_active: isActive,
        });
        toast.success("Blocklist updated.");
      } else {
        await blocklistsApi.create({
          name: name.trim(),
          description: description.trim() || null,
          is_default: isDefault,
          is_active: isActive,
        });
        toast.success("Blocklist created.");
      }
      setFormOpen(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await blocklistsApi.remove(deleteTarget.id);
      toast.success(`Deleted blocklist "${deleteTarget.name}".`);
      setDeleteTarget(null);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  };

  const columns = React.useMemo<LegacyColumnDef<BlocklistResponse, unknown>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: ({ row }) => (
          <div>
            <Link
              to={`/blocklists/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {row.original.name}
            </Link>
            {row.original.is_default ? (
              <Badge variant="outline" className="ml-2 text-[10px]">
                Default
              </Badge>
            ) : null}
            {row.original.description ? (
              <p className="text-muted-foreground max-w-xs truncate text-xs">
                {row.original.description}
              </p>
            ) : null}
          </div>
        ),
      },
      {
        accessorKey: "current_version",
        header: "Version",
        cell: ({ row }) => (
          <Badge variant="secondary" className="font-mono">
            {row.original.current_version}
          </Badge>
        ),
      },
      {
        accessorKey: "domain_count",
        header: "Domains",
        cell: ({ row }) => row.original.domain_count.toLocaleString(),
      },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: ({ row }) => (
          <StatusBadge status={row.original.is_active ? "active" : "inactive"} />
        ),
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        cell: ({ row }) => (
          <span className="text-xs">
            {formatDateTime(row.original.updated_at)}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Button asChild size="sm" variant="outline">
              <Link to={`/blocklists/${row.original.id}`}>Manage</Link>
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => openEdit(row.original)}
              title="Edit metadata"
            >
              <Pencil className="size-4" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="text-destructive"
              onClick={() => setDeleteTarget(row.original)}
              title="Delete blocklist"
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Blocklists</h1>
          <p className="text-muted-foreground text-sm">
            Create filtering collections, ingest feeds, and publish SHA-256 releases.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void reload()}
            disabled={loading}
          >
            <RefreshCw className="mr-2 size-4" />
            Refresh
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="mr-2 size-4" />
            New Blocklist
          </Button>
        </div>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Error loading blocklists</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Registered Collections</CardTitle>
          <CardDescription>
            Click any blocklist name or Manage button to inspect domains, ingest raw feeds, or publish versions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={blocklists}
            searchPlaceholder="Filter blocklists..."
            emptyMessage={
              loading ? "Loading blocklists..." : "No blocklists registered."
            }
          />
        </CardContent>
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit Blocklist" : "Create Blocklist"}
            </DialogTitle>
            <DialogDescription>
              Configure filtering list metadata and activation status.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="bl-name">Name</Label>
              <Input
                id="bl-name"
                required
                minLength={2}
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="core-adult-filter"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="bl-desc">Description</Label>
              <Textarea
                id="bl-desc"
                maxLength={500}
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Primary adult content domain blocklist..."
              />
            </div>

            <div className="flex flex-col gap-3">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={isActive}
                  onCheckedChange={(checked) => setIsActive(Boolean(checked))}
                />
                <span>Active (included in client sync)</span>
              </label>

              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={isDefault}
                  onCheckedChange={(checked) => setIsDefault(Boolean(checked))}
                />
                <span>Default protection list</span>
              </label>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setFormOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : editing ? "Save Changes" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Blocklist?</DialogTitle>
            <DialogDescription>
              This permanently removes{" "}
              <span className="font-semibold text-foreground">
                {deleteTarget?.name}
              </span>{" "}
              and all of its release snapshots.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleDelete()}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
