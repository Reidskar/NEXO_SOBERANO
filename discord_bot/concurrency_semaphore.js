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
            return;
        }
        return new Promise(resolve => this.queue.push(resolve));
    }

    release() {
        this.running--;
        if (this.queue.length > 0) {
            this.running++;
            const next = this.queue.shift();
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
