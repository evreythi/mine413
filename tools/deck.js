// D7 presentation builder (pptxgenjs). Called by tools/make_presentation.py with a JSON data file.
const fs = require("fs");
const path = require("path");
const pptxgen = require(path.join(__dirname, "node_modules", "pptxgenjs"));

let RAW = fs.readFileSync(process.argv[2], "utf8");
const D0 = JSON.parse(RAW);
// substitute team names from config/team.yaml into every string ("[Member n]")
(D0.team && D0.team.members || []).forEach((m, i) => {
  const ph = `[Member ${i + 1}]`;
  if (m.name && m.name !== ph) RAW = RAW.split(ph).join(m.name);
});
const D = JSON.parse(RAW);
const MEMBER = i => { const m = (D.team && D.team.members || [])[i - 1]; return m && m.name ? m.name : `[Member ${i}]`; };
const TEAM_NAMES = (D.team && D.team.members || []).map(m => m.name).join(", ") || "[Member 1-5]";
const k = D.k;
const THEME = {
  name: "Copper Pit",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1D2329", lt1: "FFFFFF", dk2: "33424A", lt2: "EEF1F2",
    accent1: "B5652B", accent2: "D9A21B", accent3: "4F7A8C", accent4: "8A9499", accent5: "7A3A1A", accent6: "3E6B4F",
    hlink: "4F7A8C", folHlink: "7A3A1A",
  },
};
const H = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Pit I HG stockpile - reconstruction and block model";
pres.author = "MIN E 413 project team";
const C = pres.SchemeColor;

// ------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE_DARK", background: { color: H.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.1, w: 11.7, h: 1.7, fontSize: 40, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.95, w: 11.7, h: 1.6, fontSize: 18, color: C.accent2, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION_DARK", background: { color: H.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.6, w: 11.7, h: 1.2, fontSize: 38, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.95, w: 11.7, h: 0.8, fontSize: 18, color: C.accent2, valign: "top" }, text: "" } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.background2 },
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: H.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 0.95, fontSize: 30, bold: true, color: C.text1, valign: "middle" }, text: "" } },
    { text: { text: "MIN E 413  |  Pit I HG stockpile reconstruction", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: C.accent4 } } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent4 },
});

// ------------------------------------------------------------ helpers
const fmt = (v, d = 0) => Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
function fitImg(slide, key, x, y, w, h, name) {
  const f = D.figs[key];
  if (!f) return;
  const r = f.w / f.h;
  let ww = w, hh = w / r;
  if (hh > h) { hh = h; ww = h * r; }
  slide.addImage({ path: f.path, x: x + (w - ww) / 2, y: y + (h - hh) / 2, w: ww, h: hh, objectName: name || key });
}
function card(slide, x, y, w, h, big, label, color, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.08, objectName: name + "_bg" });
  slide.addText(big, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: h * 0.5, fontSize: 30, bold: true, color: color || C.accent1, fontFace: THEME.headFontFace, valign: "bottom", margin: 0, isTextBox: true, objectName: name + "_big" });
  slide.addText(label, { x: x + 0.2, y: y + h * 0.55 + 0.05, w: w - 0.4, h: h * 0.45 - 0.2, fontSize: 13, color: C.text2, valign: "top", margin: 0, isTextBox: true, objectName: name + "_lab" });
}
function bullets(slide, items, x, y, w, h, fs, name) {
  slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 8 } })),
    { x, y, w, h, fontSize: fs || 16, color: C.text1, valign: "top", isTextBox: true, objectName: name || "bullets" });
}
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}
function sectionSlide(title, sub, section) {
  pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  s.addText(sub, { placeholder: "body" });
  return s;
}
const inv = Object.fromEntries(D.inv.map(r => [r["class"], r]));
const F = inv["FMS-tracked (reconciled + provisional)"], U = inv["Unattributed (imputed grade)"], L = inv["Legacy (assumed grade)"], T = inv["TOTAL"];
const mcT = D.mc.total_tonnes, mcCu = D.mc.cu_t, mcAu = D.mc.au_kg;
const mcRP = D.mc.record_period_tonnes, mcRPCu = D.mc.record_period_cu_t;
const RPt = F.tonnes + U.tonnes, RPcu = F.cu_t + U.cu_t;
const SC = Object.fromEntries(D.scen.map(r => [r.scenario, r]));

