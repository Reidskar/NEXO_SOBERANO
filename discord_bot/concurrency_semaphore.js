const limitCount = parseInt(process.env.MAX_CONCURRENT_STT || '3', 10);

class SimpleSemaphore {
    constructor(max) {
        this.max = max;
        this.running = 0;
        this.queue = [];
    }

    async acquire() {
        if (this.running < this.max) {
            this.running++;
            console.log(`[SEMAPHORE] Acquired. Running: ${this.running}/${this.max}`);
            return;
        }
        console.log(`[SEMAPHORE] Queueing request. Queue length: ${this.queue.length + 1}`);
        return new Promise(resolve => this.queue.push(resolve));
    }

    release() {
        this.running--;
        console.log(`[SEMAPHORE] Released. Running: ${this.running}/${this.max}`);
        if (this.queue.length > 0) {
            this.running++;
            const next = this.queue.shift();
            console.log(`[SEMAPHORE] Next in queue started. Running: ${this.running}/${this.max}`);
            next();
        }
    }
}

const concurrencySemaphore = new SimpleSemaphore(limitCount);

// Helper limit function for exact replacement 
const limit = (fn) => async (...args) => {
    await concurrencySemaphore.acquire();
    try {
        return await fn(...args);
    } finally {
        concurrencySemaphore.release();
    }
};

module.exports = {
    concurrencySemaphore,
    limit
};
