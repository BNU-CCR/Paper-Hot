import { notFound } from "next/navigation";
import { JournalReadingList } from "../../../components/journal-reading-list";
import { getAllPapers, getFeaturedPapers, matchesJournal } from "../../../lib/data";
import { journals } from "../../../src/journal-covers";

export function generateStaticParams(): Array<{ slug: string }> { return journals.map((journal) => ({ slug: journal.slug })); }

export default async function JournalReadingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const journal = journals.find((item) => item.slug === slug);
  if (!journal) notFound();
  // Pre-filter on the server so the client only receives this journal's
  // papers instead of the whole corpus (~1MB) in the RSC payload.
  const featured = getFeaturedPapers().filter((paper) => matchesJournal(paper, journal));
  const allPapers = getAllPapers().filter((paper) => matchesJournal(paper, journal));
  return <JournalReadingList journal={journal} featuredPapers={featured} allPapers={allPapers} />;
}