// ------------------------------------------------------------ 1 title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
s.addText("Reconstructing the Pit I HG stockpile", { placeholder: "title" });
s.addText(`Material movement, 3-D block model and uncertainty\nMIN E 413 term project  |  Fall 2026  |  Team: ${TEAM_NAMES}`, { placeholder: "body" });
s.addNotes(`Presenter: ${MEMBER(1)} (project lead). Introduce the team and the Mine Manager's request: a defensible, updatable platform that reconstructs where truck-dumped material ended up in the long-term stockpile, and a block model of tonnage, grade, metal and uncertainty.`);

// ------------------------------------------------------------ 2 answer first
s = content(`The answer first: ${fmt(RPt / 1000, 1)} kt placed during the record, tied to surveyed fill`, "Opening");
card(s, 0.6, 1.5, 3.0, 2.1, `${fmt(RPt / 1000, 1)} kt`, `record-period inventory (P10-P90 ${fmt(mcRP[0] / 1000, 1)}-${fmt(mcRP[2] / 1000, 1)} kt)`, C.accent1, "c1");
card(s, 3.8, 1.5, 3.0, 2.1, `${fmt(F.tonnes / 1000, 1)} kt`, "FMS-tracked: measured tonnes and grades, placed by CPST", C.accent1, "c2");
card(s, 7.0, 1.5, 2.8, 2.1, `${fmt(U.tonnes / 1000, 1)} kt`, "unattributed: surveyed fill in FMS-gap intervals; grade imputed", C.accent3, "c3");
card(s, 10.0, 1.5, 2.75, 2.1, `${fmt(L.tonnes / 1000)} kt`, `pre-record core: inferred geometry, assumed grade (whole pile ${fmt(T.tonnes / 1000)} kt)`, C.accent4, "c4");
bullets(s, [
  `Record-period grade ${fmt(RPcu / RPt * 100, 2)}% Cu; contained Cu P10-P90 ${fmt(mcRPCu[0] / 1000, 2)}-${fmt(mcRPCu[2] / 1000, 2)} kt (as-supplied units, implausibly high: confirm with Geology).`,
  `Not included in those ranges: if the 47% volume excess is loads missing from the FMS (not bulking), the record period holds ${fmt(SC.X2.record_period_tonnes / 1000, 1)} kt. Confirming the FMS density basis settles it.`,
  "Plan reclaim on the FMS-tracked benches with P10/P90 ranges; sample the pre-record core before committing it to a production target.",
  "Reproducible with one command; every input hashed; an independent implementation (B) agrees to about 2%.",
], 0.6, 4.0, 12.1, 2.8, 15, "summary");
s.addNotes(`Presenter: ${MEMBER(1)}. State the main message before the detail. We lead with the material placed during the two-week record, because it is tied to surveyed volumes and measured grades. The pre-record core and the whole-pile total come second, clearly labelled. Say explicitly what the ranges do not include.`);

// ------------------------------------------------------------ data
sectionSlide("1  Data and QA/QC", `Presenter: ${MEMBER(2)} (data and QA/QC lead)`, "Data and QA/QC");
s = content("Each survey file is a change solid, not a surface", "Data and QA/QC");
fitImg(s, "solids", 0.5, 1.35, 8.4, 5.5);
bullets(s, [
  "Every grid cell is crossed by exactly two faces: top = this survey, bottom = previous surface",
  "Bottom of solid s equals top of solid s-1 to 0.000 m (P5-P95)",
  "So the files give measured daily fill directly, but only where change occurred",
  `${fmt(k.survey_volume_m3)} m³ in 10 solids, 03-15 to 03-29`,
], 9.1, 1.5, 3.7, 5.2, 15, "solid_facts");
s.addNotes(`Presenter: ${MEMBER(2)}. This was the key discovery in the data: the DXFs are Vulcan change solids. That is why each file looks like a crescent band, the active crest and face, rather than the whole pile.`);

