import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  BackpressureQueue,
  isSinkSaturated,
} from "../backpressure.js";

describe("T9 — backpressure", () => {
  it("push and shift FIFO", () => {
    const q = new BackpressureQueue<number>(3);
    q.push(1);
    q.push(2);
    q.push(3);
    assert.equal(q.shift(), 1);
    assert.equal(q.shift(), 2);
    assert.equal(q.shift(), 3);
    assert.equal(q.shift(), undefined);
  });

  it("drops oldest when full", () => {
    const q = new BackpressureQueue<number>(3);
    q.push(1);
    q.push(2);
    q.push(3);
    q.push(4);
    const remaining = q.drain();
    assert.deepEqual(remaining, [2, 3, 4]);
    assert.equal(q.stats().dropped, 1);
  });

  it("dropped counter accumulates across overflows", () => {
    const q = new BackpressureQueue<number>(2);
    for (let i = 0; i < 10; i += 1) q.push(i);
    assert.equal(q.stats().dropped, 8);
    assert.equal(q.length, 2);
    assert.deepEqual(q.drain(), [8, 9]);
  });

  it("enqueued counter reflects every push", () => {
    const q = new BackpressureQueue<number>(5);
    for (let i = 0; i < 7; i += 1) q.push(i);
    assert.equal(q.stats().enqueued, 7);
  });

  it("drain with max respects limit", () => {
    const q = new BackpressureQueue<number>(10);
    for (let i = 1; i <= 5; i += 1) q.push(i);
    const got = q.drain(3);
    assert.deepEqual(got, [1, 2, 3]);
    assert.equal(q.length, 2);
  });

  it("clear empties buffer", () => {
    const q = new BackpressureQueue<number>(3);
    q.push(1);
    q.push(2);
    q.clear();
    assert.equal(q.length, 0);
  });

  it("constructor rejects bad capacity", () => {
    assert.throws(() => new BackpressureQueue<number>(0));
    assert.throws(() => new BackpressureQueue<number>(-1));
    assert.throws(() => new BackpressureQueue<number>(NaN));
  });

  it("isSinkSaturated reports based on writableLength/HWM", () => {
    assert.equal(
      isSinkSaturated({ writableLength: 100, writableHighWaterMark: 100 }),
      true
    );
    assert.equal(
      isSinkSaturated({ writableLength: 50, writableHighWaterMark: 100 }),
      false
    );
    assert.equal(isSinkSaturated({}), false);
  });
});
