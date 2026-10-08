---
title: "D1 - Team Charter and Work Plan"
subtitle: "MIN E 413 Term Project - Long-Term Stockpile Reconstruction and Block Modelling"
---

> **Before submission:** enter real names in `config/team.yaml` (they replace every `[Member n]` in the built documents), confirm the roles at the first meeting, and have every member sign Section 9. The meeting log and contribution record (Section 8) must reflect what *actually* happened. Do not pre-fill them.

# 1. Team members and initial roles

The team has five members. Each member owns one technical work package. Every member also reviews another member's work package (Section 6), so that each person can explain the whole method at the technical defence (course outline, Section 7.3).

| Member | Primary role (owner) | Technical work package | Reviewer of | Rotating duty |
|---|---|---|---|---|
| [Member 1] | Project lead and integrator | Overall workflow, final report (D6), presentation (D7) | WP5 | Meeting chair (weeks 1-3) |
| [Member 2] | Data and QA/QC lead | Task 1 data investigation, Task 2 growth analysis, Data and Assumption Register (D2) | WP3 | Minute-taker (weeks 1-3) |
| [Member 3] | Algorithm lead | Task 3 material-movement algorithm, Task 4 assumptions (D3) | WP4 | AI/software verification officer (weeks 1-4) |
| [Member 4] | Block model and validation lead | Task 5 block model, Task 6 validation, Task 7 uncertainty (D4) | WP2 | Meeting chair (weeks 4-6) |
| [Member 5] | Platform and reproducibility lead | Task 8 automated platform, tests, audit trail (D5) | WP1 | EDI and professional-practice champion |

Roles rotate where indicated, so that leadership and administrative load are shared fairly. The **AI/software verification officer** keeps the AI-use log (D6 appendix) and checks that every AI-assisted code change has a recorded test or hand check. The **EDI and professional-practice champion** leads the ethics/equity scenario discussion and checks that the report states its limitations.

# 2. Communication expectations and channels

| Channel | Purpose | Response expectation |
|---|---|---|
| Team chat (e.g. Teams/Discord channel) | Day-to-day coordination, quick questions | Within 24 h on weekdays |
| Shared Git repository (this repo) | All code, configuration, data registry, documents; one branch per work package, merged after review | Pull requests reviewed within 48 h |
| Weekly meeting (in person or video, 60 min) | Progress, decisions, blockers | Attendance expected; notify the chair 24 h ahead if absent |
| Shared drive | Large binaries (presentation recordings, scanned signatures) | |
| E-mail to the instructor/TA | Only via the project lead, after team agreement | |

Decisions made in chat are copied into the decision log (Section 8) by the person who proposed them.

# 3. Decision-making process

1. **Technical decisions inside one work package:** the owner decides after consulting the reviewer and records the decision in the decision log with its justification.
2. **Decisions affecting more than one work package or the final results** (for example survey timing, density basis, the algorithm form, block size): discussed at the weekly meeting. We aim for **consensus**. If no consensus is reached after a 10-minute structured discussion (each member states a position without interruption), we take a **majority vote** of members present (quorum of 4). The dissenting view is recorded in the decision log.
3. **Engineering-judgement items** (exclusions, corrections, imputations) need a register entry: assumption, need, justification, consequence and treatment (Task 4 format). The reviewer approves it before the change is merged.

# 4. Procedure for resolving disagreements

1. Raise the issue directly and respectfully with the person concerned within 48 h. Focus on the work, not the person.
2. If unresolved, bring it to the weekly meeting as an agenda item. The chair facilitates, and each side presents evidence (data, test results, references).
3. If still unresolved, a vote decides, as in Section 3, and the minority position is documented.
4. For persistent problems (missed commitments, conduct), the project lead holds a private conversation and agrees a written recovery plan. If this fails, the team informs the instructor, with a factual summary that the member concerned has seen.

# 5. Meeting and contribution expectations

* Weekly 60-minute meeting, plus a short stand-up in the lab session. The agenda is posted 24 h before. Minutes are posted within 24 h and record attendance, decisions, actions, owners and due dates.
* Each member is expected to contribute about equal effort (about 6-8 h per week). Workload is reviewed every second meeting. If one person is overloaded, tasks are re-allocated and the change is recorded.
* Commitments are made explicitly ("I will do X by date Y"). If a commitment is at risk, the member tells the team **before** the due date.
* Every member presents part of D7 and must be able to explain any part of the method.

# 6. Internal technical review and quality control

