import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import { createKeywordTableRefreshCoalescer } from '../src/features/keywords/keywordTableRefreshCoalescer.js';

class FakeTimers {
  now = 0;
  nextId = 1;
  timers = new Map();

  setTimeout = (callback, delay) => {
    const id = this.nextId++;
    this.timers.set(id, { callback, at: this.now + delay });
    return id;
  };

  clearTimeout = (id) => {
    this.timers.delete(id);
  };

  advance(milliseconds) {
    const target = this.now + milliseconds;
    while (true) {
      const due = [...this.timers.entries()]
        .filter(([, timer]) => timer.at <= target)
        .sort((left, right) => left[1].at - right[1].at)[0];
      if (!due) break;
      const [id, timer] = due;
      this.timers.delete(id);
      this.now = timer.at;
      timer.callback();
    }
    this.now = target;
  }
}

const flushPromises = () => new Promise((resolve) => setImmediate(resolve));

function setup() {
  const timers = new FakeTimers();
  let refreshes = 0;
  const coalescer = createKeywordTableRefreshCoalescer(
    async () => {
      refreshes += 1;
    },
    {
      debounceMs: 100,
      maxWaitMs: 400,
      setTimer: timers.setTimeout,
      clearTimer: timers.clearTimeout,
    }
  );
  return { timers, coalescer, refreshCount: () => refreshes };
}

test('one keyword_updated event refreshes the table promptly once', async () => {
  const { timers, coalescer, refreshCount } = setup();

  coalescer.request();
  await flushPromises();
  assert.equal(refreshCount(), 1);

  timers.advance(100);
  await flushPromises();
  assert.equal(refreshCount(), 1);
});

test('rapid keyword_updated events are coalesced into bounded table refreshes', async () => {
  const { timers, coalescer, refreshCount } = setup();

  coalescer.request();
  coalescer.request();
  coalescer.request();
  coalescer.request();
  await flushPromises();
  assert.equal(refreshCount(), 1);

  timers.advance(100);
  await flushPromises();
  assert.equal(refreshCount(), 2);
});

test('continuous events refresh periodically and once after the burst ends', async () => {
  const { timers, coalescer, refreshCount } = setup();

  coalescer.request();
  await flushPromises();
  for (let index = 0; index < 5; index += 1) {
    timers.advance(80);
    coalescer.request();
  }
  await flushPromises();
  assert.equal(refreshCount(), 2);

  timers.advance(100);
  await flushPromises();
  assert.equal(refreshCount(), 3);
});

test('an event after the coalescing window starts a new prompt refresh', async () => {
  const { timers, coalescer, refreshCount } = setup();

  coalescer.request();
  await flushPromises();
  timers.advance(100);

  coalescer.request();
  await flushPromises();
  assert.equal(refreshCount(), 2);
});

test('dispose cancels stale trailing refreshes for unmount or project change', async () => {
  const { timers, coalescer, refreshCount } = setup();

  coalescer.request();
  coalescer.request();
  await flushPromises();
  assert.equal(refreshCount(), 1);

  coalescer.dispose();
  timers.advance(1000);
  await flushPromises();
  assert.equal(refreshCount(), 1);

  coalescer.request();
  await flushPromises();
  assert.equal(refreshCount(), 1);
});

test('KeywordsPage owns and disposes one coalescer per selected-project SSE effect', async () => {
  const page = await readFile(
    new URL('../src/views/KeywordsPage.jsx', import.meta.url),
    'utf8'
  );

  assert.match(page, /createKeywordTableRefreshCoalescer\(\s*fetchTableData/);
  assert.match(page, /tableRefreshCoalescer\.request\(\)/);
  assert.match(page, /tableRefreshCoalescer\.dispose\(\)/);
  assert.match(page, /\}, \[selectedProjectId, fetchTableData\]\);/);
});
