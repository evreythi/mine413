// Usage: node tools/html2pdf.js in.html out.pdf   (Chromium via Playwright)
const { chromium } = require('playwright');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + require('path').resolve(inp), { waitUntil: 'networkidle' });
  await page.pdf({ path: out, format: 'Letter', printBackground: true,
    margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
})();
