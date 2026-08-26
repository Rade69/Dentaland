// DENT-IMPROVE-011 — Playwright E2E testovi javne forme.
//
// Testira STVARAN backend (uvicorn na 127.0.0.1:8000) i STVARAN statičan web
// (python -m http.server na 127.0.0.1:8080) — bez mock-ovanog fetch-a.
// Sintetski podaci, nema stvarnih pacijenata. SMTP nije konfigurisan, pa
// email potvrde idu no-op putem.

const { test, expect } = require('@playwright/test');

const BACKEND_URL = 'http://127.0.0.1:8000';

async function pickAvailableDay(page) {
  // Prvi omogućeni dan u kalendaru tekućeg mjeseca (ne prošli, ne nedjelja).
  await page.locator('#calendar-grid button:not([disabled])').first().click();
}

async function fillDetails(page, { ime = 'Test Pacijent', telefon = '061111222' } = {}) {
  await page.locator('#full-name').fill(ime);
  await page.locator('#phone').fill(telefon);
  await page.locator('#consent').check();
}

test('1 — validan submit vraca 201 i prikazuje potvrdu', async ({ page }) => {
  await page.goto('/');
  await pickAvailableDay(page);
  await fillDetails(page);

  const responsePromise = page.waitForResponse(
    (r) => r.url().includes('/api/booking-requests') && r.request().method() === 'POST',
  );
  await page.locator('#continue-button').click();
  const response = await responsePromise;

  expect(response.status()).toBe(201);
  await expect(page.getByText('ZAHTJEV PRIMLJEN!')).toBeVisible();
});

test('2 — prazno obavezno polje onemogucava nastavak', async ({ page }) => {
  await page.goto('/');
  await pickAvailableDay(page);

  await page.locator('#phone').fill('061111222');
  await page.locator('#consent').check();
  await page.locator('#full-name').fill(''); // ime ostaje prazno (obavezno)

  await expect(page.locator('#continue-button')).toBeDisabled();
});

test('3 — backend nedostupan prikazuje poruku korisniku', async ({ page }) => {
  // Usmjeri formu na nedostupni port PRIJE nego se app.js učita.
  await page.addInitScript(() => {
    window.DENTALAND_API_BASE = 'http://127.0.0.1:9999';
  });

  await page.goto('/');
  await pickAvailableDay(page);
  await fillDetails(page);
  await page.locator('#continue-button').click();

  const error = page.locator('.submit-error');
  await expect(error).toBeVisible();
  await expect(error).not.toHaveText('');
});

test('4 — 429 rate limit prikazuje jasnu poruku', async ({ page }) => {
  // Iscrpi rate limiter (10/minute po IP-u) sintetskim zahtjevima direktno na
  // API; UI submit je onda 11.+ zahtjev → 429.
  const future = new Date();
  future.setDate(future.getDate() + 14);
  const iso = [
    future.getFullYear(),
    String(future.getMonth() + 1).padStart(2, '0'),
    String(future.getDate()).padStart(2, '0'),
  ].join('-');

  const payload = { ime: 'Rate Test', telefon: '061000000', email: '', requested_date: iso };
  for (let i = 0; i < 12; i += 1) {
    await page.request.post(`${BACKEND_URL}/api/booking-requests`, { data: payload });
  }

  await page.goto('/');
  await pickAvailableDay(page);
  await fillDetails(page);
  await page.locator('#continue-button').click();

  const error = page.locator('.submit-error');
  await expect(error).toBeVisible();
  await expect(error).toContainText('Previše zahtjeva');
});

test.describe('6 — mobile viewport', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('forma je upotrebljiva na mobilnoj rezoluciji', async ({ page }) => {
    await page.goto('/');

    await expect(
      page.getByRole('heading', { name: 'ZAKAŽITE SVOJ TERMIN' }),
    ).toBeVisible();
    await expect(page.locator('#calendar-grid')).toBeVisible();

    await pickAvailableDay(page);
    await expect(page.locator('#details-card')).toHaveClass(/current-step/);
    await expect(page.locator('#full-name')).toBeVisible();
  });
});

test('7 — privacy link vodi na privacy.html', async ({ page }) => {
  await page.goto('/');

  const popupPromise = page.waitForEvent('popup');
  await page.locator('a[href="privacy.html"]').first().click();
  const popup = await popupPromise;

  await popup.waitForLoadState();
  expect(popup.url()).toContain('privacy.html');
});
