export class AsyncMutex {
  private queue: Promise<void> = Promise.resolve();
  async runExclusive<T>(fn: () => Promise<T> | T): Promise<T> {
    let release!: () => void;
    const prev = this.queue;
    this.queue = new Promise<void>((r) => { release = r; });
    await prev;
    try {
      return await fn();
    } finally {
      release();
    }
  }
}

export class TokenBucket {
  private tokens = 10;
  private closed = false;
  private readonly stateLock = new AsyncMutex();
  private readonly drainLock = new AsyncMutex();

  // BUG: acquires drainLock -> stateLock (opposite of close()!)
  async refill(amount: number): Promise<number> {
    return this.drainLock.runExclusive(async () => {
      await Promise.resolve();
      return this.stateLock.runExclusive(() => {
        if (this.closed) return 0;
        this.tokens += amount;
        return this.tokens;
      });
    });
  }

  // Acquires stateLock -> drainLock
  async close(): Promise<void> {
    await this.stateLock.runExclusive(async () => {
      await Promise.resolve();
      await this.drainLock.runExclusive(() => {
        this.closed = true;
        this.tokens = 0;
      });
    });
  }
}
