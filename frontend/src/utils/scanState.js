export function shouldStopScanning(status) {
  return status === 'done' || status === 'failed' || status === 'timed_out';
}

export function partialResultFromTimedOutJob(job) {
  if (job?.status !== 'timed_out' || !job.result) return null;
  return { ...job.result, error: job.error };
}
