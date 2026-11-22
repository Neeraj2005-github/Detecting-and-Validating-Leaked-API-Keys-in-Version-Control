import React from 'react';

export function ScanEmptyState() {
  return React.createElement(
    'section',
    { className: 'vg-empty-result', role: 'status' },
    React.createElement('h2', null, 'No secrets detected'),
    React.createElement(
      'p',
      null,
      'No configured patterns matched the scanned history. This does not prove that credentials are valid or absent from skipped files, archives, submodules, LFS objects, or formats the scanner does not recognize.',
    ),
  );
}
