import type { Metadata } from "next";
import Link from "next/link";
import { NavLink } from "@/components/NavLink";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Zambia Open Data: Lusaka's budget, line by line", template: "%s · Zambia Open Data" },
  description:
    "Where Lusaka City Council's money comes from and where it goes, plus its Constituency Development Fund projects, from the council's own published documents.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/budgets", label: "Budgets" },
  { href: "/cdf", label: "CDF projects" },
  { href: "/about", label: "About the data" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:m-2 focus:rounded focus:bg-surface focus:p-2">
          Skip to content
        </a>
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-4">
            <Link href="/" className="leading-tight">
              <span className="block text-lg font-semibold tracking-tight text-brand">Zambia Open Data</span>
              <span className="block text-sm text-ink-2">Lusaka City Council, line by line</span>
            </Link>
            <nav aria-label="Main" className="-mx-1 flex flex-wrap gap-1 text-sm">
              {NAV.map((n) => (
                <NavLink key={n.href} href={n.href}>
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flag-stripe h-1" aria-hidden />
        </header>
        <main id="main" className="mx-auto max-w-6xl px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-line">
          <div className="mx-auto max-w-6xl space-y-1 px-4 py-6 text-sm text-ink-2">
            <p>
              Figures are from Lusaka City Council&apos;s approved budget books and news posts at{" "}
              <a className="underline" href="https://www.lcc.gov.zm">
                lcc.gov.zm
              </a>
              . This is an independent project, not run by the council.
            </p>
            <p>
              Open data and code on{" "}
              <a className="underline" href="https://github.com/kasondebbuku-spec/zambia-open-data">
                GitHub
              </a>
              .
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
