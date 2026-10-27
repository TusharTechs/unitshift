# Third-party notices

## Meterless H-MEM

Source: https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/hmem/reference

Upstream repository license: Apache License 2.0. The source implementation is fetched by `npm run setup:memory` and is not authored by this project. Retain upstream notices when distributing the vendored implementation. The application's upstream engine reference is pinned to the revision above, as recorded in the local degit source cache used for setup.

## Development dependencies

`tsx`, `degit` and their transitive dependencies retain the licenses distributed in their respective npm packages. No model weights or proprietary Zetaris platform binaries are included in this source tree.

## UCI Online Retail public dataset

Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33.
Source: https://archive.ics.uci.edu/dataset/352/online+retail
License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/.

Changes: source workbook dates are converted to calendar timestamps rounded to the recorded second; decimal line amounts, entity summaries, duplicate-looking-row references, review selections and proposed candidate links are derived by UnitShift. All 541,909 original transaction lines are retained in the indexed source. Identifiers remain anonymised as published. No endorsement is implied.

## ECB reference observations

Source: ECB statistics, series EXR.D.GBP.EUR.SP00.A. Original observations are unchanged and remain freely available from the ECB. Reuse terms: https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html and https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html.

UnitShift's reporting-currency joins and EUR equivalents are derived calculations, explicitly labelled separately from ECB-published data. No endorsement is implied.
