"use client";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="card mx-auto max-w-lg p-6 text-center">
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      <p className="mt-2 text-sm text-ink-2">
        {error.message.includes("data service")
          ? error.message
          : "We couldn't load this page. Please try again in a minute."}
      </p>
      <button onClick={reset} className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white dark:text-black">
        Try again
      </button>
    </div>
  );
}