s = content("Data-quality findings that shape the model", "Data and QA/QC");
const qa = [
  ["Payload is estimated", `${fmt(D.payload38 * 100)}% of payloads are multiples of 38 t (bucket passes): per-load error plus a systematic payload factor`],
  ["Grades are source values", `${D.n_sig} grade signatures repeated across 275 loads: correlated grade error`],
  ["Stuck GPS, unreliable Z", "14 loads (2.4 kt) share one default position: location treated as unknown, not invented. Dump Z not used"],
  ["Headers and names wrong", "DXF header says inches (data are metres); two files carry year 2025: re-dated by logged interventions MI-001/002"],
  ["FMS has real gaps", "03-23 to 03-27 and after 03-29 08:17. 03-17 (no dumps, no survey) was a non-dumping day, not an outage"],
  ["Cuts hidden in solids", "Solid bottoms up to 2 m below earlier surfaces: dozer cuts re-handled as sources"],
];
qa.forEach((q, i) => {
  const x = 0.6 + (i % 3) * 4.1, y = 1.5 + Math.floor(i / 3) * 2.65;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.85, h: 2.4, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.08, objectName: `qa${i}_bg` });
  s.addText(q[0], { x: x + 0.2, y: y + 0.15, w: 3.45, h: 0.55, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: `qa${i}_h` });
  s.addText(q[1], { x: x + 0.2, y: y + 0.75, w: 3.45, h: 1.5, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `qa${i}_t` });
});
s.addNotes(`Presenter: ${MEMBER(2)}. No record was deleted: ${D.qa.n_rules} named QA rules at record, file and dataset level, ${D.qa.n_trig} triggered, each with a documented treatment (D2). Emphasise that these findings changed the method: payload and grade error enter the Monte Carlo, Z is ignored, and gaps become an explicit 'unattributed' class.`);

s = content("A survey labelled D closes its interval at D+1 07:00", "Data and QA/QC");
fitImg(s, "align", 0.4, 1.35, 8.9, 3.4);
bullets(s, [
  "Survey time was not supplied: the cut-off was scanned 0-36 h after 00:00 of the survey date",
  `r = ${fmt(D.align_r, 3)} at D+1 07:00 vs ${fmt(D.align_r24, 3)} at midnight; ratio spread ${fmt(D.align_rcv, 2)} vs ${fmt(D.align_rcv24, 2)}`,
  "Independent evidence: dumping stops 06:00-07:30 and 18:30-20:00 (shift changes)",
  "Version 1 searched only 21:00-23:59 and stopped at the end of its range",
], 9.4, 1.5, 3.45, 5.2, 14, "align_facts");
s.addNotes(`Presenter: ${MEMBER(2)}. A data-driven choice of an unrecorded parameter (A-05), corroborated by an independent signal in the FMS. This was the largest sensitivity driver in version 1; inside the dump-free window it hardly matters any more.`);

s = content(`Measured fill is ${fmt(D.vf.f_v, 2)} × recorded tonnes ÷ density on every complete day`, "Data and QA/QC");
fitImg(s, "volfac", 0.4, 1.35, 8.9, 3.4);
bullets(s, [
  `Volume factor f_v = ${fmt(D.vf.f_v, 3)} on 7 complete intervals (P10-P90 ${fmt(D.vf.f_v_p10, 2)}-${fmt(D.vf.f_v_p90, 2)})`,
  `Calibrated on the first half, it predicts the second to ${fmt(D.vf.holdout_mae_fv * 100, 1)}% (density as in-pile: ${fmt(D.vf.holdout_mae_dens_as_inpile * 100)}%)`,
  "FMS-gap intervals (03-15, 03-27, 03-29) sit at 2.2-2.4: that fill is unattributed",
  "Same f_v as the independent implementation B (1.476)",
], 9.4, 1.5, 3.45, 5.2, 14, "vf_facts");
s.addNotes(`Presenter: ${MEMBER(2)}. f_v fixes the in-pile volume of each load. What it means in tonnes is the open question: bulking (base case, in-pile density ${fmt(D.vf.in_pile_density_base, 2)} t/m³), under-recorded payloads, or missing loads. See the scenario slide.`);

