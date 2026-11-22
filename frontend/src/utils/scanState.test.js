import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldStopScanning } from './scanState.js';

test('all terminal scan states leave the stuck scanning state', () => {
  assert.equal(shouldStopScanning('done'), true);
  assert.equal(shouldStopScanning('failed'), true);
  assert.equal(shouldStopScanning('timed_out'), true);
  assert.equal(shouldStopScanning('running'), false);
});
