export function formatINR(value: number, compact = false) {
  if (compact && Math.abs(value) >= 10_000_000) return `₹${(value / 10_000_000).toFixed(2)} Cr`;
  if (compact && Math.abs(value) >= 100_000) return `₹${(value / 100_000).toFixed(2)} L`;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
}

export function friendlyError(error: unknown) {
  if (error && typeof error === "object" && "body" in error) {
    const body = (error as { body?: { detail?: string | Array<{ msg: string }> } }).body;
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail[0]?.msg ?? "Please check the entered details.";
  }
  return "Something went wrong. Please try again.";
}