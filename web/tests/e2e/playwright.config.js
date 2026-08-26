// Playwright konfiguracija za Dentaland E2E testove (DENT-IMPROVE-011).
//
// Pokreće DVA webServer-a automatski prije testova:
//   1. FastAPI backend (uvicorn) na 127.0.0.1:8000, sa izolovanom test bazom
//      (DENTALAND_DB_PATH → temp fajl, ne postojeća dev/produkcijska baza).
//      SMTP env varijable se NAMJERNO ne postavljaju → email slanje je no-op
//      (send_booking_confirmation preskače kad DENTALAND_SMTP_HOST nedostaje).
//   2. Statičan web server (python -m http.server) na 127.0.0.1:8080 koji
//      servira web/ folder.
//
// CORS je već otvoren (allow_origins=["*"]) — cross-port 8080 → 8000 radi.
//
// workers: 1 je NAMJERNO — rate limiter je 10/minute po IP-u (127.0.0.1),
// pa testovi moraju ići sekvencijalno da 429 scenario bude determinističan.

const os = require('os');
const path = require('path');
const { defineConfig } = require('@playwright/test');

// web/tests/e2e → repo root = 3 nivoa gore.
const REPO_ROOT = path.join(__dirname, '..', '..', '..');
// web/tests/e2e → web/ = 2 nivoa gore.
const WEB_DIR = path.join(__dirname, '..', '..');
const TEST_DB = path.join(os.tmpdir(), `dentaland-e2e-${process.pid}.db`);

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000',
      cwd: REPO_ROOT,
      url: 'http://127.0.0.1:8000/docs',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        ...process.env,
        PYTHONPATH: 'src',
        DENTALAND_DB_PATH: TEST_DB,
      },
    },
    {
      command: 'python -m http.server 8080 --bind 127.0.0.1',
      cwd: WEB_DIR,
      url: 'http://127.0.0.1:8080/index.html',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
