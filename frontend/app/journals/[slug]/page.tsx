import { notFound } from "next/navigation";
import { JournalReadingList } from "../../../components/journal-reading-list";
import { getAllPapers, getFeaturedPapers } from "../../../lib/data";
import { journals } from "../../../src/journal-covers";

export function generateStaticParams(): Array<{ slug: string }> { return journals.map((journal) => ({ slug: journal.slug })); }

export default async function JournalReadingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const journal = journals.find((item) => item.slug === slug);
  if (!journal) notFound();
  const featured = getFeaturedPapers();
  const allPapers = getAllPapers();
  return <JournalReadingList journal={journal} featuredPapers={featured} allPapers={allPapers} />;
}
