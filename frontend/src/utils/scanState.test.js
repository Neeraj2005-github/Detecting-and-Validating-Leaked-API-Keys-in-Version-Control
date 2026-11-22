import test from 'node:test';
import assert from 'node:assert/strict';
import { partialResultFromTimedOutJob, shouldStopScanning } from './scanState.js';

test('all terminal scan states leave the stuck scanning state', () => {
  assert.equal(shouldStopScanning('done'), true);
  assert.equal(shouldStopScanning('failed'), true);
  assert.equal(shouldStopScanning('timed_out'), true);
  assert.equal(shouldStopScanning('running'), false);
});

test('timed out partial results retain their stage and reason', () => {
  const result = partialResultFromTimedOutJob({
    status: 'timed_out',
    result: { partial: true, findings: [{ masked_value: '[REDACTED]' }] },
    error: { stage: 'scan', reason: 'Stage timed out.' },
  });

  assert.equal(result.partial, true);
  assert.equal(result.error.stage, 'scan');
  assert.equal(result.error.reason, 'Stage timed out.');
  assert.equal(partialResultFromTimedOutJob({ status: 'done', result: {} }), null);
});
