interface CacheEntry<T> {
  data: T;
  expiry: number;
}

const DEFAULT_TTL = 300000; // 5 minutes

class Cache {
  private store = new Map<string, CacheEntry<unknown>>();

  get<T>(key: string): T | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiry) {
      this.store.delete(key);
      return null;
    }
    return entry.data as T;
  }

  set<T>(key: string, data: T, ttl: number = DEFAULT_TTL): void {
    this.store.set(key, {
      data,
      expiry: Date.now() + ttl,
    });
  }

  delete(key: string): boolean {
    return this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}

export const cache = new Cache();
export default cache;
