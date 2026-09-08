# PrivAudit

This repository is the artifact for *PrivAudit: A Dual-Lens Auditing Framework for Website Privacy
Practices under the CCPA*, appearing at the ACM SIGSAC Conference on Computer and Communications
Security (CCS '26).

## Quickstart

```bash
pip install -r requirements.txt
cd data && unzip data.zip && cd ..

python3 analysis/apply_verified_labels.py     # attach CCPA-subjectivity labels to the cookie data
python3 analysis/regen_table1_policy.py       # reproduces the Table 1 disclosure results
```

Each `analysis/regen_*` script prints the submitted and current results side by side. The datasets
and CCPA-subjectivity labels ship in `data/data.zip`, so the analyses run without re-scraping or
re-crawling. Scripts resolve `data/` relative to the repository root; set `PRIVAUDIT_ROOT` to point
them elsewhere.

## Components

- `subjectivity/`: CCPA applicability labeling from revenue and entity-type signals (Section 3.1).
- `policy_analysis/`: Disclosure lens, privacy-policy scraping, LLM rubric scoring, and validation
  (Section 3.2). Includes the scraper (`scraper/`), the scoring notebook
  (`extract_policy_claims.ipynb`), and the CCPA rubric prompt (`prompts/`).
- `crawler/`: Behavior lens, Puppeteer cookie audit under six privacy configurations
  (Section 3.3). Includes the crawler (`scripts/`), configuration profiles (`configs/`),
  consent-banner selectors (`flows/`), and GPC tooling (`gpc_toolkit/`).
- `cookie_categorization/`: Cookie-functionality classification from multiple public datasets
  (Section 3.3).
- `banner_detection/`: Consent-banner detector (Sections 3.3, 4.2).
- `analysis/`: Statistical analysis and the paper's tables and figures (Sections 3.4, 4.1–4.3).
- `inner_page/`: Extension, tracking beyond the homepage (Appendix).
- `tranco_scale/`: Case study, 1,000 popular Tranco websites (Section 4.4).
- `data/`: Datasets, shipped as `data.zip` (see [Data](#data)).

## Claims

Each of the paper's claims is reproduced by the script below. Run `apply_verified_labels.py` once
first; every script reads only from `data/`.

- **CCPA-Subject websites provide stronger disclosures** (opt-out 77% vs. 57%, access 85% vs. 68%,
  delete 86% vs. 69%, GPC 29% vs. 13%; Section 4.1, Table 1),  `analysis/regen_table1_policy.py`.
- **Cookie-based tracking remains pervasive** (6,392 Targeting cookies, 49% third-party writes;
  10 scripts set over half of all tracking cookies; Section 4.2, Table 2), 
  `analysis/regen_table2_full.py`, `analysis/regen_overall_after_exclusion.py`,
  `analysis/tables/`.
- **Privacy signals reduce but do not eliminate tracking** (GPC cuts total tracking cookies 55% but
  third-party tracking only 41%; Section 4.2), `analysis/regen_table_3p_reduction.py`,
  `analysis/regen_overall_after_exclusion.py`.
- **Linking disclosures to behavior reveals audit-relevant gaps** (GPC-honoring claims with no
  tracking reduction; "do-not-sell" sites still setting third-party cookies; Section 4.3), 
  `analysis/regen_joint_lens.py`, `analysis/compliance_matrix_1798130.py`.
- **Findings survive multiple-hypothesis correction** (every main policy finding holds under the
  Holm–Bonferroni correction over all 25 tests; appendix), `analysis/regen_mht_table.py`.
- **The disclosure gap is not explained by firm size** (Section 4.1), 
  `analysis/size_control_analysis.py`.
- **Findings generalize to popular websites** (1,000-site Tranco case study; Section 4.4), 
  `tranco_scale/analyze_ccpa_frame.py`.

Figures (`analysis/figures/`) regenerate to `figures_output/`:

```bash
python3 analysis/figures/plot_split_violin_updated.py
python3 analysis/figures/plot_cdf_comprehensive_banner_ccpa.py
python3 analysis/figures/plot_ecdf_lifespan_ccpa_split.py
```

## Requirements

- Python ≥ 3.10
- Node.js ≥ 18.x (for the crawler)
- Google Chrome

```bash
pip install -r requirements.txt
cd crawler && npm install && cd ..
```

## Using the framework on your own websites

The Quickstart and Components sections reproduce the paper from the bundled data. To audit a new set
of websites, run the two lenses on your target list and then join them. The lenses are independent;
the join at the end produces PrivAudit's audit signals.

### 1. Determine CCPA applicability (optional)

Label each business as CCPA-Subject or CCPA-Not-Subject from revenue and entity-type signals.

```bash
python3 subjectivity/apollo_reclassify.py
```

### 2. Disclosure lens — privacy policy audit

List your target site URLs in `policy_analysis/scraper/data/url_list_to_process.txt`, locate and
extract each policy, then score it against the CCPA rubric. Pass your OpenAI key through the
environment.

```bash
python3 policy_analysis/scraper/privacy_policy_url_scraper.py    # find each site's privacy-policy URL
python3 policy_analysis/scraper/privacy_policy_data_scraper.py   # extract policy text -> scraped_results.json

export OPENAI_API_KEY="your-key"
jupyter notebook policy_analysis/extract_policy_claims.ipynb     # score disclosures against the rubric
```

The notebook reads `scraped_results.json` and writes per-site disclosure scores and claims.

### 3. Behavior lens — cookie audit

List your target domains in a CSV with an `Accessible Domain` column and point a config in
`crawler/configs/` at it via `input_files`. The crawler then visits each site under the six privacy
configurations (default, GPC, DNT, third-party blocking, uBlock Origin, Consent-O-Matic) and records
every cookie written.

```bash
node crawler/scripts/cookie_profile_test.js         # per-cookie CSV, one column per configuration
python3 cookie_categorization/update_cookies.py     # categorize functionality + attribute third parties
```

### 4. Join the lenses

Attach the CCPA labels to the cookie data, then compute the disclosure–behavior gaps that are
PrivAudit's core auditing signal.

```bash
python3 analysis/apply_verified_labels.py
python3 analysis/regen_joint_lens.py            # disclosures vs. tracking, by group
python3 analysis/compliance_matrix_1798130.py   # §1798.130 disclosure-vs-behavior matrix
```

## Data

`data/data.zip` contains the audited cookie dataset, the extracted policy claims, the
CCPA-subjectivity labels (`results/`), and the case-study crawl data. The corpus comprises 998
analyzed websites — 602 CCPA-Subject and 396 CCPA-Not-Subject — plus a separate 1,000-site
case-study sample.

## Cookie categorization databases

`cookie_categorization/` needs external databases that are not redistributed here due to licensing.
Download them and place them in `cookie_categorization/databases/`:

| Database | Source |
|---|---|
| Open Cookie Database | https://github.com/jkwakman/Open-Cookie-Database |
| Cookiepedia | https://cookiepedia.co.uk |
| Cookie Cutter DB | https://github.com/nickcounts/CookieCutter |
| DuckDuckGo Tracker Radar | https://github.com/nickcounts/tracker-radar |
| Disconnect Tracking Lists | https://github.com/nickcounts/disconnect-tracking-protection |

## Ethics

We conducted all crawling and analysis from clients located in California. PrivAudit issues fewer
than 10 requests per website — to retrieve its privacy policy and to observe the cookies set under
each privacy configuration — an insignificant fraction of normal web traffic, and the
configurations are crawled round-robin to avoid load on the websites. We collect no user data other
than our own, and all analysis, including data fed to the LLMs, relies solely on publicly available
website responses. The patterns PrivAudit surfaces are auditing signals for manual review, not
determinations of legal violations.

## Citation

If you use PrivAudit in your research, please cite our paper:

> Mohamed Moustafa Dawoud, Riya Aggarwal, Likith Rahul Krishnamurthy, and Ram Sundara Raman. 2026. PrivAudit: A Dual-Lens Auditing Framework for Website Privacy Practices under the CCPA. In *Proceedings of the 2026 ACM SIGSAC Conference on Computer and Communications Security (CCS '26)*.

```bibtex
@inproceedings{dawoud2026privaudit,
  title     = {PrivAudit: A Dual-Lens Auditing Framework for Website Privacy Practices under the {CCPA}},
  author    = {Dawoud, Mohamed Moustafa and Aggarwal, Riya and Krishnamurthy, Likith Rahul and Sundara Raman, Ram},
  booktitle = {Proceedings of the 2026 ACM SIGSAC Conference on Computer and Communications Security (CCS '26)},
  year      = {2026},
  publisher = {Association for Computing Machinery}
}
```
