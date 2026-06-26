const assert = require("node:assert/strict");
const {
  createPaperCard,
  escapeHtml,
  filterPapers,
  getAllTags,
  groupPapersByDate,
} = require("./app.js");

const papers = [
  {
    id: 1,
    title: "Older platform governance paper",
    authors: ["Alice"],
    journal: "Journal A",
    published_date: "2025-01-01",
    relevance: "Medium",
    score: 72,
    summary: "Studies platform governance",
    reason: "Useful background",
    tags: ["平台治理", "social media"],
    source_url: "https://example.com/older",
  },
  {
    id: 2,
    title: "LLM communication paper",
    authors: ["Bob"],
    journal: "Journal B",
    published_date: "2026-05-10",
    relevance: "High",
    score: 91,
    summary: "LLM use in communication research",
    reason: "Strong computational communication fit",
    tags: ["LLM", "social media"],
    doi: "10.1000/test",
    source_url: "https://example.com/newer",
  },
  {
    id: 3,
    title: "No date paper",
    relevance: "High",
    tags: ["LLM"],
  },
];

assert.equal(escapeHtml("<script>"), "&lt;script&gt;");

assert.deepEqual(getAllTags(papers), ["LLM", "social media", "平台治理"]);

assert.deepEqual(
  filterPapers(papers, { relevance: "High", tag: null, query: "" }).map((paper) => paper.id),
  [2, 3],
);

assert.deepEqual(
  filterPapers(papers, { relevance: "all", tag: "social media", query: "governance" }).map(
    (paper) => paper.id,
  ),
  [1],
);

assert.deepEqual(
  filterPapers(papers, { relevance: "all", tag: null, query: "" }).map((paper) => paper.id),
  [2, 1, 3],
);

assert.deepEqual(Array.from(groupPapersByDate(papers).keys()), [
  "2025-01-01",
  "2026-05-10",
  "日期待补充",
]);

const card = createPaperCard({
  title: "<Unsafe>",
  relevance: "High",
  tags: ["x"],
  source_url: "https://example.com",
});
assert.match(card, /&lt;Unsafe&gt;/);
assert.doesNotMatch(card, /<Unsafe>/);

console.log("web app logic tests passed");