// ------------------------------------------------------------ algorithm
sectionSlide("2  Algorithm, and how far it can be trusted", `Presenter: ${MEMBER(3)} (algorithm lead)`, "Algorithm");
s = content("CPST: surveys say where, FMS says what, transport decides which", "Algorithm");
fitImg(s, "algo", 0.5, 1.3, 6.2, 5.6);
bullets(s, [
  "Sinks = observed fill per 1 m column; sources = truck loads, carried platform parcels, cut material",
  "Cost = dozer push work: slope-aware geodesic distance (uphill penalised, ≤ 90 m), a weak preference inside the measured fill (see the ablation)",
  "Entropy-regularised optimal transport (Sinkhorn): mixing length ε = 6 m",
  "Dummy nodes keep it honest: U = fill with no FMS source, R = FMS volume not yet on the face",
  "Every operation is linear in tonnes and metal, so conservation is exact",
], 6.9, 1.45, 5.9, 5.3, 15, "cpst");
s.addNotes(`Presenter: ${MEMBER(3)}. Optimal transport was invented by Monge in 1781 for moving cuts to fills, the same earthworks problem. Walk through questions A to J: initial placement (point parcel at dump X/Y), direction (least-work route), distance (capacity plus max push), downslope (the surveyed face is at repose), mixing (epsilon), reconciliation (column marginals = survey), mass and metal (exact), sequential updating (column state), numerical stability (tolerance, grid tests).`);

s = content("Push distances and the face advance are physically plausible", "Algorithm");
fitImg(s, "advance", 0.5, 1.3, 6.4, 5.6);
fitImg(s, "push", 7.1, 1.4, 5.7, 3.4);
bullets(s, ["Crest advanced about 30 m south in two weeks", "Reconstructed pushes are mostly tens of metres, well inside the dozer economic range"], 7.1, 5.0, 5.7, 1.8, 14, "adv_facts");
s.addNotes(`Presenter: ${MEMBER(3)}. Growth characterisation (Task 2): when each cell first received fill.`);

s = content("Independent tests: prediction and known-truth twin", "Algorithm");
fitImg(s, "fwdtest", 0.4, 1.35, 8.2, 2.8);
const tw = D.twin.filter(r => r.method && !String(r.method).startsWith("Reference"));
s.addChart(pres.charts.BAR, [{ name: "Cu RMSE", labels: D.twin.map(r => String(r.method).replace("Baseline: ", "").replace("Reference: ", "")), values: D.twin.map(r => r.cu_rmse) }],
  { x: 0.5, y: 4.25, w: 8.0, h: 2.6, barDir: "bar", chartColors: [H.accent3], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
    dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt", dataLabelColor: "33424A", showLegend: false, catAxisLabelFontSize: 10, valAxisLabelFontSize: 9,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E6E8", size: 0.5 }, catGridLine: { style: "none" },
    catAxisLabelColor: "33424A", valAxisLabelColor: "33424A", showTitle: true, title: "Twin experiment: block Cu RMSE vs truth (% Cu)", titleFontSize: 12, titleFontFace: "+mn-lt", titleColor: "33424A" });
const ft = D.fwd.filter(r => r.set.startsWith("test"));
const fp = ft.find(r => r.mode.startsWith("push (cal")), fb = ft.find(r => r.mode.startsWith("no-push")), fu = ft.find(r => r.mode.startsWith("uniform"));
bullets(s, [
  `Forward model on unseen intervals: earth-mover error ${fmt(fp.w1_m, 1)} m vs ${fmt(fb.w1_m, 1)} m without dozer push and ${fu ? fmt(fu.w1_m, 1) : "-"} m for uniform spreading`,
  "Physics alone predicts where fill lands only moderately well, which is why the surveys must constrain the allocation",
  `Twin: CPST block Cu r = ${fmt(D.twin[1].cu_corr, 2)}; block tonnage r = ${fmt(D.twin[1].tonnes_corr, 2)} (measured by the survey)`,
  (() => { const r = D.twin_alt.find(x => x.truth.startsWith("random") && x.method.startsWith("CPST")); const b = D.twin_alt.find(x => x.truth.startsWith("random") && x.method.startsWith("Baseline")); return `Stress test with a truth rule CPST does not assume (random crest): ${fmt(r.cu_rmse, 2)}% Cu RMSE, the same as the main twin`; })(),
], 8.8, 1.5, 4.0, 5.3, 13, "test_facts");
s.addNotes(`Presenter: ${MEMBER(3)}. Temporal validation uses periods never used for calibration. The twin experiment generates a stockpile with known truth (forward physics with random dozer deviations), observes it like the real one (GPS noise, 15% missing FMS records, survey noise) and reconstructs it blind.`);

