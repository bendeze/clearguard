import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, ShieldAlert, XCircle } from "lucide-react";
import { toast } from "sonner";

import { accountabilityApi } from "@/api/endpoints";
import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import type { PartnerVerifyTokenResponse } from "@/types/api";

export function PartnerVerifyPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialToken = searchParams.get("token") ?? "";

  const [tokenInput, setTokenInput] = React.useState(initialToken);
  const [verification, setVerification] =
    React.useState<PartnerVerifyTokenResponse | null>(null);
  const [loading, setLoading] = React.useState(initialToken.trim().length >= 16);
  const [submitting, setSubmitting] = React.useState(false);
  const [rejectionReason, setRejectionReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(
    initialToken && initialToken.trim().length < 16
      ? "Please enter a valid partner verification token (at least 16 characters)."
      : null,
  );

  const validateToken = React.useCallback(async (rawToken: string) => {
    const cleaned = rawToken.trim();
    if (cleaned.length < 16) {
      setVerification(null);
      setError("Please enter a valid partner verification token (at least 16 characters).");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await accountabilityApi.verifyToken(cleaned);
      setVerification(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to verify token.");
      setVerification(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    const cleaned = initialToken.trim();
    if (cleaned.length < 16) return;

    let active = true;
    accountabilityApi
      .verifyToken(cleaned)
      .then((res) => {
        if (!active) return;
        setVerification(res);
        setError(null);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Unable to verify token.");
        setVerification(null);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [initialToken]);

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ token: tokenInput.trim() });
    void validateToken(tokenInput);
  };

  const handleDecision = async (decision: "approve" | "reject") => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await accountabilityApi.partnerCosign({
        token: tokenInput.trim(),
        decision,
        rejection_reason:
          decision === "reject" && rejectionReason.trim()
            ? rejectionReason.trim()
            : null,
      });
      setVerification(res);
      toast.success(
        decision === "approve"
          ? "Deactivation request co-signed."
          : "Deactivation request rejected.",
      );
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to submit partner decision.";
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-muted/30 flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="size-5" />
              Accountability Partner Verification
            </CardTitle>
            <CardDescription>
              Review and co-sign a ClearGuard deactivation request using your one-time email verification token.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <form onSubmit={handleLookup} className="flex gap-2">
              <div className="flex-1 space-y-1">
                <Label htmlFor="partner-token" className="sr-only">
                  Verification Token
                </Label>
                <Input
                  id="partner-token"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Paste verification token..."
                  className="font-mono text-xs"
                />
              </div>
              <Button type="submit" variant="secondary" disabled={loading}>
                {loading ? <Loader2 className="size-4 animate-spin" /> : "Verify"}
              </Button>
            </form>

            {error ? (
              <Alert variant="destructive">
                <XCircle className="size-4" />
                <AlertTitle>Verification Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}

            {verification ? (
              <div className="space-y-4 rounded-lg border p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">Token Status</span>
                  {verification.valid ? (
                    <StatusBadge status={verification.status ?? "active"} />
                  ) : (
                    <StatusBadge status="unhealthy" />
                  )}
                </div>

                <p className="text-muted-foreground text-sm">
                  {verification.message}
                </p>

                {verification.valid ? (
                  <>
                    <div className="bg-muted/50 grid grid-cols-2 gap-3 rounded-md p-3 text-xs">
                      <div>
                        <p className="text-muted-foreground">Request ID</p>
                        <p className="mt-0.5 truncate font-mono font-medium">
                          {verification.request_id}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Cool-off Delay</p>
                        <p className="mt-0.5 font-medium">
                          {verification.cooloff_days} days
                        </p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-muted-foreground">Started At</p>
                        <p className="mt-0.5 font-medium">
                          {formatDateTime(verification.started_at)}
                        </p>
                      </div>
                    </div>

                    {verification.status === "pending_partner_approval" ? (
                      <div className="space-y-3 pt-1">
                        <div className="space-y-1.5">
                          <Label htmlFor="reject-reason" className="text-xs">
                            Rejection Reason (optional, used if rejecting)
                          </Label>
                          <Textarea
                            id="reject-reason"
                            rows={2}
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            placeholder="Optional note for why deactivation is denied..."
                          />
                        </div>

                        <div className="flex flex-col gap-2 sm:flex-row">
                          <Button
                            className="flex-1"
                            disabled={submitting}
                            onClick={() => void handleDecision("approve")}
                          >
                            <CheckCircle2 className="mr-2 size-4" />
                            Approve Co-Sign
                          </Button>
                          <Button
                            variant="destructive"
                            className="flex-1"
                            disabled={submitting}
                            onClick={() => void handleDecision("reject")}
                          >
                            <XCircle className="mr-2 size-4" />
                            Reject Request
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : null}
              </div>
            ) : null}
          </CardContent>

          <CardFooter className="justify-between border-t pt-4">
            <Link
              to="/login"
              className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-4"
            >
              Back to Admin Sign In
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
