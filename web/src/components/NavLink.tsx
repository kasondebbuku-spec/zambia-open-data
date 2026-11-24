"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const path = usePathname();
  const current = href === "/" ? path === "/" : path.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={current ? "page" : undefined}
      className={`rounded-md px-3 py-1.5 ${
        current ? "bg-brand-soft font-medium text-brand" : "text-ink-2 hover:bg-plane hover:text-ink"
      }`}
    >
      {children}
    </Link>
  );
}
