import * as React from "react";

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  fallbackError: string,
) {
  const [data, setData] = React.useState<T | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const mountedRef = React.useRef(true);

  React.useEffect(() => {
    mountedRef.current = true;
    let active = true;

    fetcher()
      .then((res) => {
        if (!active) return;
        setData(res);
        setError(null);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : fallbackError);
        setLoading(false);
      });

    return () => {
      active = false;
      mountedRef.current = false;
    };
  }, [fetcher, fallbackError]);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetcher();
      if (mountedRef.current) {
        setData(res);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : fallbackError);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetcher, fallbackError]);

  return { data, loading, error, reload };
}

