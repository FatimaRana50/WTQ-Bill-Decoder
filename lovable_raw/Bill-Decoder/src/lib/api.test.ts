import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, API_URL } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("API error handling", () => {
  it("defaults to the supplied local REST URL", () => {
    expect(API_URL).toBe("http://localhost:8000");
  });
  it("treats missing expected values as no answer key", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    vi.stubGlobal("fetch", fetcher);
    expect(await api.expected("bill-id")).toBeNull();
    expect(fetcher.mock.calls[0]?.[0]).toBe("http://localhost:8000/api/expected/bill-id");
  });
  it("does not hide other expected-values errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    await expect(api.expected("bill-id")).rejects.toBeInstanceOf(ApiError);
  });
  it("turns unavailable health requests into friendly errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.health()).rejects.toThrow("We can't reach the bill service.");
  });
});
