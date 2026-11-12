import { Badge } from "@/components/ui/badge";

const STATUS_STYLES: Record<
  string,
  {
    label: string;
    variant: "default" | "secondary" | "destructive" | "outline";
    className?: string;
  }
> = {
  healthy: {
    label: "Healthy",
    variant: "secondary",
    className:
      "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  },
  ready: {
    label: "Ready",
    variant: "secondary",
    className:
      "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  },
  connected: {
    label: "Connected",
    variant: "secondary",
    className:
      "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  },
  active: {
    label: "Active",
    variant: "secondary",
    className:
      "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  },
  inactive: {
    label: "Inactive",
    variant: "outline",
    className: "text-muted-foreground",
  },
  pending_partner_approval: {
    label: "Pending Partner",
    variant: "secondary",
    className:
      "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  },
  partner_approved: {
    label: "Partner Approved",
    variant: "secondary",
    className:
      "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30",
  },
  partner_rejected: {
    label: "Partner Rejected",
    variant: "destructive",
  },
  admin_overridden: {
    label: "Admin Overridden",
    variant: "default",
  },
  cancelled: {
    label: "Cancelled",
    variant: "outline",
    className: "text-muted-foreground",
  },
  completed: {
    label: "Completed",
    variant: "secondary",
  },
  unhealthy: {
    label: "Unhealthy",
    variant: "destructive",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const entry = STATUS_STYLES[normalized] ?? {
    label: status.replaceAll("_", " "),
    variant: "outline" as const,
  };

  return (
    <Badge variant={entry.variant} className={entry.className}>
      {entry.label}
    </Badge>
  );
}

