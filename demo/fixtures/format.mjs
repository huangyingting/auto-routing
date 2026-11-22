// Intentionally incomplete trim: misses Unicode NBSP (\u00A0) so Step 2 fixes and tests it.
export function greetingFormatter(rawName) {
  const cleaned = String(rawName ?? "").replace(/^[ ]+|[ ]+$/g, "");
  return cleaned ? `Hello, ${cleaned}!` : "Hello, guest!";
}
