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

// ------------------------------------------------------------ 1 title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
s.addText("Reconstructing the Pit I HG stockpile", { placeholder: "title" });
s.addText(`Material movement, 3-D block model and uncertainty\nMIN E 413 term project  |  Fall 2026  |  Team: ${TEAM_NAMES}`, { placeholder: "body" });
s.addNotes(`Presenter: ${MEMBER(1)} (project lead). Introduce the team and the Mine Manager's request: a defensible, updatable platform that reconstructs where truck-dumped material ended up in the long-term stockpile, and a block model of tonnage, grade, metal and uncertainty.`);

// ------------------------------------------------------------ 2 answer first
s = content("The answer first: one fifth of the pile has a measured grade basis", "Opening");
card(s, 0.6, 1.5, 2.95, 2.1, `${fmt(T.tonnes / 1000)} kt`, `modelled stockpile (P10-P90 ${fmt(mcT[0] / 1000)}-${fmt(mcT[2] / 1000)} kt)`, C.text1, "c1");
card(s, 3.75, 1.5, 2.95, 2.1, `${fmt(F.tonnes / 1000, 1)} kt`, `FMS-tracked (${fmt(F.share_of_tonnes * 100)}%): placed by CPST, mass and metal conserved exactly`, C.accent1, "c2");
card(s, 6.9, 1.5, 2.95, 2.1, `${fmt(U.tonnes / 1000, 1)} kt`, `unattributed (${fmt(U.share_of_tonnes * 100)}%): surveyed volume with no FMS record; grade imputed`, C.accent3, "c3");
card(s, 10.05, 1.5, 2.7, 2.1, `${fmt(L.tonnes / 1000, 1)} kt`, `legacy (${fmt(L.share_of_tonnes * 100)}%): pre-record pile; grade assumed`, C.accent4, "c4");
bullets(s, [
  `Best-estimate grade ${fmt(T.cu_pct, 2)}% Cu and ${fmt(T.au_gpt, 2)} g/t Au; contained Cu P10-P90 ${fmt(mcCu[0] / 1000, 1)}-${fmt(mcCu[2] / 1000, 1)} kt, Au ${fmt(mcAu[0] / 31.1035, 1)}-${fmt(mcAu[2] / 31.1035, 1)} koz.`,
  "Recommendation: plan reclaim on the FMS-tracked benches with P10/P90 ranges; sample the legacy core before committing it to a production target.",
  "Grades and metal are as supplied (8.4% Cu, 8.0 g/t Au is implausibly high): units must be confirmed with Geology before any economic use.",
  "Everything is reproducible with one command and auditable to the input file hash.",
], 0.6, 4.0, 12.1, 2.8, 16, "summary");
s.addNotes(`Presenter: ${MEMBER(1)}. State the main message before the detail. The FMS covers only two weeks; most of the pile pre-dates the record. We never mix measured, imputed and assumed numbers without labelling them.`);

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
  ["Payload is estimated", `${fmt(D.payload38 * 100)}% of payloads are multiples of 38 t (bucket passes): CV 8% tonnage error modelled`],
  ["Grades are source values", `${D.n_sig} grade signatures repeated across 275 loads: correlated grade error`],
  ["Dump Z unreliable; stuck GPS", "Z vs surface P10/P90 -2.8/+2.0 m; 14 loads (2.4 kt) share one default position: X/Y imputed"],
  ["Two files mis-dated", "Topo_2503xx re-dated to 2026-03-28/29 via a logged override, not by renaming"],
  ["FMS has gaps", "No records 03-17, 03-23 to 03-27; 56 h silence 03-16 to 03-18 while 4,843 m³ was placed"],
  ["Cuts hidden in solids", "Solid bottoms up to 2 m below earlier surfaces: dozer cuts re-handled as sources"],
];
qa.forEach((q, i) => {
  const x = 0.6 + (i % 3) * 4.1, y = 1.5 + Math.floor(i / 3) * 2.65;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.85, h: 2.4, fill: { color: H.lt2 }, line: { color: H.lt2 }, rectRadius: 0.08, objectName: `qa${i}_bg` });
  s.addText(q[0], { x: x + 0.2, y: y + 0.15, w: 3.45, h: 0.55, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: `qa${i}_h` });
  s.addText(q[1], { x: x + 0.2, y: y + 0.75, w: 3.45, h: 1.5, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `qa${i}_t` });
});
s.addNotes(`Presenter: ${MEMBER(2)}. No record was deleted: 14 flags, each with a documented treatment (D2). Emphasise that these findings changed the method: payload and grade error enter the Monte Carlo, Z is ignored, and gaps become an explicit 'unattributed' class.`);

