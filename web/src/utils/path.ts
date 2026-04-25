export function sanitizeFilename(name: string): string {
  return name.replace(/[/\\:*?"<>|]+/g, "_").trim();
}

export function dirname(p: string): string {
  const idx = p.lastIndexOf("/");
  return idx >= 0 ? p.slice(0, idx) : p;
}
