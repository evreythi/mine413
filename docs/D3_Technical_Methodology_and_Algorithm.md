---
title: "D3 - Technical Methodology and Algorithm"
subtitle: "Constrained Push-and-Settle Transport (CPST) for stockpile reconstruction and block modelling"
---

# 1. Purpose and design philosophy

The movement of material from a truck dump point to its final place in the pile is never observed. Two kinds of observation constrain it:

* **where material came from**: FMS dump coordinates, tonnage and grade (*sources*);
* **where volume appeared**: the sequential survey change solids (*sinks*).

Physics-only rules (push to the crest, roll down at the angle of repose) can predict the shape of a deposit, but they predict *where* fill appears only moderately well. Our forward model places 40% of predicted volume inside the observed fill footprint on unseen periods (Section 9.3). A reconstruction used for inventory must therefore be **constrained by the surveys**. The design principle is:

> *Let the surveys decide **where** volume went, let the FMS decide **what** went there, and use a physically based transport cost (dozer push work over the real terrain) to decide **which** source filled **which** part of the observed fill, conserving mass and metal exactly.*

This is a classical earth-moving problem. Optimal transport was formulated by Monge (1781) to move *déblais* (cuts) to *remblais* (fills) with minimum work. We use its modern entropy-regularised form (Cuturi, 2013; Peyré and Cuturi, 2019), where the regularisation strength is a physically interpretable **mixing length**. We name the method **CPST: Constrained Push-and-Settle Transport**. A separate **forward physics model** (dozer push to crest + avalanche cellular automaton at the angle of repose) is used for prediction (temporal validation), for loads not yet surveyed (nowcast), and to generate known-truth data (synthetic twin validation).

![Platform workflow](figures/fig_workflow.png)

# 2. Data model

## 2.1 Grid and survey change solids

A regular grid of cell size $\Delta$ = 1 m (A-24) covers all data plus a 6 m margin. Its origin is snapped to a 10 m lattice so that grids of different resolution share block boundaries. Each survey file *s* is a closed triangulated solid (QA-S01). It is rasterised at cell centres $c$ by barycentric interpolation. The highest face through a centre gives $\text{top}_s(c)$ and the lowest gives $\text{bot}_s(c)$. Cells crossed by no face are outside the solid. The implementation is vectorised (`spbm/grid.py::rasterize_triangles`) and independent of face winding.

## 2.2 State: stratigraphic columns

The stockpile state is a **column of layers** for every cell. Each layer $\ell$ has a bottom and top elevation and a vector of **extensive** properties:

$$\boldsymbol{\pi}_\ell = (V,\; T_F, Cu_F, Au_F, Ag_F,\; T_U, Cu_U, Au_U, Ag_U,\; T_L, Cu_L, Au_L, Ag_L,\; \Sigma m\,g_{Cu}^2,\; \Sigma m\,g_{Au}^2,\; \Sigma m\,t,\; \Sigma m^2,\; T_R)$$

Here $V$ is volume (m³) and $T$ is tonnes. $Cu$ is tonnes of copper ($m\,g_{Cu}/100$). $Au$ and $Ag$ are kilograms ($m\,g/1000$). The subscripts F, U, L and R mean FMS-tracked, unattributed, legacy and provisional. Every operation of the algorithm (deposit, split, cut, mix) is a **non-negative linear combination** of these vectors. Mass and metal are therefore conserved by construction, and grades are always derived as ratios (e.g. $g_{Cu} = 100\,\sum Cu / \sum T$), never averaged directly.

## 2.3 Periods

Survey *s* is assigned the time $t_s$ = 23:59 on its (corrected) date (A-05). Period *s* is $(t_{s-1}, t_s]$. A load with time $t_k$ belongs to period *s* if $t_{s-1} < t_k \le t_s$. Loads after the last survey are *provisional*. A period is a **gap period** if $t_s - t_{s-1} > 36$ h, or if more than 10% of previously surveyed cells inside solid *s* have $\text{bot}_s$ above the model surface by more than τ (a missing intermediate survey).

