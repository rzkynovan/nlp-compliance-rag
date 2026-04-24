import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      retry: (failureCount, error: unknown) => {
        if (error instanceof Error && "status" in error) {
          const status = (error as { status: number }).status;
          if (status === 404 || status === 401) return false;
        }
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});