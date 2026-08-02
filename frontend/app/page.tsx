import { getAllPapers, getFeaturedPapers } from "../lib/data";
import { HomeFeed } from "../components/home-feed";

export default function HomePage() {
  const featured = getFeaturedPapers();
  const allPapers = getAllPapers();
  return <HomeFeed featured={featured} allPapers={allPapers} />;
}
