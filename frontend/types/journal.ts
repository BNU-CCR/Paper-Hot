/** Tracking priority for red-list journals. */
export type JournalPriority = "core" | "watch" | "skip";

export interface JournalCover {
  background: string;
  accent: string;
}

export interface Journal {
  abbr: string;
  slug: string;
  name: string;
  publisher: string;
  priority: JournalPriority;
  issn: string;
  publisherUrl: string;
  cover: JournalCover;
}
