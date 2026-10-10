export const MAX_FILE_SIZE = 15 * 1024 * 1024;
export function validateImage(file: File): string | null {
  if (!["image/png", "image/jpeg"].includes(file.type))
    return "Please choose a PNG or JPG image of your bill.";
  if (file.size > MAX_FILE_SIZE)
    return "This image is too large. Please choose a file under 15 MB.";
  if (file.size === 0) return "This image is empty. Please choose another file.";
  return null;
}
export function money(value: number | null | undefined): string {
  if (value == null) return "Not on bill";
  return `PKR ${new Intl.NumberFormat("en-PK", { minimumFractionDigits: Number.isInteger(value) ? 0 : 2, maximumFractionDigits: 2 }).format(value)}`;
}
export function pretty(value: string): string {
  const labels: Record<string, string> = {
    KE: "K-Electric",
    gst: "GST",
    fpa: "Fuel price adjustment",
    sanctioned_load_kw: "Sanctioned load (kW)",
    payable_within_due_date: "Payable by due date",
    payable_after_due_date: "Payable after due date",
  };
  return labels[value] || value.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}
export function date(value: string | null): string {
  if (value === null) return "Not on bill";
  const parsed = new Date(`${value.length === 7 ? value + "-01" : value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    ...(value.length === 7 ? {} : { day: "numeric" as const }),
    month: "short",
    year: "numeric",
  }).format(parsed);
}
const currencyFields = new Set([
  "total_charges",
  "total_taxes",
  "current_bill",
  "arrears",
  "payable_within_due_date",
  "payable_after_due_date",
]);
export function fieldValue(field: string, value: unknown): string {
  if (value == null) return "Not on bill";
  if (currencyFields.has(field) && typeof value === "number") return money(value);
  if ((field.endsWith("_date") || field === "bill_month") && typeof value === "string")
    return date(value);
  if (field === "provider" && typeof value === "string") return pretty(value);
  if (Array.isArray(value))
    return value.length
      ? value
          .map((item) =>
            typeof item === "object" && item !== null && "type" in item && "amount" in item
              ? `${pretty(String(item.type))}: ${money(item.amount as number | null)}`
              : JSON.stringify(item),
          )
          .join("; ")
      : "None printed";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
