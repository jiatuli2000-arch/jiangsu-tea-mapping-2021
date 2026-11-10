# Compute evidence snapshot

Snapshot date: 10 November 2026. Figures were read from Earth Engine `ee.data.getTaskStatus` for the Jiangsu 2021 city probability exports. The local full task-ID snapshot is retained for the application; project and account identifiers are omitted here.

| Observation | Value | Interpretation |
| --- | ---: | --- |
| Completed city exports | 13 of 13 | All city probability exports finished in Earth Engine |
| Sum of completed batch task usage | 749.70 EECU-hours | Observed task-level total, not a monthly forecast |
| Four completed exports on the primary project | 178.17 EECU-hours | The project returned an Earth Engine restricted-mode warning |
| Wuxi direct pooled export | 107,777.67 EECU-seconds = 29.94 EECU-hours | One measured city export |

The 2021 city probability exports are a measured single-year workload; local download, threshold selection, independent validation and final area accounting are separate. Multi-year mapping would require repeated imagery processing, classification, and validation, but its EECU requirement has not been measured. Two comparable annual export cycles in one month would be estimated at about 1,499 EECU-hours before validation; this is a scenario, not observed monthly demand. The [official tier guide](https://developers.google.com/earth-engine/guides/noncommercial_tiers) describes recurring **monthly** quotas and restricted-mode behavior. A Partner Tier request should include a dated work schedule and explain why the Contributor Tier would be insufficient.
