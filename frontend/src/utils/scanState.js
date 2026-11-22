export function shouldStopScanning(status) {
  return status === 'done' || status === 'failed' || status === 'timed_out';
}
