#!/usr/bin/env node
// Screenshot each page-element of a print-design HTML at high DPI.
// Why screenshots, not page.pdf(): Chrome mis-paints `transform: scale()` page
// artboards during PDF pagination (fits page using pre-transform box -> content
// squashes into top-left). Element screenshots capture post-transform pixels correctly.
//
// Usage: node shoot.js <LIVE_HTML_URL> <OUTDIR> [dpi=384] [selector=.sheet]
//   dpi 384 (default) / 480 for extra crispness (match source photo res; 300 is the floor).
//   Pass the SAME dpi to assemble_pdf.py so page boxes size correctly.
//   Render the LIVE url so relative ../images/ assets and webfonts resolve.

const puppeteer = require('puppeteer-core');
const CHROME = process.env.CHROME_PATH
  || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const URL = process.argv[2];
const OUTDIR = process.argv[3];
const DPI = parseFloat(process.argv[4] || '384');
const DSF = DPI / 96;                 // CSS px are 96/in; deviceScaleFactor maps DPI -> pixels
const SEL = process.argv[5] || '.sheet';

if (!URL || !OUTDIR) {
  console.error('Usage: node shoot.js <LIVE_HTML_URL> <OUTDIR> [dpi=384] [selector=.sheet]');
  process.exit(2);
}

(async () => {
  const b = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'shell',
    args: ['--no-sandbox', '--force-color-profile=srgb', '--high-dpi-support=1',
           '--font-render-hinting=none', '--disable-lcd-text'],
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1400, height: 1100, deviceScaleFactor: DSF });
  await p.goto(URL, { waitUntil: 'networkidle0', timeout: 180000 });

  const broken = await p.evaluate(async () => {
    await document.fonts.ready;
    const imgs = Array.from(document.images);
    await Promise.all(imgs.map(i => (i.complete && i.naturalWidth) ? null :
      new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
    document.querySelectorAll('.toolbar,.hint').forEach(e => e.style.display = 'none');
    return Array.from(document.images).filter(i => !i.naturalWidth).map(i => i.src);
  });

  const pages = await p.$$(SEL);
  console.log(`pages: ${pages.length} | ${DPI} DPI (dsf ${DSF}) | selector: ${SEL}`);
  broken.forEach(s => console.log('  BROKEN IMAGE:', s));
  if (!pages.length) { console.error(`No elements match "${SEL}". Check the selector.`); process.exit(1); }

  const fs = require('fs'); fs.mkdirSync(OUTDIR, { recursive: true });
  for (let i = 0; i < pages.length; i++) {
    const n = String(i + 1).padStart(2, '0');
    await pages[i].screenshot({ path: `${OUTDIR}/sheet-${n}.png`, type: 'png', captureBeyondViewport: true });
    process.stdout.write(`  shot ${n}/${pages.length}\r`);
  }
  console.log(`\nDONE -> ${OUTDIR}`);
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });