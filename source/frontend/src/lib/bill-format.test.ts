import { describe, expect, it } from "vitest";
import { validateImage, MAX_FILE_SIZE, money, date, fieldValue } from "./bill-format";
describe("Bill upload requirements", () => {
  it("accepts PNG and JPG images", () => {
    expect(validateImage(new File(["image"], "bill.png", { type: "image/png" }))).toBeNull();
    expect(validateImage(new File(["image"], "bill.jpg", { type: "image/jpeg" }))).toBeNull();
  });
  it("rejects other file types", () => {
    expect(
      validateImage(new File(["pdf"], "bill.pdf", { type: "application/pdf" })),
    ).not.toBeNull();
  });
  it("limits images to 15 MB", () => {
    expect(MAX_FILE_SIZE).toBe(15 * 1024 * 1024);
    expect(
      validateImage(new File([new Uint8Array(MAX_FILE_SIZE)], "bill.png", { type: "image/png" })),
    ).toBeNull();
    expect(
      validateImage(
        new File([new Uint8Array(MAX_FILE_SIZE + 1)], "bill.png", { type: "image/png" }),
      ),
    ).not.toBeNull();
  });
});
describe("Bill formatting requirements", () => {
  it("shows null as Not on bill rather than zero", () => {
    expect(money(null)).toBe("Not on bill");
    expect(fieldValue("units_consumed", null)).toBe("Not on bill");
    expect(money(0)).toBe("PKR 0");
  });
  it("uses PKR with thousands separators and drops .00", () => {
    expect(money(3430.24)).toBe("PKR 3,430.24");
    expect(money(3430)).toBe("PKR 3,430");
    expect(money(-0.53)).toBe("PKR -0.53");
  });
  it("formats bill dates unambiguously", () => {
    expect(date("2026-04-21")).toBe("21 Apr 2026");
    expect(date("2026-04")).toBe("Apr 2026");
  });
});
