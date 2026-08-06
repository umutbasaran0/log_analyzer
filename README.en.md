# Log Analyzer — LLM-based Syslog Analysis System

🇹🇷 [Türkçe için tıklayın](README.md)

A prototype system that analyzes large-volume syslog data with the help of an
LLM (DeepSeek Flash v4). Using templating, time/token-based chunking, and
RAG-like retrieval, it analyzes millions of log lines in a scalable and
cost-effective way, without sending the entire dataset directly to the model.

See [docs/01_architecture.md](docs/01_architecture.md) for a detailed
architecture description (Turkish; English translation planned).

## Requirements

- Python 3.11+
- (For real analysis) A DeepSeek API key — https://platform.deepseek.com/

## Installation

```powershell
git clone https://github.com/umutbasaran0/log_analyzer.git
cd log_analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Setting the API Key

A `.env` file in the project root is required to run against the real
DeepSeek API:

```powershell
"DEEPSEEK_API_KEY=your-real-key-here" | Set-Content -NoNewline -Encoding ascii .env
```

The `.env` file is protected by `.gitignore` and is never committed to the
repo. If this file is missing (or the `--mock` flag is passed), the system
automatically falls back to mock mode — no real request is sent to DeepSeek;
a rule-based fake JSON response is returned instead, for free testing.

## Downloading Sample Data

The project works with a small subset of the
[vulcansiem/synthetic-syslog-1B](https://huggingface.co/datasets/vulcansiem/synthetic-syslog-1B)
dataset — tested at prototype scale with sizes ranging from 500 to 50,000 lines:

```powershell
python scripts\download_sample.py 500 sample_data\sample_syslog.txt
```

## Usage

### Mock mode (no API key required, free testing)

```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500 --mock
```

### With the real DeepSeek API

If the `.env` file is set up, running without the `--mock` flag is enough:

```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500
```

### Natural language Q&A (RAG)

After the analysis completes, a question can be asked with `--ask`; the
system first converts the question into filters (query understanding), then
locally retrieves matching records (retrieval), and finally sends only that
subset to the LLM to generate an answer:

```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500 --ask "what are the most common error types?"
```

### All parameters

| Parameter | Default | Description |
|---|---|---|
| `--input` | `sample_data/sample_syslog.txt` | Input log file |
| `--limit` | (none, whole file) | Maximum number of lines to read |
| `--window-minutes` | `5` | Time window size (minutes) |
| `--max-tokens-per-chunk` | `4000` | Token budget per sub-chunk |
| `--mock` | off | Run LLM calls in mock mode |
| `--ask` | (none) | Natural language question to ask after the report |
| `--output` | `output/report.json` | Path to write the report output |

## Output

At the end of a run, `output/report.json` contains the overall analysis
report (summary, anomalies, error categories, security signals), and a cost
summary (token counts, dollar amount) is printed to the console.

## Project Structure

```text
log_analyzer/
├── siem/
│   ├── __init__.py
│   ├── syslog_parser.py    # Parses raw log lines into LogRecord objects
│   ├── templater.py        # Templates and groups logs
│   ├── chunker.py          # Time-window + token-budget based splitting
│   ├── cost_tracker.py     # LLM call cost tracking
│   ├── prompts.py          # All LLM system prompts
│   ├── llm_client.py       # DeepSeek API client
│   ├── analyzer.py         # Map step: window-based LLM analysis
│   ├── aggregator.py       # Reduce step: hierarchical summary merging
│   ├── qa.py               # RAG-like natural language Q&A
│   └── main.py             # CLI entry point
├── scripts/
│   └── download_sample.py  # Sample data downloader from Hugging Face
├── prompts/
│   ├── 01_chunk_analysis_system_prompt.txt
│   ├── 02_reduce_system_prompt.txt
│   ├── 03_qa_system_prompt.txt
│   └── 04_query_understanding_system_prompt.txt
├── docs/
├── sample_data/
├── requirements.txt
├── .gitignore
└── README.md
```

## Documentation

- **Architecture and design decisions:** [docs/01_architecture.md](docs/01_architecture.md)
- **Sample analysis results:** [docs/02_sample_results.md](docs/02_sample_results.md)
- **Performance and API cost measurements:** [docs/03_performance_and_cost.md](docs/03_performance_and_cost.md)
- **Known issues and proposed improvements:** [docs/04_problems_and_improvements.md](docs/04_problems_and_improvements.md)

> Note: the linked documents under `docs/` are currently in Turkish. An
> English translation may be added later.