s = content(`Surveys represent the end of the day (r = ${fmt(D.align_r, 2)})`, "Data and QA/QC");
fitImg(s, "align", 0.5, 1.4, 8.6, 3.6);
bullets(s, [
  "Survey time was not supplied",
  `Assigning loads to periods with survey time 23:59 gives r = ${fmt(D.align_r, 2)} between FMS volume and surveyed volume`,
  `Any time before 10:00 gives r ≤ ${fmt(D.align_morning_r, 2)}`,
  "Sensitivity: 21:00-23:59 sampled in the Monte Carlo",
], 9.3, 1.5, 3.5, 5.2, 15, "align_facts");
s.addNotes(`Presenter: ${MEMBER(2)}. A data-driven choice of an unrecorded parameter, documented as assumption A-05.`);

s = content("FMS explains only part of the surveyed fill", "Data and QA/QC");
s.addChart(pres.charts.BAR, [
  { name: "Observed fill (survey)", labels: D.periods.map(p => p.label), values: D.periods.map(p => Math.round(p.fill)) },
  { name: "FMS volume available", labels: D.periods.map(p => p.label), values: D.periods.map(p => Math.round(p.fms)) },
  { name: "Unattributed", labels: D.periods.map(p => p.label), values: D.periods.map(p => Math.round(p.unatt)) },
], { x: 0.6, y: 1.4, w: 8.6, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [H.accent3, H.accent1, H.accent4],
  showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: "+mn-lt",
  valAxisTitle: "m³", showValAxisTitle: true, valAxisTitleFontSize: 11, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
  valGridLine: { color: "E3E6E8", size: 0.5 }, catGridLine: { style: "none" }, catAxisLabelColor: "33424A", valAxisLabelColor: "33424A",
  showTitle: true, title: "Fill vs FMS volume per survey period (* = gap period)", titleFontSize: 13, titleFontFace: "+mn-lt", titleColor: "33424A" });
bullets(s, [
  "Volume not explained by FMS becomes 'unattributed' material with an imputed grade, never invented loads",
  "Complete days: apparent density 1.67 t/m³ vs FMS 2.06 t/m³: swell or missing loads (cannot be separated)",
  "Dozer lag: 03-20 surplus carried to 03-21",
], 9.4, 1.5, 3.4, 5.2, 14, "recon_facts");
s.addNotes(`Presenter: ${MEMBER(2)}. Distinguish physical explanations (swell, dozer lag) from data limitations (FMS outages, missing surveys).`);