s = content("What the push cost buys: an honest ablation", "Algorithm");
const truths = [["physics", "our push physics"], ["random", "random crest"], ["period-uniform", "uniform within interval"]];
const pick = (t, m) => { const r = D.twin_alt.find(x => x.truth.startsWith(t) && x.method.startsWith(m)); return r ? r.cu_rmse : null; };
s.addChart(pres.charts.BAR, [
  { name: "CPST (push cost)", labels: truths.map(t => t[1]), values: truths.map(t => pick(t[0], "CPST eps=6 m")) },
  { name: "flat cost (survey constraint only)", labels: truths.map(t => t[1]), values: truths.map(t => pick(t[0], "CPST eps=6, flat")) },
], { x: 0.5, y: 1.4, w: 7.4, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [H.accent1, H.accent3], showValue: true, dataLabelFormatCode: "0.00",
  dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt", dataLabelColor: "33424A", showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: "+mn-lt",
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 10, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E6E8", size: 0.5 },
  catGridLine: { style: "none" }, catAxisLabelColor: "33424A", valAxisLabelColor: "33424A", valAxisTitle: "block Cu RMSE vs truth (% Cu)", showValAxisTitle: true,
  valAxisTitleFontSize: 11, valAxisTitleFontFace: "+mn-lt", showTitle: true, title: "Synthetic twins: which truth generated the stockpile", titleFontSize: 13, titleFontFace: "+mn-lt", titleColor: "33424A" });
bullets(s, [
  `Push term helps by ${fmt(pick("physics", "CPST eps=6, flat") - pick("physics", "CPST eps=6 m"), 2)}% Cu only when the truth follows the same physics; it hurts otherwise`,
  `On the real data it moves block grades by ${fmt(D.flat_blk, 2)}% Cu on average; totals unchanged`,
  "Almost all of CPST's skill comes from the survey constraint and from keeping unrecorded volume apart",
  "Physically motivated and costs nothing, but on two weeks of data it cannot be shown to improve the answer: kept in the base case, both forms sampled in the Monte Carlo, tracers to settle it",
], 8.1, 1.45, 4.7, 5.4, 13, "abl_facts");
s.addNotes(`Presenter: ${MEMBER(3)}. Be direct: the ablation removes the push term entirely, so every load is spread over its interval's measured fill. The survey constraint survives every truth we tried; the push cost does not. We say so rather than leave it for the examiner to find.`);

// ------------------------------------------------------------ block model and validation
sectionSlide("3  Block model and validation", `Presenter: ${MEMBER(4)} (block model and validation lead)`, "Block model");
s = content("Block model: 5 × 5 × 2 m, Cu grade by bench", "Block model");
fitImg(s, "plans", 0.4, 1.3, 12.5, 5.6);
s.addNotes(`Presenter: ${MEMBER(4)}. Block size justified by GPS error plus mixing length (~5 m) horizontally and daily layer thickness vertically. Partial blocks keep their fill fraction. Grades are composited from metal over tonnes.`);

