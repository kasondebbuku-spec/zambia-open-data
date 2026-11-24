import Link from "next/link";

export default function NotFound() {
  return (
    <div className="card mx-auto max-w-lg p-6 text-center">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="mt-2 text-sm text-ink-2">We only have the budget books the council has published online.</p>
      <Link href="/budgets" className="mt-4 inline-block text-sm text-brand underline">
        See the budgets we have
      </Link>
    </div>
  );
}
