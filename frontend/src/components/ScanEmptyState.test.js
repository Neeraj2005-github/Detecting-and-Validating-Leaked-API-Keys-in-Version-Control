import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { ScanEmptyState } from './ScanEmptyState.js';

test('empty scan result renders a verdict and explains its limits', () => {
  const markup = renderToStaticMarkup(React.createElement(ScanEmptyState));

  assert.match(markup, /No secrets detected/);
  assert.match(markup, /does not prove/);
  assert.match(markup, /skipped files/);
});
