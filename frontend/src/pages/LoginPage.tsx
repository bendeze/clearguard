import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, Loader2, ShieldCheck } from "lucide-react";

import { DEFAULT_API_BASE_URL, getApiBaseUrl, setApiBaseUrl } from "@/api/client";
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
import { useAuth } from "@/context/AuthContext";

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [apiUrl, setApiUrl] = React.useState(getApiBaseUrl());
  const [showApiConfig, setShowApiConfig] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (user) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      setApiBaseUrl(apiUrl);
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to sign in. Check credentials.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-muted/30 flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4">
        <div className="flex flex-col items-center text-center">
          <div className="bg-primary text-primary-foreground mb-3 flex size-11 items-center justify-center rounded-xl shadow-sm">
            <ShieldCheck className="size-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            ClearGuard Admin
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Sign in with an administrator account to manage overrides &amp; blocklists
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Administrator Sign In</CardTitle>
            <CardDescription>
              Only users with <code className="font-mono text-xs">is_admin = true</code> can access the console.
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error ? (
                <Alert variant="destructive">
                  <AlertCircle className="size-4" />
                  <AlertTitle>Authentication failed</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowApiConfig((v) => !v)}
                  className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-4"
                >
                  {showApiConfig ? "Hide backend API URL" : "Configure backend API URL"}
                </button>
                {showApiConfig ? (
                  <div className="mt-2 space-y-1.5">
                    <Label htmlFor="apiUrl" className="text-xs">
                      API v1 Base URL
                    </Label>
                    <Input
                      id="apiUrl"
                      value={apiUrl}
                      onChange={(e) => setApiUrl(e.target.value)}
                      placeholder={DEFAULT_API_BASE_URL}
                      className="font-mono text-xs"
                    />
                  </div>
                ) : null}
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-3">
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign in to Console"
                )}
              </Button>
              <Link
                to="/verify"
                className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-4"
              >
                Are you an Accountability Partner? Verify a request here
              </Link>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}

