import { redirect } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Budgets() {
  const books = await api.budgets();
  redirect(books.length ? `/budgets/${books.at(-1)!.year}` : "/");
}
