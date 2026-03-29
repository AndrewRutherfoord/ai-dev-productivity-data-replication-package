# Developer Productivity in the age of AI - Replication Package

This repository contains the replication package for our study on whether AI-assisted development tooling is associated with measurable changes in open-source developer productivity. We identify candidate GitHub repositories via Google dorks queries for `CLAUDE.md` and `AGENTS.md`, treat the first commit introducing either file as the AI adoption point, and compare pre-/post-adoption activity and churn metrics.

Data collection and drilling were performed with [NeoRepro](https://github.com/AndrewRutherfoord/NeoRepro-MSR-Tool), which mines repositories into a Neo4j graph database to enable reproducible querying and analysis.

We then used Python scripts to perform time series analysis on the mined data, fitting ARIMAX models to identify significant changes in trends and levels of activity and churn metrics post-AI adoption, as well as paired t-tests comparing pre/post metrics.

## Finding relevant Repositories

To find relevant repositories, we used Google dorks queries to search for GitHub repositories containing `CLAUDE.md` and `AGENTS.md` files (case-insensitive). The end-to-end workflow is implemented in `data_collection/`:

Before running the scripts below, install the Python dependencies declared in `data_collection/pyproject.toml` (`cd data_collection && uv sync`).

1. **Collect candidate repositories using SerpAPI (Google results).**
   - Script: `data_collection/gathering_repos/1_gather_repos.py`
   - Setup: create `data_collection/gathering_repos/.env` with `SERPAPI_KEY` (see `data_collection/gathering_repos/.env.example`).
   - What it does: issues Google dork queries of the form `site:github.com inurl:blob "AGENTS.md"` and `site:github.com inurl:blob "CLAUDE.md"`, extracts the repository URL from each result (by stripping the `/blob/...` suffix), and writes the clone URLs to `data_collection/gathering_repos/agent_repos.csv`.
   - Run from the `data_collection/` directory so relative paths resolve:

```bash
uv run gathering_repos/1_gather_repos.py
```

2. **Convert the CSV into a NeoRepro drill configuration and deduplicate repositories.**
   - Script: `data_collection/gathering_repos/2_neorepro_yaml_convert_and_dedupe.py`
   - What it does: reads `agent_repos.csv`, normalizes entries to `https://github.com/<owner>/<repo>.git`, deduplicates by repository URL, and writes a NeoRepro YAML config (`data_collection/gathering_repos/agent_repos.yaml`) with the appropriate `defaults` and `repositories` entries.
   - Run (again from `data_collection/`):

```bash
uv run gathering_repos/2_neorepro_yaml_convert_and_dedupe.py
```

3. **Run the drill in NeoRepro.**
   - Start NeoRepro (see `tool/README.md`), then upload/paste the generated YAML config (e.g., `agent_repos.yaml`) on the Drill Configuration page and click **Execute**.
   - This clones each repository and indexes commit metadata plus file modifications/diffs needed for churn and file-touch metrics.

4. **Remove repositories that repeatedly failed or stalled during drilling.**
   - Some repositories consistently failed or became impractically slow to drill (often due to very large files/binaries), so we removed them to complete the study within time constraints.
   - Script: `data_collection/remove_failed/remove_failed.py`
   - Inputs/outputs:
     - Reads failed repos from `data_collection/remove_failed/failed.json`
     - Removes them from `data_collection/remove_failed/agents-file-config.yaml`
     - Writes a cleaned config to `data_collection/remove_failed/agents-file-config-with-failed-removed.yaml`

## Running the NeoRepro tool to drill the repositories

Consult the README in `tool/` for instructions on setting up and running NeoRepro to drill the repositories into a Neo4j database. Make sure to use the cleaned YAML config generated in step 4 above.

To load the backup without running the drill again, download the Neo4j backup from [this link](https://drive.google.com/file/d/1IGSNp5hP59hU5hkap8tI4__5B-TvswTr/view?usp=sharing) and place it in `./volumes/neo4j_import` and unzip it:

```bash
cd volumes/neo4j_import
tar -xzf neo4j_backup.zip
```

Then in the NeoRepro tool, navigate to "Manage DB" and click the restore button next to the cypher phile that you unzipped. This will restore the Neo4j database to the state of the backup, which contains all the drilled data from the repositories. The restore will take a while since it is 12GB of data.

## Analysis and Plotting

The main analysis scripts are in `processing_scripts/`. They assume you have already drilled the repositories into Neo4j using NeoRepro (see `tool/README.md`) and that the Neo4j connection details match your environment.

Before running the scripts below, install the Python dependencies declared in `processing_scripts/pyproject.toml`:

```bash
cd processing_scripts
uv sync
```

### ARIMAX churn analysis

- Script: `processing_scripts/arimax_analysis_of_churn.py`
- What it does:
   - Queries Neo4j for weekly and per-commit churn/activity metrics around the AI-adoption point (first commit introducing `CLAUDE.md` or `AGENTS.md`).
   - Fits ARIMAX models to weekly metrics (level and trend change after adoption).
   - Performs paired t-tests
   - Writes summary CSVs used for reporting/plotting.
- Outputs (written into `processing_scripts/`):
   - `churn_arimax_summary.csv`
   - `churn_paired_ttest_summary.csv`

Run it from the `processing_scripts/` directory:

```bash
cd processing_scripts
uv run arimax_analysis_of_churn.py
```

If your Neo4j host/credentials differ, update them in `processing_scripts/interact_with_neo4j.py`.

### Plotting the results

- Script: `processing_scripts/arimax_result_plots.py`
- What it does:
   - Reads `churn_arimax_summary.csv` and `churn_paired_ttest_summary.csv`.
   - Produces heatmaps and bar charts summarizing significance rates and effect directions.
- Output directory: `arimax_result_plots/`

Run:

```bash
cd processing_scripts
uv run arimax_result_plots.py
```