// ------------------------------------------------------------ algorithm
sectionSlide("2  Material-movement algorithm", `Presenter: ${MEMBER(3)} (algorithm lead)`, "Algorithm");
s = content("CPST: surveys say where, FMS says what, push work says which", "Algorithm");
fitImg(s, "algo", 0.5, 1.3, 6.2, 5.6);
bullets(s, [
  "Sinks = observed fill per 1 m column; sources = truck loads, carried platform parcels, cut material",
  "Cost = dozer push work: slope-aware geodesic distance (uphill penalised, ≤ 90 m)",
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

// ------------------------------------------------------------ block model, validation, uncertainty
sectionSlide("3  Block model, validation and uncertainty", `Presenter: ${MEMBER(4)} (block model and validation lead)`, "Block model");
s = content("Block model: 5 × 5 × 2 m, Cu grade by bench", "Block model");
fitImg(s, "plans", 0.4, 1.3, 12.5, 5.6);
s.addNotes(`Presenter: ${MEMBER(4)}. Block size justified by GPS error plus mixing length (~5 m) horizontally and daily layer thickness vertically. Partial blocks keep their fill fraction. Grades are composited from metal over tonnes.`);

s = content("Tracked material forms a skin on the advancing face", "Block model");
fitImg(s, "sections", 0.4, 1.3, 7.6, 5.6);
fitImg(s, "classes", 8.1, 1.5, 4.8, 2.2);
bullets(s, ["Orange dashed = pre-record surface: everything below is legacy material with an assumed grade", "Reclaim of the outer benches recovers mostly FMS-tracked material"], 8.2, 4.0, 4.6, 2.8, 14, "sec_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Show where measured and assumed information sit in 3-D.`);

s = content("Inventory by information and confidence class", "Block model");
s.addChart(pres.charts.BAR, [{ name: "tonnes (kt)", labels: ["FMS-tracked", "Unattributed", "Legacy"], values: [F.tonnes / 1000, U.tonnes / 1000, L.tonnes / 1000] }],
  { x: 0.6, y: 1.4, w: 5.8, h: 5.2, barDir: "bar", chartColors: [H.accent1, H.accent3, H.accent4], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
    dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelColor: "33424A", showLegend: false, catAxisLabelFontSize: 13, valAxisLabelFontSize: 10,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E6E8", size: 0.5 }, catGridLine: { style: "none" },
    catAxisLabelColor: "33424A", valAxisLabelColor: "33424A", showTitle: true, title: "Modelled tonnes by information class (kt)", titleFontSize: 13, titleFontFace: "+mn-lt", titleColor: "33424A" });
fitImg(s, "confidence", 6.6, 1.4, 6.2, 3.3);
bullets(s, [`High + Medium confidence: ${fmt((D.conf.High + D.conf.Medium) / 1000, 1)} kt`, "Classes are internal planning classes, not JORC/NI 43-101 categories"], 6.7, 5.0, 6.0, 1.7, 14, "conf_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Legacy and unattributed grades are not measurements; they are reported separately.`);

s = content("Validation: exact balances, survey-matched geometry", "Block model");
card(s, 0.6, 1.5, 3.0, 1.9, "< 10⁻⁹", "relative mass and Cu/Au/Ag balance error (FMS in vs block model)", C.accent6, "v1");
card(s, 0.6, 3.6, 3.0, 1.9, `${fmt(D.geo.rmse_m, 2)} m`, `RMSE model vs latest survey; ${fmt(D.geo.frac_within_tau * 100, 1)}% of cells within 0.14 m`, C.accent6, "v2");
fitImg(s, "geometry", 3.9, 1.4, 8.9, 3.9);
bullets(s, ["Geometry is constrained by design, so it is a check on numerics. Independent tests are on the next slide", "Automated test enforces conservation on every code change"], 3.9, 5.5, 8.9, 1.3, 14, "val_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Visual agreement alone is not validation; these are quantitative.`);

s = content("Independent tests: prediction and known-truth twin", "Block model");
fitImg(s, "fwdtest", 0.4, 1.35, 8.2, 2.8);
const tw = D.twin.filter(r => r.method && !String(r.method).startsWith("Reference"));
s.addChart(pres.charts.BAR, [{ name: "Cu RMSE", labels: D.twin.map(r => String(r.method).replace("Baseline: ", "").replace("Reference: ", "")), values: D.twin.map(r => r.cu_rmse) }],
  { x: 0.5, y: 4.25, w: 8.0, h: 2.6, barDir: "bar", chartColors: [H.accent3], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
    dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt", dataLabelColor: "33424A", showLegend: false, catAxisLabelFontSize: 10, valAxisLabelFontSize: 9,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E6E8", size: 0.5 }, catGridLine: { style: "none" },
    catAxisLabelColor: "33424A", valAxisLabelColor: "33424A", showTitle: true, title: "Twin experiment: block Cu RMSE vs truth (% Cu)", titleFontSize: 12, titleFontFace: "+mn-lt", titleColor: "33424A" });
const ft = D.fwd.filter(r => r.set.startsWith("test"));
const fp = ft.find(r => r.mode.startsWith("push (cal")), fb = ft.find(r => r.mode.startsWith("no-push"));
bullets(s, [
  `Forward model on unseen periods: earth-mover error ${fmt(fp.w1_m, 1)} m vs ${fmt(fb.w1_m, 1)} m without dozer push`,
  "Physics alone predicts where fill lands only moderately well, which is why the surveys must constrain the allocation",
  `Twin: CPST block Cu r = ${fmt(D.twin[1].cu_corr, 2)}; beats period-average and global-mean baselines`,
  (() => { const r = D.twin_alt.find(x => x.truth.startsWith("random") && x.method.startsWith("CPST")); const b = D.twin_alt.find(x => x.truth.startsWith("random") && x.method.startsWith("Baseline")); return `Stress test with a truth rule CPST does not assume (random crest): ${fmt(r.cu_rmse, 2)}% vs ${fmt(b.cu_rmse, 2)}% Cu RMSE`; })(),
], 8.8, 1.5, 4.0, 5.3, 13, "test_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Temporal validation uses periods never used for calibration. The twin experiment generates a stockpile with known truth (forward physics with random dozer deviations), observes it like the real one (GPS noise, 15% missing FMS records, survey noise) and reconstructs it blind.`);

s = content("Uncertainty: what moves the answer", "Block model");
fitImg(s, "tornado", 0.4, 1.3, 7.6, 5.6);
fitImg(s, "mchist", 8.1, 1.4, 4.8, 1.8);
bullets(s, [`Monte Carlo (60 runs): GPS, payload, assay, density, survey, timing, mixing, push`, `Total tonnes P10-P90 ${fmt(mcT[0] / 1000)}-${fmt(mcT[2] / 1000)} kt, driven by density/swell and the legacy volume`, "Block grade ranges for legacy blocks use the load-scale prior, not false precision"], 8.2, 3.4, 4.6, 3.4, 13, "unc_facts");
s.addNotes(`Presenter: ${MEMBER(4)}. Distinguish measured, inferred, assumed and model-generated information. Global ranges cover the FMS-informed uncertainty; the legacy grade is a scenario assumption whose range cannot be quantified from the supplied data.`);

// ------------------------------------------------------------ platform & practice
sectionSlide("4  Platform and professional practice", `Presenter: ${MEMBER(5)} (platform lead) with ${MEMBER(1)}`, "Platform and practice");
s = content("A repeatable, auditable in-house platform", "Platform and practice");
fitImg(s, "workflow", 0.4, 1.3, 8.0, 5.6);
bullets(s, ["One command: python -m spbm update", "Input files hashed; every manual intervention logged with reason and approver", "Run manifest: code commit, library versions, configuration hash", "Model history and automatic change report", "Open formats: CSV, VTK, ESRI grids"], 8.6, 1.5, 4.2, 5.3, 15, "platform");
s.addNotes(`Presenter: ${MEMBER(5)}. Demonstrate (or show the recorded demo of) examples/demo_update.sh: build the model to 22 March, then update with the later data and read the change report.`);

s = content("Professional accountability and equity", "Platform and practice");
const cols2 = [
  ["Accountability", ["Never present a single expected value: report P10/P50/P90 and the class split", "Legacy grade is assumed: decline a 'definitive' inventory until sampled", "Independent review of code and assumptions before operational use; AI use disclosed and verified"]],
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
s.addNotes(`Presenter: ${MEMBER(1)} and ${MEMBER(5)}. Response to the course scenario (Section 6.2): management asks for a definitive inventory. Our position: provide it with ranges and classes, and state clearly what we cannot yet support.`);

s = content("Limitations and recommendations", "Platform and practice");
const rec = [
  ["1", "Survey the whole pile now, and the original ground if records exist", "Removes most legacy-geometry uncertainty (A-13, A-14)"],
  ["2", "Audit FMS completeness for 03-16 to 03-18 and 03-22 to 03-28", "Converts unattributed volume to tracked material"],
  ["3", "Density, moisture and grade sampling of the legacy core", "Replaces assumed grades; confirms Cu/Au units"],
  ["4", "Tracer trials and mill reconciliation by block", "Calibrates mixing length and push model"],
  ["5", "Export full-pile surfaces daily with a recorded survey time", "Removes A-05 and the toe-clipping artefacts"],
];
rec.forEach((r, i) => {
  const y = 1.45 + i * 1.08;
  s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.12, w: 0.62, h: 0.62, fill: { color: H.accent1 }, line: { color: H.accent1 }, objectName: `rec${i}_dot` });
  s.addText(r[0], { x: 0.6, y: y + 0.12, w: 0.62, h: 0.62, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_n` });
  s.addText(r[1], { x: 1.45, y: y, w: 6.6, h: 0.86, fontSize: 16, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_t` });
  s.addText(r[2], { x: 8.2, y: y, w: 4.6, h: 0.86, fontSize: 14, color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: `rec${i}_d` });
});
s.addNotes(`Presenter: ${MEMBER(5)}. Key limitations: no full-pile or pre-pile survey; two weeks of FMS against a pile built over the life of Pit I; grades are source-block values; mixing parameters are uncalibrated without tracers.`);

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
