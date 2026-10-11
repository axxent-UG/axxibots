import test from "node:test";
import assert from "node:assert/strict";
import { NextRequest } from "next/server";
import { accessDecision, requireSiteAccess } from "../lib/access";
import { proxy } from "../proxy";
const password = "synthetic-only-test-password";
const basic = (user: string, pass: string) =>
  "Basic " + Buffer.from(`${user}:${pass}`).toString("base64");

test("access fails closed with missing, short or invalid server credentials", () => {
  assert.equal(accessDecision(null, undefined), "unconfigured");
  assert.equal(accessDecision(basic("alex", "short"), "short"), "unconfigured");
  assert.equal(accessDecision(null, password, "bad:user"), "unconfigured");
});
test("only correct username and password open the site", () => {
  assert.equal(accessDecision(basic("alex", password), password), "authorized");
  assert.equal(
    accessDecision(basic("someone-else", password), password),
    "unauthorized",
  );
  assert.equal(
    accessDecision(basic("alex", "incorrect-password"), password),
    "unauthorized",
  );
  assert.equal(accessDecision(null, password), "unauthorized");
});
test("malformed, oversized and bearer credentials are rejected", () => {
  for (const header of [
    "Basic !!!",
    "Basic " + Buffer.from("no-separator").toString("base64"),
    "Bearer something",
    "Basic " + "A".repeat(9000),
  ])
    assert.equal(accessDecision(header, password), "unauthorized");
});
test("UTF-8 and passwords containing colons are supported", () => {
  const pass = "unique-test:pässword:2026";
  assert.equal(accessDecision(basic("alex", pass), pass), "authorized");
});
test("pages, demo data, auth routes and assets all receive a password challenge", () => {
  const old = process.env.HQ_ACCESS_PASSWORD,
    oldUser = process.env.HQ_ACCESS_USER;
  process.env.HQ_ACCESS_PASSWORD = password;
  process.env.HQ_ACCESS_USER = "alex";
  try {
    for (const path of [
      "/",
      "/api/data",
      "/api/auth",
      "/_next/static/example.js",
    ]) {
      const req = new NextRequest("https://hq.example" + path, {
        headers: { "x-middleware-subrequest": "proxy" },
      });
      const response = proxy(req);
      assert.equal(response.status, 401);
      assert.match(
        response.headers.get("www-authenticate") ?? "",
        /AXXIBOTS HQ/,
      );
      assert.match(response.headers.get("cache-control") ?? "", /no-store/);
    }
    assert.equal(
      requireSiteAccess(new NextRequest("https://hq.example/api/data"))?.status,
      401,
    );
  } finally {
    if (old === undefined) delete process.env.HQ_ACCESS_PASSWORD;
    else process.env.HQ_ACCESS_PASSWORD = old;
    if (oldUser === undefined) delete process.env.HQ_ACCESS_USER;
    else process.env.HQ_ACCESS_USER = oldUser;
  }
});
test("valid credentials pass the request gate; absent environment keeps it locked", () => {
  const old = process.env.HQ_ACCESS_PASSWORD,
    oldUser = process.env.HQ_ACCESS_USER;
  process.env.HQ_ACCESS_PASSWORD = password;
  process.env.HQ_ACCESS_USER = "alex";
  try {
    const req = new NextRequest("https://hq.example/", {
      headers: { authorization: basic("alex", password) },
    });
    assert.equal(requireSiteAccess(req), null);
    assert.equal(proxy(req).headers.get("x-middleware-next"), "1");
    delete process.env.HQ_ACCESS_PASSWORD;
    assert.equal(proxy(req).status, 503);
  } finally {
    if (old === undefined) delete process.env.HQ_ACCESS_PASSWORD;
    else process.env.HQ_ACCESS_PASSWORD = old;
    if (oldUser === undefined) delete process.env.HQ_ACCESS_USER;
    else process.env.HQ_ACCESS_USER = oldUser;
  }
});
