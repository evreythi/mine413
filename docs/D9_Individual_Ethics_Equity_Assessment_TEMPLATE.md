---
title: "D9 - Individual Professional Responsibility, Ethics and Equity Assessment (TEMPLATE)"
subtitle: "MIN E 413 Term Project - each student writes their own response"
---

> **This is a template, not a submission.** D9 is an *individual* assessment. Each student must analyse the scenario in their own words and reach their own justified recommendation. The structure and the evidence pointers below come from the team's technical work. Use them as facts to reason with, not as text to copy. Cite the professional code that applies to you (e.g. APEGA Code of Ethics, Engineers Canada Code of Ethics / Guideline on the Code of Ethics, and the EGBC/APEGA guidance on the use of software and AI in practice, as applicable).

**Name:** ______________________

## Scenario (from the course outline, Section 6.2)

Management requests a definitive copper and gold inventory and a reclaim sequence for next year. Some regions of the stockpile have substantial uncertainty. A production target would be easier to justify by presenting only expected values. Parts of the historical dataset are less complete for some operating periods, crews, contractors or data-collection systems, so model reliability is uneven across the stockpile.

## Facts from the project you may draw on (verify against the outputs)

* Only **22%** of the modelled stockpile tonnage is directly informed by FMS records. **21%** is observed volume with an **imputed** grade (unattributed: FMS records missing). **57%** is pre-record (legacy) material with an **assumed** grade (`outputs/validation/inventory_by_class.csv`).
* FMS records are missing or partial on 03-16 to 03-18 and 03-22 to 03-28 (`outputs/qaqc/daily_coverage.csv`). The gaps are periods, not people: the data supplied contain no crew or contractor identifiers.
* Payloads are pass-count estimates (all multiples of 38 t). Grades are source-block values (21 signatures).
* Monte Carlo P10-P90 ranges for total tonnes and contained metal are in `outputs/uncertainty/mc_global_summary.csv`. Block-level CVs and confidence classes are in the block model.
* The tornado shows which assumptions move the answer most (`outputs/uncertainty/fig_sens_tornado.png`).

## Suggested structure (about 1,000-1,500 words)

1. **Ethical issues identified.** What is being asked, and what is the conflict (e.g. pressure to suppress uncertainty, paramountcy of public and stakeholder welfare, duty to the employer, competence, honesty in reporting)?
2. **Affected parties.** Who relies on the inventory and how could each be harmed or helped? (e.g. mine management, processing plant, finance/investors, regulators, workers whose jobs depend on the plan, crews/contractors whose data appear "incomplete", local communities, the team members themselves.)
3. **Uncertainty disclosure.** What must be communicated, and how? Consider ranges (P10/P50/P90), information classes (measured/inferred/assumed/model-generated), confidence maps, and a plain-language summary. What would be misleading about expected values alone?
4. **Risks.** Technical, financial, safety, reputational and legal risks of (a) presenting expected values only, and (b) refusing to provide any number.
5. **Bias and equity concerns.**
   * Systematic bias from unequal data quality: the legacy and gap-period material is assigned average grades. That could over- or under-state grade in exactly the regions with least data.
   * The risk of attributing discrepancies to particular crews/contractors when the cause may be data systems (FMS outages, survey clipping, timing). What evidence would be required before any attribution? Who should be consulted?
   * Explainability and usability: can operators, planners and processing staff understand and challenge the model? How were different perspectives (geology, survey, operations, processing) included?
6. **Professional responsibilities.** Validation and approval (who signs off?), the level of evidence needed before operational use, documenting assumptions and manual interventions, and verifying AI-generated or externally sourced code.
7. **Required actions and controls.** Specific workflow controls, e.g. mandatory display of confidence classes, a stage-gate review, independent check of the code and assumptions, a reconciliation programme against mill feed, a data-completeness audit, targeted sampling or drilling of the legacy and unattributed zones, a "no single-number" reporting rule.
8. **Justified recommendation.** State clearly what *you* would deliver to management, what you would qualify or decline to state, and under what conditions a definitive recommendation would become appropriate.

## References

(list the codes, guidelines and literature you cite)
