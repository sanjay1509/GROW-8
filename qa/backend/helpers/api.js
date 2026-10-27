export const API_BASE = `${process.env.API_URL || 'http://127.0.0.1:8000'}/api/v1`;
export const API_ORIGIN = process.env.API_URL || 'http://127.0.0.1:8000';

// The accounts/password below come from Grow8's DEVELOPMENT-ONLY seed SQL.
// Never reuse this password or this script against production.
export async function loginAs(request, email) {
  const response = await request.post(`${API_BASE}/auth/login`, {
    data: { email, password: process.env.SEED_PASSWORD || 'Grow8Dev!2026' },
  });
  if (!response.ok()) throw new Error(`Seeded login failed: ${response.status()} ${await response.text()}`);
  return (await response.json()).access_token;
}
