export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative flex min-h-svh items-center justify-center bg-muted/40 p-4">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60rem_30rem_at_50%_-10%,--theme(--color-primary/12%),transparent)]"
      />
      <div className="relative w-full max-w-sm">{children}</div>
    </main>
  );
}
