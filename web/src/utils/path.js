export function sanitizeFilename(name) {
    return name.replace(/[/\\:*?"<>|]+/g, "_").trim();
}
export function dirname(p) {
    const idx = p.lastIndexOf("/");
    return idx >= 0 ? p.slice(0, idx) : p;
}
