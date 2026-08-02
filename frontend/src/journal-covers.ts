import type { Journal, JournalPriority } from "../types/journal";

type PublisherName =
  | "Oxford University Press"
  | "SAGE"
  | "Taylor & Francis"
  | "Inderscience Publishers"
  | "International Journal of Communication"
  | "ICONO14";

const publisherUrls: Record<PublisherName, string> = {
  "Oxford University Press": "https://academic.oup.com/",
  SAGE: "https://journals.sagepub.com/",
  "Taylor & Francis": "https://www.tandfonline.com/",
  "Inderscience Publishers": "https://www.inderscience.com/",
  "International Journal of Communication": "https://ijoc.org/",
  ICONO14: "https://icono14.net/",
};

const palettes: Array<[string, string]> = [
  ["#112a46", "#75d6e9"], ["#164e43", "#eabf74"], ["#8c202a", "#f1d7a2"],
  ["#5b3f91", "#d7c7ff"], ["#203c73", "#b2cdfc"], ["#a84527", "#f9d4a7"],
  ["#27646c", "#e2c56d"], ["#123e77", "#e8edf6"], ["#654b27", "#f2d7a1"],
  ["#3c385e", "#d4d0ff"], ["#7a3d2d", "#f2c68d"], ["#245866", "#bcecf2"],
];

type JournalRow = [
  abbr: string,
  name: string,
  publisher: PublisherName,
  priority: JournalPriority,
  issn: string,
];

const rawJournals: JournalRow[] = [
  ["HCR", "Human Communication Research", "Oxford University Press", "core", "0360-3989"],
  ["JCMC", "Journal of Computer-Mediated Communication", "Oxford University Press", "core", "1083-6101"],
  ["CR", "Communication Research", "SAGE", "core", "0093-6502"],
  ["ICS", "Information, Communication & Society", "Taylor & Francis", "core", "1369-118X"],
  ["JLSP", "Journal of Language and Social Psychology", "SAGE", "core", "0261-927X"],
  ["IJPP", "The International Journal of Press/Politics", "SAGE", "core", "1040-1620"],
  ["Icono14", "Revista Icono 14", "ICONO14", "core", "1697-8293"],
  ["CMM", "Communication Methods and Measures", "Taylor & Francis", "core", "1931-2458"],
  ["PC", "Political Communication", "Taylor & Francis", "core", "1058-4609"],
  ["JITP", "Journal of Information Technology & Politics", "Taylor & Francis", "core", "1933-1681"],
  ["SMS", "Social Media + Society", "SAGE", "core", "2056-3051"],
  ["JME", "Journal of Media Economics", "Taylor & Francis", "core", "0899-7764"],
  ["VC", "Visual Communication", "SAGE", "core", "1470-3572"],
  ["AJC", "Asian Journal of Communication", "Taylor & Francis", "core", "0129-2986"],
  ["JOBEM", "Journal of Broadcasting & Electronic Media", "Taylor & Francis", "core", "0883-8151"],
  ["IJSC", "International Journal of Strategic Communication", "Taylor & Francis", "core", "1553-118X"],
  ["MWC", "Media, War & Conflict", "SAGE", "core", "1750-6352"],
  ["CRR", "Communication Research Reports", "Taylor & Francis", "core", "0882-4096"],
  ["CAP", "Communication and the Public", "SAGE", "core", "2057-0481"],
  ["CRP", "Communication Reports", "Taylor & Francis", "core", "0893-4215"],
  ["IJMC", "International Journal of Mobile Communications", "Inderscience Publishers", "core", "1470-949X"],
  ["GMC", "Global Media and Communication", "SAGE", "core", "1742-7665"],
  ["IJPOR", "International Journal of Public Opinion Research", "Oxford University Press", "watch", "0954-2892"],
  ["IJoC", "International Journal of Communication", "International Journal of Communication", "skip", "1932-8036"],
  ["CS", "Communication Studies", "Taylor & Francis", "skip", "1051-0974"],
  ["IJMM", "International Journal on Media Management", "Taylor & Francis", "skip", "1424-1254"],
];

export const journals: Journal[] = rawJournals.map(([abbr, name, publisher, priority, issn], index) => ({
  abbr,
  slug: abbr.toLowerCase(),
  name,
  publisher,
  priority,
  issn,
  publisherUrl: publisherUrls[publisher] || "https://doi.org/",
  cover: { background: palettes[index % palettes.length][0], accent: palettes[index % palettes.length][1] },
}));
