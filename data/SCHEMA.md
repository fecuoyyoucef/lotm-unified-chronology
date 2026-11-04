# Data schema

## `timeline.json` / `timeline.csv`

Each record contains:

- `id`: stable hash-based record identifier.
- `section`: source timeline section.
- `section_id`: Fandom template name used to retrieve the section.
- `era_label`: source table grouping label, when present.
- `time`: source time/period string.
- `date`: source date string, when present.
- `event`: normalized, citation-stripped event text with nested bullets flattened.
- `source_template`: canonical Fandom template URL.
- `source_page`: canonical public timeline URL.

## `summaries.json`

Each item contains `title`, `url`, `start`, and `end` chapter numbers.

## `arcs.json`

Each item contains `title`, `url`, `start`, `end`, and the source `description`.

## `chapter-crosswalk.json`

Each item maps one 100-chapter summary range to every named story arc whose chapter interval overlaps it.