| Item | QC step | Evidence |
|---|---|---|
| Code | Peer review of every pull request by the WP reviewer. Automated tests (`python -m pytest`) must pass | PR approval, test log |
| AI-assisted code or text | Verification by a member other than the one who prompted the AI. Hand calculation or test on a small case | AI-use log entry (D6, Appendix A) |
| Data cleaning or exclusion | Register entry approved by the reviewer. Original record retained with a flag | `outputs/qaqc/fms_records_with_flags.csv` |
| Numbers in the report | Each number traced to an output file produced by a logged run (`outputs/audit/run_manifest.json`) | Run ID cited in the report |
| Final submission | Checklist (course outline, Section 12) ticked by two members independently | Signed checklist |

# 7. Respectful and inclusive participation

* Everyone gets the floor. The chair actively invites quieter members to speak before decisions, and written input (chat or comments) counts the same as speaking.
* Meeting times rotate where needed to accommodate work, caregiving, religious observance and time zones. Accessibility needs are accommodated without requiring disclosure of reasons.
* Feedback is specific, about the work, and given in private when it is critical.
* Technical tasks are assigned by interest and development goals, not by assumptions about who is "good at" coding, writing or presenting. Each member gets at least one opportunity to lead.
* Credit is attributed accurately in the contribution record.
* Harassment or discriminatory behaviour is not tolerated and will be escalated under university policy.

# 8. Work plan (Fall 2026)

| Week (starting) | Milestone | Owner(s) | Deliverable / evidence |
|---|---|---|---|
| Oct 5 | Charter signed; repository and environment set up; data inventory | All, M5 | D1, `requirements.txt` |
| Oct 12 | Task 1 QA/QC complete; survey re-dating and timing decisions logged | M2 | QA/QC tables and figures |
| Oct 19 | Task 2 growth and FMS-survey reconciliation; density/swell discussion | M2, M4 | Period reconciliation table |
| Oct 26 | Task 3 algorithm prototype; forward physics model; Task 4 register v1 | M3 | Algorithm notebook, D2 draft |
| Nov 2 | Block model v1; mass/metal balance verified; unit tests | M4, M5 | D4 draft, test log |
| Nov 9 | Validation (temporal, twin experiment), Monte Carlo and sensitivity | M4, M3 | Validation tables |
| Nov 16 | Platform hardening (update workflow, audit trail); report draft; ethics/equity discussion | M5, M1, all | D5, D6 draft |
| Nov 23 | Final review, presentation rehearsal, submission zip (Thursday Nov 26, 23:59) | All | D1-D9 |

Buffer: the 48 h before the deadline are reserved for review only, not new analysis.

## 8.1 Meeting log and contribution record (to be maintained by the team)

| Date | Attendees | Key decisions (ID) | Actions (owner, due) | Changes in responsibility |
|---|---|---|---|---|
| | | | | |

## 8.2 Technical decision log (decisions taken in the analysis - assign the proposer and approver)

| ID | Decision | Rationale (see D2/D3) | Proposed by | Approved by / date |
|---|---|---|---|---|
| DEC-01 | Survey files `Topo_250328`/`Topo_250329` re-dated to 2026-03-28/29 | QA-S02: FMS dates, face progression, layer naming | | |
| DEC-02 | Survey surfaces represent the end of the day (23:59) | Temporal alignment r = 0.96 vs ≤ 0.21 for morning times | | |
| DEC-03 | Treat each DXF as a closed change solid (bottom = previous surface) | 100% of cells hit by exactly two faces; bottoms match previous tops | | |
| DEC-04 | Use FMS dump XY only, not dump Z | Z residual vs surface sd ≈ 2.5 m | | |
| DEC-05 | No record deleted; flags + documented treatment | Traceability requirement | | |
| DEC-06 | Allocation by entropy-regularised optimal transport (CPST) | Survey-constrained, mass-conserving, mixing parameter explicit | | |
| DEC-07 | Base-case density = FMS density (κ = 1.0); κ tested 0.80-1.05 | Measured value preferred; confounded with missing FMS | | |
| DEC-08 | Block size 5 × 5 × 2 m | Survey/GPS resolution, reclaim equipment, sensitivity tested | | |
| DEC-10 | Impute X/Y of 14 records with an identical default position (A-32) | QA-F11: physically impossible location | | |
| DEC-09 | Legacy material reported separately with assumed grade, never mixed into "measured" totals | Professional accountability (Section 6.2 of brief) | | |

# 9. Agreement

By signing, each member agrees to follow this charter and to raise concerns early.

| Name | Signature | Date |
|---|---|---|
| [Member 1] | | |
| [Member 2] | | |
| [Member 3] | | |
| [Member 4] | | |
| [Member 5] | | |
