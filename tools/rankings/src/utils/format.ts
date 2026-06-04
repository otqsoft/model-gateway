export function formatPrice(price: number): string {
  if (price === 0) return 'Free';
  if (price < 0.01) return `$${price.toFixed(4)}/M`;
  return `$${price.toFixed(2)}/M`;
}

export function formatContextLength(length: number): string {
  if (length >= 1_000_000) return `${(length / 1_000_000).toFixed(length % 1_000_000 === 0 ? 0 : 1)}M`;
  if (length >= 1_000) return `${(length / 1_000).toFixed(length % 1_000 === 0 ? 0 : 1)}K`;
  return String(length);
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000_000_000) return `${(tokens / 1_000_000_000_000).toFixed(2)}T`;
  if (tokens >= 1_000_000_000) return `${(tokens / 1_000_000_000).toFixed(1)}B`;
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return String(tokens);
}

export function formatChange(change: number): string {
  if (change > 0) return `+${change}%`;
  if (change < 0) return `${change}%`;
  return '0%';
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#d4a574',
  google: '#4285f4',
  meta: '#0084ff',
  deepseek: '#4d6bfe',
  mistral: '#f70000',
  qwen: '#6f42c1',
  xiaomi: '#ff6900',
  tencent: '#25d366',
};

export function getProviderColor(provider: string): string {
  const lower = provider.toLowerCase();
  if (PROVIDER_COLORS[lower]) return PROVIDER_COLORS[lower];
  let hash = 0;
  for (let i = 0; i < provider.length; i++) {
    hash = provider.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash;
  }
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6'];
  return colors[Math.abs(hash) % colors.length];
}
