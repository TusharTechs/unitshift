# UnitShift — evidence before action

A finance operations workspace that investigates invoice and cancellation signals across source records, product context and independent currency reference data. NVIDIA Nemotron chooses bounded source tools and proposes cited decisions; code checks the references, accounting arithmetic, quote direction and missing authorisations before a result is shown.

**Track:** Solving Fragmented Intelligence. **Live judge deployment:** https://ds59bjv2cezd6.cloudfront.net (public release is verified separately in deployment evidence). No prize outcome, customer savings or production accuracy is guaranteed.

## Real data, explicitly attributed

The default workspace uses **all 541,909 original lines** from [Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), Daqing Chen, UCI Machine Learning Repository (2015), DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It contains 25,900 invoice identifiers, 4,372 non-empty anonymised customer IDs and 4,070 stock codes. Observed missing fields and duplicate-looking rows remain intact.

The independent reference source is [ECB statistics](https://data-api.ecb.europa.eu/service/data/EXR/D.GBP.EUR.SP00.A?startPeriod=2010-11-25&endPeriod=2011-12-09&format=csvdata): 272 dated observations of GBP per EUR, used under the [ECB statistics reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html). Raw observations are unchanged; transaction EUR equivalents are separately labelled UnitShift calculations. They are retrospective reporting values, not settlement or point-in-time trading quotes.

These are **historical 2010–2011 records**, not live customer operations. No retailer or customer is re-identified. Retail entity tables are derived from one UCI export; they are not described as independent commercial systems. UCI and the ECB do not endorse UnitShift. See [data provenance](data/public/manifest.json) for source hashes, transformations, row counts and limitations.

## What works

- A complete searchable source ledger, preserving original workbook row numbers.
- A review queue with cancellation context, duplicate-looking lines, missing customer IDs and zero-price signals.
- Customer summaries using original anonymised IDs, without invented business names or credit scores.
- Product-description variants, without inferring unsupported stock or pack-size facts.
- An asynchronous investigation lab with actual Zetaris reads, Nemotron tool selection, typed conclusions and verification feedback. Its animated progress steps are driven by actual source, memory, model and policy receipts.
- A separate Nightshift-backed review contract and scoped Meterless H-MEM approved-check storage and recall.
- Readable review-packet and JSON exports, actual call receipts and source SQL.
- An editable business-value calculator whose inputs and outputs are explicitly hypotheses, not measured ROI.

The main demonstration traces source rows 540423 and 540424: invoice 581483 records GBP 168,469.60; cancellation C581484 records the opposite quantity and amount twelve minutes later. A matching customer, SKU, price and quantity make the former an **attribute-match candidate**, not a source-proven original invoice or authorised refund. The two rows sum to zero, but no commercial reason, settlement, refund authorisation or business saving is claimed.

## Sponsor contributions

| Technology | Actual responsibility | Evidence |
|---|---|---|
| Zetaris | Four registered source tables and a cross-publisher semantic view joining transaction, invoice grain, product variants and dated ECB observations | Source registrations, readback counts, query hashes and complete 541,909-row join-grain check |
| NVIDIA Nemotron 3 Super on Nebius | Bounded source-tool selection, evidence interpretation and source-cited typed decisions; reasoning repair when a constraint fails | Actual effective model IDs, token usage, selected tools, attempts and verification receipts |
| Meterless Nightshift | A real NVIDIA-backed provider reviews the structured request-for-evidence disposition | Routing mode, effective model, receipt and accepted structured review |
| Meterless H-MEM | Stores operator-approved evidence checks and recalls them only for the matching dataset/contract scope | Pinned upstream engine add/query calls, ledger IDs and recalled memory references |

The code does not render private model reasoning. Generated text cannot authorise a refund, delete a row, invent a customer ID, reverse the FX quote or cite an unknown source row. Unknown references, wrong relationship fields or FX direction fail verification; no fixture answer replaces a failed live read. Mandatory missing-evidence requirements are imposed by application policy even when the model omits them. The accepted decision records policy-added checks separately from the raw model proposal, and the interface discloses that addition.

## Reproduce locally

Python 3.11+, Node.js 18+ and npm are required. Python uses its standard library. H-MEM is pinned to upstream commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`.

```sh
npm ci
npm run setup:memory
cp .env.example .env.local  # new checkout only; never overwrite configured secrets
```

Download the two primary source files from the links above. Then:

```sh
python3 scripts/import_public_retail.py --retail-zip /path/to/online-retail.zip --ecb-csv /path/to/ecb-gbp-eur.csv
python3 scripts/register_public_data.py --apply
npm start
```

The importer preserves every source line, writes an ignored read-only SQLite navigation index and CSV exports, and records hashes and the selection method. Registering sources requires the configured AWS account, the existing scoped S3 session and Zetaris access. On a new environment, configure the bucket, source session and semantic container explicitly; these setup scripts currently reference the original user's hackathon infrastructure.

Set `ZETARIS_BASE_URL`, `ZETARIS_API_KEY`, numeric `ZETARIS_ORG_ID`, `NEBIUS_BASE_URL`, `NEBIUS_API_KEY`, `NEMOTRON_MODEL`, and the discovered Nightshift endpoint, runtime key and route in `.env.local`. Use `DATA_BACKEND=zetaris` for live investigations. Browsing an indexed public source is labelled as such and does not imply a fresh live query.

Open http://127.0.0.1:8787. The earlier synthetic stock-recovery scenario remains separately labelled at `/sandbox`; the original invoice engineering workbench remains at `/review`. Its architecture, synthetic recovery outcomes and earlier small evaluation are documented in [the sandbox notes](docs/recovery-sandbox.md), not represented as real customer impact.

## Deployment and operating boundaries

The judge deployment uses one AWS EC2 `t3.small` instance, encrypted persistent storage, a CloudFront HTTPS endpoint and an origin restriction. No workstation AWS user key is installed. A dedicated instance role can read only the project's S3 source prefix; source access renews from that role without storing temporary keys in the repository. The Linux service runs as an unprivileged user with a read-only application tree and a writable state directory.

The initial compute window ends **November 10, 2026 at 00:00 UTC**, when the instance is configured to stop. Normal base infrastructure for that initial period is estimated below the user's USD 20 allowance; API usage and exceptional traffic are separate. Stopped-instance storage and distribution resources still exist and should be reviewed after judging. No costly autoscaling fleet or GPU is provisioned.

**Nightshift boundary:** the main app, source reads, H-MEM and primary Nemotron inference run in the cloud. The installed Nightshift desktop runtime is on the user's Mac, connected by a loopback-only encrypted SSH channel. If that machine or channel is unavailable, the site and primary investigation remain available and the secondary review is explicitly marked unavailable. A fully autonomous production install needs an authorised supported Nightshift host/endpoint. This is not disguised as a cloud-native Nightshift installation.

Public model calls are queued and rate-limited. The public recovery sandbox is read-only. Historical investigation and reusable-check controls create no external orders, messages, refunds or payments. Public source data is intentionally readable; this release is not a multi-tenant service for private customer data. Production requires tenant authentication, restricted runtime source credentials, fully private/TLS origin transport, external transaction controls, independent evaluation and authorised business integrations.

## Verification

```sh
npm test
node --check static/replay.js
node --check static/workspace.js
```

48 regression checks cover legacy reconciliation and recovery plus real-data evidence references, source changes, join fan-out, chronology, missing identity, unsupported refund approvals, quote direction and public model allowances. They also pass on the Linux deployment runtime. Actual public-data investigations and their receipts are saved under `data/evidence/`; these are recorded checks, not a balanced accuracy benchmark.

Source signals are **not confirmed errors, fraud, losses or savings**. The 40 review examples are a disclosed value-ranked selection. Customer validation, paid usage, measured review-time savings and production ROI have not been established. The business calculator is a pilot hypothesis that a real customer study must test.

## Provenance

UnitShift workflow, adapters, simulator, fixtures and interface are new project code. H-MEM is an Apache-2.0 upstream reference engine; commercial model weights and vendor platform code are not bundled. Development used Codex-assisted implementation and testing. Cursor was not used. Licensed public data and generated code usage are declared. See [third-party notices](THIRD_PARTY_NOTICES.md).
