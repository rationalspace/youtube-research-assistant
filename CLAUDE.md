# stock-summary-youtube — context for Claude

YouTube finance-influencer monitor. Pulls recent videos from a fixed list of
channels, transcribes/summarizes them into a structured ticker/thesis/rating
format, and stores them in a queryable SQLite database. Used as a cross-reference
input when evaluating new stock ideas or checking what a specific creator has
said about a ticker — see the "Cross-reference inputs" section of
`/Users/makkarmandeep/portfolio-monitor/CLAUDE.md` for how this project fits into
that workflow.

## Tracked channels

Defined in `profiles/finance.yaml` — currently 3: Parkev Tatevosian CFA
(`@parkevtatevosiancfa9544`), Akshat Shrivastava (`@AkshatZayn`), Ticker Symbol:
YOU (`@TickerSymbolYOU`). The summarization prompt in that same file enforces a
strict bullet format: header line with ticker(s)/rating/one-line thesis, then
Tickers & Prices / The Thesis / Rating / Worth Acting On sections.

## `query_db.py` CLI

Subcommands: `search <query> [--channel "Name"]`, `get <video_id>`, `list --limit N`,
`stats`. **`get` has no `--full` flag** — passing one errors with "unrecognized
arguments"; the full summary is the default (only) output of `get`.

## Data quality caveat — transcript-missing videos

Not every video gets a real transcript. When transcript capture fails, the
summary falls back to a description-only inference, and the record is marked
**"⚠️ LIMITED INFO - Transcript not available, summary based on description
only."** These are meaningfully lower-confidence than transcript-backed
summaries — the rating/thesis is a guess from the title and description, not
from anything the creator actually said in the video. Always surface this
caveat explicitly when reporting findings from a LIMITED INFO video; don't
present the inferred rating as if it were confirmed content.

## Data quality caveat — ticker symbol errors

Confirmed 2026-08-24: the summarizer (`gemini-2.5-flash-lite`, chosen for its free-tier
quota — see `youtube_monitor.py`) can output a **wrong ticker symbol** even from a
correctly-transcribed video, e.g. writing "CHR"/"LIT" instead of the real symbols
COHR (Coherent Corp) / LITE (Lumentum Holdings). The DB stores only the final summary,
not the raw transcript, so there's no way to tell after the fact whether the error came
from the source captions or the model itself. There is no ticker-validation step in the
pipeline. The prompt was tightened the same day to require full, verified ticker symbols
instead of guessed abbreviations — but treat any ticker from this tool as **unverified
until cross-checked** (e.g. does the company name/financials in the summary actually
match that symbol) before acting on it, same caution as the LIMITED INFO caveat below.

## Other files

- `research.db` — SQLite + FTS5, all summarized videos.
- `cron.log` — current log; rotated archives (`cron.log.YYYYMMDD`) are gitignored.
- `rotate-logs.sh` / `launchd/` — scheduled run + log rotation, launchd-managed.
