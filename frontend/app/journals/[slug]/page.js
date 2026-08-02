import { notFound } from "next/navigation";
import { JournalReadingList } from "../../../components/journal-reading-list";
import { journals } from "../../../src/journal-covers";

export function generateStaticParams() { return journals.map((journal) => ({ slug: journal.slug })); }

export default async function JournalReadingPage({ params }) {
  const { slug } = await params;
  const journal = journals.find((item) => item.slug === slug);
  if (!journal) notFound();
  return <JournalReadingList journal={journal} />;
}