# 3. The CPST algorithm (one period)

![CPST algorithm](figures/fig_algorithm.png)

## 3.1 Prior surface and legacy material (first-surveyed cells)

For a cell surveyed for the first time, the prior elevation $z^{0}_c$ is the solid bottom $\text{bot}_s(c)$, with one exception (A-13b). If the cell lies **in front of** a previously surveyed face, its prior elevation cannot exceed the repose-angle continuation of that face:

$$z^{\text{inf}}_c = \max\!\big(B_c,\; z_n - d_{cn}\tan\phi\big),\qquad z^{0}_c = \begin{cases} z^{\text{inf}}_c & \text{if } z^{\text{inf}}_c < \text{bot}_s(c) - \tau\\ \text{bot}_s(c) & \text{otherwise}\end{cases}$$

Here $n$ is the nearest surveyed cell, $d_{cn}$ the distance, $\phi = 37°$ and $B$ the fitted floor plane. "In front" is decided by the down-slope direction of the surveyed surface at $n$. The cell is in front if the vector $n\to c$ points down-slope (|cos| > 0.3); otherwise the cell is behind (on the platform). The difference $\text{bot}_s - z^{0}$ is fill placed during the record that no solid captured (toe-clipped solids, missing surveys). It joins this period's fill. A **legacy layer** from $\min(B_c, z^0_c)$ to $z^0_c$ is created with assumed properties (A-22).

## 3.2 Cuts (elevation decrease)

For previously surveyed cells, $\delta_c = \text{bot}_s(c) - z_m(c) < -\tau$ indicates material removed since the last observation (A-20). The top $|\delta_c|$ of the column is removed. Its extensive properties $\boldsymbol\Pi_j$ (split proportionally within the cut layer) become a **cut source** $j$ located at cell $c$.

## 3.3 Fill field (sinks)

$$\Delta Z_c = \text{top}_s(c) - z_m(c),\qquad b_c = \Delta Z_c\,\Delta^2 \;\;\text{for}\;\; \Delta Z_c > \tau$$

with the detection limit $\tau = k\sqrt2\,\sigma_z$ = 0.14 m (A-08, A-09).

## 3.4 Sources

