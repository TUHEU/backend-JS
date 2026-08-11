/**
 * PM2 process definitions for the GlobeTrotter Phase 2 backend.
 *
 * Only api-gateway binds to 0.0.0.0 (publicly reachable). The three
 * backend services bind to 127.0.0.1 only — same "one externally
 * reachable port" property the Docker setup had, just enforced by
 * bind address instead of Docker's network isolation.
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 status
 *   pm2 logs gt-api-gateway
 *   pm2 save              # persist across reboots (with pm2 startup)
 */
const path = require('path');

const ROOT = __dirname;
const GUNICORN = path.join(ROOT, 'venv', 'bin', 'gunicorn');
const SECRET = process.env.GLOBETROTTER_SECRET || 'dev-secret-change-in-prod';

const GUNICORN_FLAGS = '--workers 2 --timeout 30 --access-logfile - --error-logfile -';

module.exports = {
  apps: [
    {
      name: 'gt-user-service',
      script: GUNICORN,
      args: `wsgi:app --bind 127.0.0.1:5005 ${GUNICORN_FLAGS}`,
      cwd: path.join(ROOT, 'user-service'),
      interpreter: 'none',
      env: { GLOBETROTTER_SECRET: SECRET },
    },
    {
      name: 'gt-itinerary-service',
      script: GUNICORN,
      args: `wsgi:app --bind 127.0.0.1:5006 ${GUNICORN_FLAGS}`,
      cwd: path.join(ROOT, 'itinerary-service'),
      interpreter: 'none',
      env: { GLOBETROTTER_SECRET: SECRET },
    },
    {
      name: 'gt-recommendation-service',
      script: GUNICORN,
      args: `wsgi:app --bind 127.0.0.1:5007 ${GUNICORN_FLAGS}`,
      cwd: path.join(ROOT, 'recommendation-service'),
      interpreter: 'none',
      env: {
        GLOBETROTTER_SECRET: SECRET,
        USER_SERVICE_URL: 'http://127.0.0.1:5005',
        ITINERARY_SERVICE_URL: 'http://127.0.0.1:5006',
      },
    },
    {
      name: 'gt-api-gateway',
      script: GUNICORN,
      args: `wsgi:app --bind 0.0.0.0:5004 ${GUNICORN_FLAGS}`,
      cwd: path.join(ROOT, 'api-gateway'),
      interpreter: 'none',
      env: {
        USER_SERVICE_URL: 'http://127.0.0.1:5005',
        ITINERARY_SERVICE_URL: 'http://127.0.0.1:5006',
        RECOMMENDATION_SERVICE_URL: 'http://127.0.0.1:5007',
      },
    },
  ],
};
