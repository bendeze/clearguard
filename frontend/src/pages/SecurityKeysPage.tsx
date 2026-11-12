import * as React from "react";
import { Check, Copy, KeyRound, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { adminApi } from "@/api/endpoints";
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
import { useAsyncData } from "@/hooks/useAsyncData";

export function SecurityKeysPage() {
  const fetcher = React.useCallback(() => adminApi.getPublicKey(), []);
  const { data, loading, error, reload } = useAsyncData(
    fetcher,
    "Failed to fetch public key.",
  );
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    if (!data?.public_key_pem) return;
    await navigator.clipboard.writeText(data.public_key_pem);
    setCopied(true);
    toast.success("Ed25519 public key copied to clipboard.");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Security Keys</h1>
          <p className="text-muted-foreground text-sm">
            Asymmetric Ed25519 verification key used by Android clients to verify emergency overrides offline.
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
          <AlertTitle>Error loading key</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="size-4" />
              Admin Verification Public Key
            </CardTitle>
            <CardDescription>
              Endpoint:{" "}
              <code className="font-mono text-xs">GET /api/v1/admin/public-key</code>
            </CardDescription>
          </div>
          {data ? <Badge variant="secondary">{data.algorithm}</Badge> : null}
        </CardHeader>
        <CardContent className="space-y-4">
          <pre className="bg-muted overflow-x-auto rounded-lg border p-4 font-mono text-xs leading-relaxed">
            {loading
              ? "Loading PEM key..."
              : (data?.public_key_pem ?? "Unavailable")}
          </pre>

          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleCopy()}
            disabled={!data?.public_key_pem}
          >
            {copied ? (
              <>
                <Check className="mr-2 size-4 text-emerald-500" />
                Copied
              </>
            ) : (
              <>
                <Copy className="mr-2 size-4" />
                Copy PEM Key
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
