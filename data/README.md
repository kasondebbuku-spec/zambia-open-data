# The dataset

Everything in [`snapshot/`](snapshot) is built by `zod build` from Lusaka City Council's
published documents. Files are UTF-8, comma-separated, with a header row. Amounts are whole
Zambian kwacha (ZMW).

## `budget_books.csv`: one row per approved budget book

| Column | Meaning |
|---|---|
| `year` | The year the book approves |
| `revenue_total_zmw` | Grand total of revenue, as printed |
| `spending_total_zmw` | Head total of spending, as printed (equal to revenue: the budget balances) |
| `source` | Key into `sources.json` |

## `revenue.csv`: one row per revenue line per year column

| Column | Meaning |
|---|---|
| `book_year` | Which book the figure is printed in |
| `line` | Order of the line in the book, stable within a book |
| `fiscal_year` | The year the figure is for |
| `stage` | `budget` (the year the book approves) or `projection` (a forward estimate) |
| `group_code`, `group_name` | Revenue group, e.g. `02` Fees and Charges |
| `item_code`, `item_name` | The line. Codes repeat across sub-groups, so use `line` as the key |
| `amount_zmw` | Amount |

## `spending.csv`: one row per spending line per year column

| Column | Meaning |
|---|---|
| `book_year`, `fiscal_year` | As above |
| `stage` | `budget` or `prior` (an earlier year's figure, reprinted in this book) |
| `basis` | `economic` (Table 1: salaries, goods and services …) or `programme` (Table 2) |
| `code`, `name` | Line code and name, as printed in that book |
| `amount_zmw` | Amount. Blank cells in the book (`-`, `(0)`) are left out |

## `cdf_stories.csv`: one row per council news story about CDF projects

| Column | Meaning |
|---|---|
| `post_id`, `url` | The council's WordPress post |
| `published_on`, `title` | As published |
| `summary` | The first ~280 characters of the story |
| `constituencies` | `;`-separated, from Lusaka's seven: Chawama, Kabwata, Kanyama, Lusaka Central, Mandevu, Matero, Munali |
| `sectors` | `;`-separated keyword tags: education, health, water_sanitation, roads_drainage, markets, empowerment, community_safety |
| `status` | planned, under_construction, completed, commissioned or handed_over, read from the wording (headline first) |
| `largest_amount_zmw` | The largest kwacha amount the story mentions (not necessarily the project's cost) |
| `completion_pct` | A completion percentage, when the story gives one |

## `checks.csv` and `sources.json`

`checks.csv` holds every quality check with `pass`, `warn` or `fail` and a plain-English
detail. A build with any `fail` writes nothing. `sources.json` gives each source file's URL,
size, SHA-256 and the time it was fetched.
