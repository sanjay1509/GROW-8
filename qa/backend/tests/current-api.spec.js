import { expect, test } from "@playwright/test";

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";
const password = process.env.SEED_PASSWORD ?? "Grow8Dev!2026";

async function login(request, email) {
  const response = await request.post(`${apiUrl}/api/v1/auth/login`, {
    data: { email, password },
  });
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()).access_token;
}

test("API-001 @smoke Health reports live dependencies", async ({ request }) => {
  const response = await request.get(`${apiUrl}/health`);
  expect(response.status(), await response.text()).toBe(200);

  const body = await response.json();
  expect(body.status).toBe("ok");
  expect(body.checks).toMatchObject({ mysql: "ok", rabbitmq: "ok" });
});

test("API-002 @sanity Reference endpoints return populated categories and skills", async ({ request }) => {
  for (const resource of ["categories", "skills"]) {
    const response = await request.get(`${apiUrl}/api/v1/${resource}`);
    expect(response.status(), await response.text()).toBe(200);
    expect(await response.json()).toEqual(expect.arrayContaining([expect.objectContaining({})]));
  }
});

test("API-003 @sanity Login returns a token accepted by the current-user endpoint", async ({ request }) => {
  const token = await login(request, "alex.chen@grow8.dev");
  const response = await request.get(`${apiUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
  expect(await response.json()).toMatchObject({
    email: "alex.chen@grow8.dev",
    role: "contributor",
  });
});

test("API-004 @regression Received applications is creator-only", async ({ request }) => {
  const creatorToken = await login(request, "maple.bakery@grow8.dev");
  const creatorResponse = await request.get(`${apiUrl}/api/v1/applications/received`, {
    headers: { Authorization: `Bearer ${creatorToken}` },
  });
  expect(creatorResponse.status(), await creatorResponse.text()).toBe(200);
  const page = await creatorResponse.json();
  expect(Array.isArray(page.items)).toBe(true);
  expect(page.total).toBeGreaterThanOrEqual(page.items.length);

  const contributorToken = await login(request, "alex.chen@grow8.dev");
  const contributorResponse = await request.get(`${apiUrl}/api/v1/applications/received`, {
    headers: { Authorization: `Bearer ${contributorToken}` },
  });
  expect(contributorResponse.status()).toBe(403);
  expect((await contributorResponse.json()).error.code).toBe("ROLE_FORBIDDEN");
});