* **Loads** $k$ of the period: $v_k = m_k / (\kappa\,\rho_k)$ m³, located at the dump cell (for the 14 records with a default FMS position, the tonnage-weighted centroid of the period's other dumps, A-32). Properties per m³: $\boldsymbol\pi_k = \boldsymbol\Pi(m_k, g_k)/v_k$ (question A: *initial placement* is a point parcel at the reported X/Y; GPS uncertainty is handled by Monte Carlo, Section 7).
* **Carried parcels** from the previous period (A-23), at their original dump cell.
* **Cut sources** $j$ (Section 3.2).
* **Dummy source U** (unattributed) with volume $V_F = \sum_c b_c$.

Sinks are the fill cells $c$, plus a **dummy sink R** (retained on the platform) with capacity $V_S = \sum_k v_k + \sum_j V_j$. The problem is balanced: $\sum a = V_S + V_F = \sum b$.

## 3.5 Push cost (questions B, C)

On the pre-period surface $z$ (surveyed or inferred), a directed 8-neighbour graph is built. The edge weight from cell $i$ to neighbour $j$ is

$$w_{ij} = \ell_{ij} + \alpha \max(0,\, z_j - z_i)$$

where $\ell_{ij}$ = 1 or √2 m and α = 4 is the uphill penalty (A-16). The push cost is the geodesic (Dijkstra) distance $C_{kc} = \min_{\text{paths}} \sum w$, with $C_{kc} = \infty$ if $C_{kc} > L_{\max}$ = 90 m (A-17). Dummy costs: $C_{kR} = c_R$ = 90 m, $C_{Uc} = c_U$ = 90 m, $C_{UR} = 0$. Because $c_R + c_U > L_{\max}$, a load is always sent to reachable fill before being retained. U fills only the volume that available sources cannot (*partial optimal transport*).

*Direction* (B) is therefore the least-work route over the actual terrain: down-slope pushes are cheap, pushing over a crest and down the face is cheap, uphill is expensive. The survey decides which face sector actually received fill. *Distance* (C) is set by the capacity constraint: material stops where observed accommodation space exists, and the least-cost assignment is used. Movement beyond $L_{\max}$ is not allowed. Material that finds no reachable fill stays on the platform (R) and is carried to the next period (dozer lag).

## 3.6 Allocation: entropic optimal transport (questions E, F, G, H)

$$\mathbf P^\star = \arg\min_{\mathbf P \ge 0} \;\sum_{k,c} P_{kc} C_{kc} \;-\; \varepsilon H(\mathbf P)\quad \text{s.t.}\;\; \mathbf P\mathbf 1 = \mathbf a,\;\; \mathbf P^\top\mathbf 1 = \mathbf b,\qquad H(\mathbf P) = -\sum P_{kc}(\log P_{kc} - 1)$$

The solution is $P_{kc} = \exp\big((f_k + g_c - C_{kc})/\varepsilon\big)$. It is computed by **log-domain Sinkhorn** iterations (numerically stable with infinite costs):

$$f_k \leftarrow \varepsilon\log a_k - \varepsilon\,\text{LSE}_c\!\left(\tfrac{g_c - C_{kc}}{\varepsilon}\right),\qquad g_c \leftarrow \varepsilon\log b_c - \varepsilon\,\text{LSE}_k\!\left(\tfrac{f_k - C_{kc}}{\varepsilon}\right)$$

Iteration stops when $\sum_k |\sum_c P_{kc} - a_k| / \sum a < 10^{-6}$ (max. 5000 iterations). A final row rescaling $P_{kc} \leftarrow P_{kc}\,a_k/\sum_c P_{kc}$ makes **each source's volume exactly conserved**. The remaining column residual (≤ 8×10⁻⁷ relative in all periods) is reported as the numerical reconciliation error.

**ε is the mixing length** (A-18). As ε → 0 the plan becomes the work-minimising deterministic assignment (no mixing beyond what is geometrically forced). As ε → ∞ every source is spread uniformly over the period's fill, giving the "period-average" model. ε = 6 m represents GPS error, blade spill and rolling on the face. Its effect is quantified by the twin experiment, the tornado and the Monte Carlo.

## 3.7 Deposit (questions D, E, F, I)

Each fill cell receives one new layer from $z_m(c)$ up to $z_m(c) + \sum_k P_{kc}/\Delta^2$, which equals the surveyed $\text{top}_s(c)$ to solver tolerance:

$$\boldsymbol\pi_{\text{layer},c} = \sum_{k} P_{kc}\,\boldsymbol\pi_k \;+\; P_{Uc}\,\boldsymbol\pi_U,\qquad \Sigma m^2_{c} = \sum_k \big(P_{kc}\,m_k/v_k\big)^2$$

*Downslope behaviour* (D) is honoured because the layer top is the surveyed surface: faces are at the measured angle of repose (median 36.7°), and the material that formed them, including what rolled to the toe, is assigned by the transport plan. Within one period the layer is vertically homogeneous (A-19). *Mixing* (E) is the volume-weighted combination of sources in the same cell. Grades follow from metal over tonnes, so mixing of loads with different densities is handled correctly. *Surface reconciliation* (F) holds because the column marginals equal the observed fill: the model surface equals the survey (Section 9.2). The unattributed U volume carries the imputed properties $\boldsymbol\pi_U$ (A-21).

## 3.8 Sequential updating (I) and closing the record

After deposit, $z_m$ = column tops, the volume in column R becomes carried parcels, and the next period starts from this state. After the last survey:

1. Never-surveyed domain cells receive legacy columns up to the inferred pre-record surface (A-13).
2. Parcels still retained are spread (Gaussian kernel, σ = 6 m) over **unsurveyed** platform cells around their dump point.
3. Loads after the last survey are placed by the forward model (Section 4) and flagged *Provisional*. When the next survey is imported they are automatically reconciled like any other load.

## 3.9 Mass and metal conservation (G, H)

* Every source row of $\mathbf P$ sums exactly to the source volume, so no FMS tonne is created or lost.
* Cuts move extensive properties from columns to sources and back into columns.
* The dummy U adds volume only to the *unattributed* class; legacy volume is only in the *legacy* class. FMS totals are therefore checked separately from them.
* Verification: FMS tonnes, Cu, Au and Ag in the final block model differ from the FMS input by 3×10⁻¹² (relative), i.e. floating-point round-off. This is enforced by the automated test `tests/test_core.py::test_end_to_end_mass_and_metal_conservation`.

## 3.10 Numerical stability (J)

| Setting | Value | Effect tested |
|---|---|---|
| Grid cell | 1 m (0.5 and 2.5 m tested) | Robustness table, Section 9.6 |
| Detection limit τ | 0.14 m (k = 1-4 tested) | Volume not moved: 96 m³ (0.2%) |
| Sinkhorn tolerance | 10⁻⁶ (10⁻⁴, 10⁻⁸ tested) | Column residual ≤ 8×10⁻⁷ |
| Log-domain Sinkhorn | always | No underflow with costs ≫ ε |
| Time step | one survey interval (data-driven) | Gap periods flagged |
| Block size | 5 × 5 × 2 m (2 × 2 × 1 and 10 × 10 × 4 tested) | Tornado |

Typical convergence takes 10-230 Sinkhorn iterations per period. A full reconstruction takes about 6 s.

## 3.11 Pseudocode

```text
INPUT  surveys s = 0..S-1 (top_s, bot_s, t_s), loads k (x, y, t, m, g, rho), config
STATE  columns[c] = list of (z_bot, z_top, props);  z_m[c];  observed[c];  carried = []
B <- fit_floor_plane(toe cells)            ; domain <- hull(survey cells, dumps)
for s in 0..S-1:
    F <- cells with finite top_s
    for c in F not observed:               # first-surveyed cells
        z0 <- bot_s[c]
        if s>0 and front_of_earlier_face(c): z0 <- min(z0, repose_extrapolation(c))
        columns[c] <- [legacy layer B..z0]
    for c in F observed and bot_s[c] < z_m[c]-tau:
        cut_sources += remove_top(columns[c], z_m[c]-bot_s[c])
    fill <- {c in F : top_s[c]-z_m[c] > tau},  b_c <- (top_s-z_m)*A
    sources <- carried + loads(period s) + cut_sources
    a <- [v_k ..., V_fill],  b <- [b_c ..., V_sources]
    C <- geodesic_cost(surface, alpha, L_max) ; add dummy costs c_R, c_U, 0
    P <- sinkhorn_log(a, b, C, eps) ; P <- rescale_rows(P, a)
    for c in fill: append layer sum_k P[k,c]*pi_k + P[U,c]*pi_U to columns[c]
    carried <- {k : P[k,R] > 0}            # dozer lag
    observed[F] <- True
add legacy columns on never-surveyed domain cells (inferred surface)
spread carried parcels on unsurveyed cells; nowcast post-survey loads (forward model)
blocks <- integrate layers into 5x5x2 m blocks (exact partial-layer fractions)
```

# 4. Forward (predictive) physics model

Used where no survey constrains the result (temporal validation, nowcasting, synthetic truth). Code: `spbm/forward.py`.

1. **Crest detection.** On the surface smoothed with a 1.5 m Gaussian, a face cell has slope > 20° and at least 5 m of local relief within 11 m. Crest cells are gentle cells adjacent to a face and near the local maximum. Only crests within the surveyed area are used.
2. **Dozer push.** Each load is pushed to the nearest crest cell and released down-slope onto the face (release offset 0-4 m, calibrated), as a disc of radius 2-5 m (calibrated).
3. **Gravity / avalanche cellular automaton.** Only the newly placed (*mobile*) material may move. For each cell $i$ and neighbour $j$, the excess is $e_{ij} = \max(0, z_i - z_j - \ell_{ij}\tan\phi)$. The cell releases $o_i = \min(\tfrac12\max_j e_{ij},\, \text{mobile}_i)$, distributed to neighbours in proportion to $e_{ij}$. This repeats until $\max o_i < 0.01$ m. Volume is conserved exactly (unit test). Slopes relax to ≤ φ.

# 5. Block model construction (Task 5)

* **Blocks**: 5 m × 5 m × 2 m, origin (511,290; 7,122,288; 4,474). Horizontal size: GPS error (σ ≈ 3 m) plus the mixing length (6 m) mean no information exists below about 5 m. Vertical size: 2 m gives 6-8 slices over the 13-15 m face, matching the vertical resolution of daily layers (median solid thickness 0.9-3.0 m). It also suits loader reclaim slices. Larger and smaller blocks were tested (tornado).
* **Discretisation / partial blocks**: layers are integrated exactly into blocks (the fraction of each layer's thickness inside each 2 m slice). No sub-blocking is needed: each block carries its **fill fraction** and true material volume; partial blocks are exported, not rounded.
* **Density**: per-load FMS density × κ for FMS material. Imputed density for unattributed fill. Mean FMS density for legacy. Block density = tonnes / volume (derived, never averaged).
* **Grade compositing / mixing**: tonnage-weighted via extensive metal. The within-block heterogeneity $s_{Cu} = \sqrt{\Sigma m g^2/\Sigma m - \bar g^2}$ is reported.
* **Provenance**: a sparse load × block tonnage matrix built from the stored transport plans. It gives the effective number of loads $n_\text{eff} = (\sum t)^2/\sum t^2$ and the top three contributing cycle IDs per block (traceability for reconciliation with mill results).
* **Uninformed regions**: legacy (pre-record) material and unattributed fill are kept in **separate tonnage fields**. A block's `info_class` is its dominant class. Geometry is flagged by `top_surveyed_frac`.

Fields exported per block: indices and centroid, dimensions, volume, fill fraction, tonnes, density, Cu %, Au g/t, Ag g/t, contained Cu (t), Au (kg), Ag (kg), tonnes by class, FMS-only grades, within-block SD, n_eff, top loads, mean placement date, surveyed-top fraction, Monte Carlo P10/P50/P90 and CV, information class and confidence class.

## 5.1 Confidence classification

| Class | Rule |
|---|---|
| High | ≥ 80% of tonnes FMS-tracked, Cu CV ≤ 10%, ≥ 50% of footprint has a surveyed top |
| Medium | ≥ 50% FMS-tracked and Cu CV ≤ 20% |
| Low | ≥ 20% FMS-tracked |
| Uninformed | < 20% FMS-tracked (legacy or unattributed dominated) |

These are internal planning classes, **not** JORC/NI 43-101 resource categories. Public reporting would require a Competent/Qualified Person.

# 6. Information types

| Quantity | Type |
|---|---|
| Dump X/Y, timestamp, payload, source grade, density | Measured (with stated errors) |
| Survey top/bottom surfaces in solid footprints | Measured |
| Survey time-of-day, file re-dating | Inferred from data |
| Floor plane, pre-record surface outside solids, front-of-face prior | Inferred |
| Legacy grade/density, unattributed grade, κ, φ in unsurveyed areas | Assumed |
| Location of each load inside the fill, block grades, uncertainty ranges | Model-generated |

# 7. Uncertainty methodology (Task 7)

**Monte Carlo** (60 realisations, seed 413). Each realisation runs the full reconstruction with jointly sampled inputs:

| Source | Sampling |
|---|---|
| Truck GPS error | X, Y + N(0, 3 m) per load |
| Tonnage measurement | × (1 + N(0, 0.08)) per load, × (1 + N(0, 0.03)) systematic |
| Assay / source grade | × (1 + N(0, 0.10)) per grade signature (Cu, Au, Ag independently) |
| Density / compaction | κ ~ U(0.80, 1.05) |
| Survey error | vertical bias N(0, 0.05 m) per survey |
| Survey timing | survey time ∈ {21:00, 22:00, 23:00, 23:59} |
| Degree of mixing | ε ~ U(2, 15) m |
| Unknown dozer trajectories | α ~ U(1, 10) |
| Movement distance | L_max ~ U(50, 130) m |
| Missing data | unattributed grade drawn by tonnage-weighted bootstrap of the period's loads |

Blocks are accumulated on the base block grid. For each block we report P10/P50/P90 and the coefficient of variation of Cu, Au and tonnes; for the whole stockpile we report P10/P50/P90 totals. **One-at-a-time sensitivity** (tornado) varies ε, α, $L_{\max}$, κ, σz, survey time, grid cell, block size and the A-13b switch individually.

# 8. Validation methodology (Task 6)

| Area | Metric |
|---|---|
| Geometry | RMSE, bias, P1/P99, volume difference of model top vs latest surveyed top; fraction within τ; error map |
| Mass balance | FMS tonnes in vs block model (by class); unattributed and retained volumes per period |
| Metal balance | Cu, Au, Ag in vs block model |
| Temporal | Forward model calibrated on periods 1-5, tested on 6-9 (unseen). Metrics: Wasserstein-1 (earth mover's) distance between predicted and observed fill (m), capture ratio (share of predicted volume inside observed fill), centroid error. Baseline: no dozer push |
| Inversion skill | Synthetic twin: truth generated with the forward model (push jitter 6 m), observed with GPS noise (3 m), payload noise (5%), 15% missing FMS records and survey noise. Block Cu/Au RMSE and correlation vs truth for CPST variants and baselines |
| Robustness | Grid 0.5/1/2.5 m, Sinkhorn tolerance, detection limit: totals, top-bench grade, mean absolute block change |

# 9. Implementation map

| Function | Module |
|---|---|
| Source scanning, hashing, readers | `spbm/io.py`, `spbm/dataset.py` |
| Rasterisation | `spbm/grid.py` |
| Floor, domain, inference | `spbm/surfaces.py` |
| QA/QC | `spbm/qaqc.py` |
| Periods, alignment, growth | `spbm/growth.py` |
| CPST engine | `spbm/movement.py` (`reconstruct`, `sinkhorn`, `geodesic_cost`) |
| Forward model | `spbm/forward.py` |
| Block model, exports | `spbm/blockmodel.py`, `spbm/bmviz.py` |
| Validation | `spbm/validation.py` |
| Uncertainty / sensitivity | `spbm/uncertainty.py` |
| Audit trail | `spbm/audit.py` |
| Orchestration / CLI | `spbm/pipeline.py`, `spbm/__main__.py` |

# References

* Monge, G. (1781). *Mémoire sur la théorie des déblais et des remblais.* Histoire de l'Académie Royale des Sciences de Paris.
* Cuturi, M. (2013). Sinkhorn distances: lightspeed computation of optimal transport. *Advances in Neural Information Processing Systems* 26.
* Peyré, G. and Cuturi, M. (2019). Computational optimal transport. *Foundations and Trends in Machine Learning* 11(5-6), 355-607.
* Chizat, L., Peyré, G., Schmitzer, B. and Vialard, F.-X. (2018). Scaling algorithms for unbalanced optimal transport problems. *Mathematics of Computation* 87, 2563-2609.
* Bak, P., Tang, C. and Wiesenfeld, K. (1987). Self-organized criticality: an explanation of 1/f noise. *Physical Review Letters* 59, 381-384 (sandpile cellular automata).
* Wheaton, J.M., Brasington, J., Darby, S.E. and Sear, D.A. (2010). Accounting for uncertainty in DEMs from repeat topographic surveys. *Earth Surface Processes and Landforms* 35, 136-156 (level of detection).
* Caterpillar Inc. *Caterpillar Performance Handbook* (current edition). Dozer production and grade-correction factors.
* Dijkstra, E.W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik* 1, 269-271.
