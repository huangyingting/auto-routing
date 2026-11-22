export const DEFAULT_PORT = 8787;
export const PORT_ENV_VAR = "AUTO_DEMO_PORT";

export function resolvePort(env = process.env): number {
  const raw = env[PORT_ENV_VAR];
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PORT;
}
