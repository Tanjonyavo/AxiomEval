// Print every HTML file of docs/pedagogie/build to PDF with Chromium (Playwright).
// Usage: node tools/pedagogie/print.mjs <path-to-playwright-index.mjs>
import { readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const playwright = await import(pathToFileURL(process.argv[2]).href);
const build = resolve('docs/pedagogie/build');
const out = resolve('docs/pedagogie/PDF');
const browser = await playwright.chromium.launch();
for (const name of readdirSync(build).filter((f) => f.endsWith('.html'))) {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(join(build, name)).href, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.pdf({
    path: join(out, name.replace(/\.html$/, '.pdf')), format: 'Letter', printBackground: true,
    preferCSSPageSize: true, displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;font-size:8pt;color:#666;padding:0 0.6in;display:flex;justify-content:space-between;font-family:Calibri,Arial"><span>AxiomEval — ' + name.replace(/\.html$/, '') + '</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  await page.close();
  console.log('ok', name);
}
await browser.close();
