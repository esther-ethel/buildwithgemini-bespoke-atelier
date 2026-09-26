const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  console.log('Launching browser to capture live UI functionality screenshots...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  // 1. Initial UI Landing Page & Pattern Catalog
  console.log('Navigating to http://localhost:8080/...');
  await page.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const imagesDir = path.join(__dirname, 'docs', 'images');
  if (!fs.existsSync(imagesDir)) {
    fs.mkdirSync(imagesDir, { recursive: true });
  }

  console.log('Capturing Landing Page & Catalog view...');
  await page.screenshot({ path: path.join(imagesDir, 'ui_landing_catalog.png'), fullPage: false });

  // 2. Query 1: Catalog & Waistcoat Draft
  console.log('Sending Query 1: Show catalog and draft Old Money waistcoat...');
  const inputSelector = 'input#input';
  await page.fill(inputSelector, "Show me your catalog of bespoke tailored patterns and draft an Old Money linen waistcoat.");
  await page.keyboard.press('Enter');

  console.log('Waiting for Turn 1 response and A2UI cards (30s)...');
  await page.waitForTimeout(30000);

  console.log('Capturing Turn 1 A2UI Pattern Spec Cards...');
  await page.screenshot({ path: path.join(imagesDir, 'ui_pattern_spec_cards.png'), fullPage: false });

  // 3. Query 2: Technical Flat Sketch & Cut List
  console.log('Sending Query 2: Generate 2D technical flat sketch with welt pockets and show the fabric cut list table...');
  await page.fill(inputSelector, "Generate a 2D technical flat sketch for this waistcoat with welt pockets and show the fabric cut list table.");
  await page.keyboard.press('Enter');

  console.log('Waiting for Turn 2 response, Flat Sketch rendering & Cut List (35s)...');
  await page.waitForTimeout(35000);

  console.log('Capturing Technical Flat Sketch & Cut List UI...');
  await page.screenshot({ path: path.join(imagesDir, 'ui_technical_flat_cutlist.png'), fullPage: false });

  await browser.close();
  console.log('Successfully captured UI screenshots in docs/images/!');
})();