s = content("Tracked material forms a skin on the advancing face", "Block model");
fitImg(s, "sections", 0.4, 1.3, 7.6, 5.6);
fitImg(s, "classes", 8.1, 1.5, 4.8, 2.2);
bullets(s, ["Orange dashed = pre-record surface: everything below is the pre-record core, with an assumed grade", "Reclaim of the outer benches recovers mostly FMS-tracked material"], 8.2, 4.0, 4.6, 2.8, 14, "sec_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Show where measured and assumed information sit in 3-D.`);

s = content("Inventory by information and confidence class", "Block model");
s.addChart(pres.charts.BAR, [{ name: "tonnes (kt)", labels: ["FMS-tracked", "Unattributed", "Pre-record core"], values: [F.tonnes / 1000, U.tonnes / 1000, L.tonnes / 1000] }],
  { x: 0.6, y: 1.4, w: 5.8, h: 5.2, barDir: "bar", chartColors: [H.accent1, H.accent3, H.accent4], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
    dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelColor: "33424A", showLegend: false, catAxisLabelFontSize: 13, valAxisLabelFontSize: 10,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E6E8", size: 0.5 }, catGridLine: { style: "none" },
    catAxisLabelColor: "33424A", valAxisLabelColor: "33424A", showTitle: true, title: "Modelled tonnes by information class (kt)", titleFontSize: 13, titleFontFace: "+mn-lt", titleColor: "33424A" });
fitImg(s, "confidence", 6.6, 1.4, 6.2, 3.3);
bullets(s, [`High + Medium confidence: ${fmt((D.conf.High + D.conf.Medium) / 1000, 1)} kt`, "Classes are internal planning classes, not JORC/NI 43-101 categories"], 6.7, 5.0, 6.0, 1.7, 14, "conf_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. The pre-record core and unattributed grades are not measurements; they are reported separately.`);

s = content("Validation: exact balances, survey-matched geometry", "Block model");
card(s, 0.6, 1.5, 3.0, 1.9, "< 10⁻⁹", "relative mass and Cu/Au/Ag balance error (FMS in vs block model)", C.accent6, "v1");
card(s, 0.6, 3.6, 3.0, 1.9, `${fmt(D.geo.rmse_m, 2)} m`, `RMSE model vs latest survey; ${fmt(D.geo.frac_within_tau * 100, 1)}% of cells within 0.14 m`, C.accent6, "v2");
fitImg(s, "geometry", 3.9, 1.4, 8.9, 3.9);
bullets(s, ["Geometry is constrained by design, so it is a check on numerics. The independent tests are in the algorithm section", "Automated test enforces conservation on every code change"], 3.9, 5.5, 8.9, 1.3, 14, "val_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Visual agreement alone is not validation; these are quantitative.`);

// ------------------------------------------------------------ uncertainty, platform, recommendations
sectionSlide("4  Uncertainty, platform and recommendations", `Presenter: ${MEMBER(5)} (platform and uncertainty lead)`, "Uncertainty and platform");
s = content("Uncertainty: what moves the answer", "Uncertainty and platform");
fitImg(s, "tornado", 0.4, 1.3, 7.6, 5.6);
fitImg(s, "mchist", 8.1, 1.4, 4.8, 1.8);
bullets(s, [`Monte Carlo (60 runs): GPS, payload, payload factor, volume factor, assay, survey, cut-off, mixing, push, push-cost form`, `Record-period tonnes P10-P90 ${fmt(mcRP[0] / 1000, 1)}-${fmt(mcRP[2] / 1000, 1)} kt; whole pile ${fmt(mcT[0] / 1000)}-${fmt(mcT[2] / 1000)} kt`, "Block grade ranges for pre-record blocks use the load-scale prior, not false precision"], 8.2, 3.4, 4.6, 3.4, 13, "unc_facts");
s.addNotes(`Presenter: ${MEMBER(5)}. Distinguish measured, inferred, assumed and model-generated information. The pre-record grade is a scenario assumption whose range cannot be quantified from the supplied data.`);

s = content("A repeatable, auditable in-house platform", "Uncertainty and platform");
fitImg(s, "workflow", 0.4, 1.3, 8.0, 5.6);
bullets(s, ["One command: python -m spbm update", "Managed raw store: every input SHA-256 named and logged; a changed file needs a supersede intervention", "Manual interventions need a reason, author and date, or the run stops", "40-rule QA catalogue; 67 automated tests", "Run manifest, model history and automatic change report", "Open formats: CSV, VTK, ESRI grids"], 8.6, 1.5, 4.2, 5.3, 14, "platform");
s.addNotes(`Presenter: ${MEMBER(5)}. Demonstrate (or show the recorded demo of) examples/demo_update.sh: build the model to the 03-22 survey cut-off, then update with the later data and read the change report. Mention that version 2 combines our platform with the stronger ideas of an independent implementation (B), disclosed in Appendix A.`);

s = content("Two independent implementations agree", "Uncertainty and platform");
s.addTable([[{ text: "quantity", options: { bold: true, fill: { color: H.lt2 } } }, { text: "A (this platform)", options: { bold: true, fill: { color: H.lt2 } } },
             { text: "B (independent)", options: { bold: true, fill: { color: H.lt2 } } }]].concat(D.ximpl.map(r => r.map(c => ({ text: String(c) })))),
  { x: 0.6, y: 1.45, w: 7.9, colW: [3.5, 2.2, 2.2], fontSize: 12, fontFace: "Calibri", color: "1D2329", border: { type: "solid", pt: 0.5, color: "BDBBB3" }, rowH: 0.36, objectName: "ximpl" });
bullets(s, [
  "Different code, rasteriser, cut detection, reconciliation and block size",
  "Same survey cut-off, same volume factor, same intervals flagged as FMS gaps",
  "Record-period inventory within about 2%",
  "B's numbers are quoted from its own report; B's code was not run",
], 8.8, 1.5, 4.0, 5.2, 14, "ximpl_facts");
s.addNotes(`Presenter: ${MEMBER(5)}. Reproducibility is the platform's job; an independent second implementation reaching the same physical ratio from the same data is the strongest check we have. Version 2 adopted B's timing scan, volume-factor calibration, raw store and test philosophy (Appendix A).`);

s = content("Limitations and recommendations", "Uncertainty and platform");
const rec = [
  ["1", "Confirm the FMS density basis; test the pile density; calibrate buckets", "Resolves bulking vs missing tonnes (up to +47%)"],
  ["2", "Audit FMS completeness for 03-23 to 03-27 and after 03-29 08:17", "Converts unattributed volume to tracked material"],
  ["3", "Survey the whole pile now, and the original ground if records exist", "Removes most pre-record geometry uncertainty (A-13, A-14)"],
  ["4", "Density, moisture and grade sampling of the pre-record core", "Replaces assumed grades; confirms Cu/Au units"],
  ["5", "Record survey acquisition times; fix the DXF unit header", "Removes A-05; avoids unit errors downstream"],
];
rec.forEach((r, i) => {
  const y = 1.45 + i * 1.08;
  s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.12, w: 0.62, h: 0.62, fill: { color: H.accent1 }, line: { color: H.accent1 }, objectName: `rec${i}_dot` });
  s.addText(r[0], { x: 0.6, y: y + 0.12, w: 0.62, h: 0.62, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_n` });
  s.addText(r[1], { x: 1.45, y: y, w: 6.6, h: 0.86, fontSize: 16, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_t` });
  s.addText(r[2], { x: 8.2, y: y, w: 4.6, h: 0.86, fontSize: 14, color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_d` });
});
s.addNotes(`Presenter: ${MEMBER(5)}. Key limitations: the meaning of the volume excess; no full-pile or pre-pile survey; two weeks of FMS against a pile built over the life of Pit I; grades are source-block values; mixing parameters are uncalibrated without tracers.`);

// ------------------------------------------------------------ decision and practice
sectionSlide("5  The decision, and professional practice", `Presenter: ${MEMBER(1)} (project lead)`, "Decision and practice");
s = content("What does the 47% volume excess mean?", "Decision and practice");
fitImg(s, "scen", 0.4, 1.35, 7.9, 3.4);
bullets(s, [
  `Bulking (base): FMS density is a bank density, recorded tonnes correct: ${fmt(SC.S0.record_period_tonnes / 1000, 1)} kt`,
  `Up to 19% payload under-recording (largest load to ${fmt(SC.S1.largest_load_t)} t): ${fmt(SC.S1.record_period_tonnes / 1000, 1)} kt (inside the range)`,
  `All under-recording: loads of ${fmt(SC.X1.largest_load_t)} t, excluded`,
  `Loads missing from the FMS: ${fmt(SC.X2.record_period_tonnes / 1000, 1)} kt. Not included in the ranges, not excluded either`,
], 8.5, 1.45, 4.35, 5.3, 13, "scen_facts");
s.addText("Cheapest fix: confirm whether Dens is a bank or a loose density, and run a pile density test.", { x: 0.6, y: 5.1, w: 7.7, h: 0.8, fontSize: 16, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "scen_fix" });
s.addNotes(`Presenter: ${MEMBER(1)}. This is the decision we ask management to take: the volume of the FMS material is calibrated; how many tonnes it holds is not identifiable from volumes. Version 1 implicitly assumed missing loads and never tested bulking; version 2 reports all interpretations, and says plainly which one is outside the ranges.`);

s = content("Professional accountability and equity", "Decision and practice");
const cols2 = [
  ["Accountability", ["Never present a single expected value: lead with the record-period range and say what it excludes", "Pre-record grade is assumed: decline a 'definitive' whole-pile inventory until sampled", "We corrected our own version 1 after an independent comparison, and documented why"]],
  ["Equity and inclusion", ["Data gaps are periods and systems, not crews: no attribution without evidence", "Average imputation can bias exactly the least-documented zones: flag, do not hide", "Explainable outputs (maps, classes, provenance) for planners, operators and processing"]],
];
cols2.forEach((c, i) => {
  const x = 0.6 + i * 6.15;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 5.95, h: 4.3, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.08, objectName: `pp${i}_bg` });
  s.addText(c[0], { x: x + 0.3, y: 1.7, w: 5.35, h: 0.6, fontSize: 22, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: `pp${i}_h` });
  bullets(s, c[1], x + 0.3, 2.45, 5.4, 3.2, 18, `pp${i}_b`);
});
s.addText("Scenario response: management asked for a definitive inventory. We provide it with ranges and information classes, and state what the data cannot yet support.",
  { x: 0.6, y: 6.05, w: 12.1, h: 0.7, fontSize: 15, italic: true, color: C.text2, margin: 0, isTextBox: true, objectName: "pp_scenario" });
s.addNotes(`Presenter: ${MEMBER(1)}. Response to the course scenario (Section 6.2): management asks for a definitive inventory. Our position: provide it with ranges and classes, and state clearly what we cannot yet support.`);

// ------------------------------------------------------------ close
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Close" });
s.addText("Plan with ranges, sample the unknown, update every survey", { placeholder: "title" });
s.addText("Questions?\nAll results reproducible: python -m spbm run", { placeholder: "body" });
s.addNotes(`Presenter: ${MEMBER(1)}. Close and take questions. Any member may be asked about data treatment, assumptions, algorithm, validation, uncertainty, software or professional decisions.`);

// pptxgenjs writes Office's default palette into the theme; replace it with THEME
// so scheme colours resolve correctly in PowerPoint (uses the jszip bundled with pptxgenjs).
async function writeTheme(file, theme) {
  const JSZip = require(require.resolve("jszip", { paths: [path.join(__dirname, "node_modules", "pptxgenjs")] }));
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files).filter(n => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  const c = theme.colors;
  const sys = (tag, v) => `<a:${tag}><a:srgbClr val="${v}"/></a:${tag}>`;
  const scheme = `<a:clrScheme name="${theme.name}">` + sys("dk1", c.dk1) + sys("lt1", c.lt1) + sys("dk2", c.dk2) + sys("lt2", c.lt2) +
    ["accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"].map(k => sys(k, c[k])).join("") + `</a:clrScheme>`;
  for (const n of names) {
    let xml = await zip.file(n).async("string");
    xml = xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme).replace(/(<a:theme[^>]*name=")[^"]*"/, `$1${theme.name}"`);
    zip.file(n, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

pres.writeFile({ fileName: D.out }).then(async (f) => {
  await writeTheme(D.out, THEME);
  console.log("written", f);
});
