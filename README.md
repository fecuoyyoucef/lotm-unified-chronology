# Lord of the Mysteries Unified Chronology

A provenance-preserving, extraction-friendly chronology that joins:

- the world-history timeline from the [Lord of the Mysteries Wiki timeline](https://lordofthemysteries.fandom.com/wiki/Timeline);
- all 15 Novel Wiki chapter-summary pages covering chapters 1–1,432; and
- the 12 named story arcs from [Novel Wiki Story Arcs](https://www.novelwiki.net/lord-of-the-mysteries/story-arcs/).

The repository stores normalized JSON and CSV data, human-readable Markdown pages, source snapshots, and a persistent extraction log. The timeline records retain the source section, era label, time/date fields, event text, source template, and source page. Summary and arc pages retain their chapter ranges and canonical URLs.

## Repository layout

- `data/timeline.json` and `data/timeline.csv`: 216 normalized timeline records in source order.
- `data/summaries.json`: the 15 chapter-summary index records.
- `data/arcs.json`: the 12 story-arc records and chapter ranges.
- `data/chapter-crosswalk.json`: overlaps between 100-chapter summary ranges and story arcs.
- `data/summaries/`: one detailed Markdown page per summary range.
- `data/arcs/`: one Markdown page per named arc.
- `sources/`: fetched source snapshots used to generate the dataset.
- `scripts/extract.py`: rerunnable extractor using the Fandom public API and Novel Wiki HTML pages.
- `logs/latest.json` and `logs/run-*.json`: persistent extraction history.

## Rebuild

```bash
python3 -m pip install requests beautifulsoup4 markdownify
python3 scripts/extract.py
```

The extractor intentionally uses paraphrase-oriented Markdown output and source links rather than presenting the novel text itself. The websites remain the authoritative sources for their content, wording, updates, and copyright terms.

## Caveats

The Fandom timeline states that many historical dates are approximate or unspecified. The normalized dataset therefore preserves source-order and the original `time`, `date`, and `era_label` strings instead of inventing precise dates. Arc links on Novel Wiki currently resolve to the relevant chapter-summary pages; the repository gives each arc its own local page while retaining that canonical link.

This is a fan-made research and indexing project. It is not affiliated with the author, the novel publisher, Fandom, or Novel Wiki.
