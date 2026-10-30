export function maskSecret(value: unknown): string {
  const text = String(value ?? '');
  if (!text) return '****';
  if (text.includes('*')) return text;
  if (text.length <= 8) return '*'.repeat(text.length);
  return `${text.slice(0, 4)}${'*'.repeat(Math.max(4, text.length - 8))}${text.slice(-4)}`;
}

export function maskCommit(value: unknown): string {
  const text = String(value ?? '');
  return text ? `****${text.slice(-4)}` : '****';
}
