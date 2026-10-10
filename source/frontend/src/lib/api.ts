import { z } from "zod";

const amount = z.number().nullable();
const text = z.string().nullable();
const items = z.array(z.object({ type: z.string(), amount }));
export const billSchema = z.object({
  provider: z.enum(["KE", "LESCO", "IESCO"]).nullable(),
  tariff: text,
  sanctioned_load_kw: amount,
  bill_month: text,
  reading_date: text,
  issue_date: text,
  due_date: text,
  previous_reading: amount,
  current_reading: amount,
  units_consumed: amount,
  charges: items,
  total_charges: amount,
  taxes: items,
  total_taxes: amount,
  current_bill: amount,
  arrears: amount,
  payable_within_due_date: amount,
  payable_after_due_date: amount,
});
export type Bill = z.infer<typeof billSchema>;
export interface DecodedBill {
  bill_id: string;
  bill: Bill;
  issues: string[];
}
export interface SecondOpinion {
  agrees: boolean;
  differences: { field: string; primary: unknown; second: unknown }[];
}
export interface Answer {
  answer: string;
  calculations: { name: string; expression: string; result: string | number | null }[];
}
export interface Comparison {
  correct: number;
  total: number;
  accuracy: number;
  fields: { field: string; predicted: unknown; expected: unknown; ok: boolean }[];
}
export const API_URL = (import.meta.env["VITE_API_URL"] || "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
async function request<T>(path: string, init: RequestInit = {}, schema?: z.ZodType<T>): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120_000);
  try {
    const response = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        /* Non-JSON errors use the friendly fallback. */
      }
      throw new ApiError(
        detail ||
          `The bill service couldn't complete this request (${response.status}). Please try again.`,
        response.status,
      );
    }
    const data: unknown = await response.json();
    if (schema) {
      const result = schema.safeParse(data);
      if (!result.success)
        throw new ApiError("The bill service returned an unexpected response. Please try again.");
      return result.data;
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error && error.name === "AbortError"
        ? "The bill service took too long to respond. Please try again."
        : "We can't reach the bill service. Check your connection and try again.",
    );
  } finally {
    clearTimeout(timer);
  }
}
function imageForm(image: File, bill?: Bill): FormData {
  const form = new FormData();
  form.append("image", image);
  if (bill) form.append("bill", JSON.stringify(bill));
  return form;
}
export const api = {
  health: () =>
    request(
      "/api/health",
      {},
      z.object({
        status: z.string(),
        model: z.string().optional(),
        verifier_model: z.string().optional(),
      }),
    ),
  samples: () => request("/api/samples", {}, z.array(z.string())),
  sample: async (name: string): Promise<File> => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120_000);
    try {
      const response = await fetch(`${API_URL}/api/samples/${encodeURIComponent(name)}`, {
        signal: controller.signal,
      });
      if (!response.ok)
        throw new ApiError(
          "This sample bill could not be loaded. Please try again.",
          response.status,
        );
      const blob = await response.blob();
      return new File([blob], name, {
        type: blob.type.startsWith("image/")
          ? blob.type
          : /\.png$/i.test(name)
            ? "image/png"
            : "image/jpeg",
      });
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError("The sample bill could not be loaded. Please try again.");
    } finally {
      clearTimeout(timer);
    }
  },
  decode: (image: File) =>
    request(
      "/api/decode",
      { method: "POST", body: imageForm(image) },
      z.object({ bill_id: z.string(), bill: billSchema, issues: z.array(z.string()) }),
    ),
  secondOpinion: (image: File, bill: Bill) =>
    request<SecondOpinion>("/api/second-opinion", { method: "POST", body: imageForm(image, bill) }),
  ask: (image: File, bill: Bill, question: string) => {
    const form = imageForm(image, bill);
    form.append("question", question);
    return request<Answer>("/api/ask", { method: "POST", body: form });
  },
  expected: async (id: string): Promise<Bill | null> => {
    try {
      return await request(`/api/expected/${encodeURIComponent(id)}`, {}, billSchema);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },
  compare: (bill: Bill, expected: Record<string, unknown>) =>
    request<Comparison>("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bill, expected }),
    }),
};
