// node --test main/app/dashboard/test_region_ai_ui.js
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('region submissions analyze the latest selection without overlapping requests', async () => {
  const handlers = {}, calls = [];
  const element = () => ({textContent: '', children: [], setAttribute() {},
    append(...items) { this.children.push(...items); }, replaceChildren() { this.children = []; }});
  function makeButton(district) {
    const fields = Object.fromEntries(['result', 'status', 'label', 'title'].map(k => [k, element()]));
    const card = {isConnected: true, dataset: {aiDistrict: district}, querySelector(selector) {
      return selector.includes('csrf') ? {value: 'test'} : fields[selector.match(/region-(\w+)/)[1]];
    }};
    return {isConnected: true, disabled: false, closest: () => card, card, fields};
  }
  let current = makeButton('강남구');
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/region-ai.js'), 'utf8'), {
    document: {addEventListener: (name, callback) => {handlers[name] = callback;},
      querySelector: () => current, createElement: element},
    FormData: class {set(key, value) {this[key] = value;}},
    fetch: (url, options) => new Promise(resolve => calls.push({district: options.body.district, resolve})),
  });
  const swap = (source = 'dashboard-filters') => handlers['htmx:afterSwap']({detail: {
    target: {id: 'dashboard-body'}, requestConfig: {elt: {id: source}},
  }});
  const settle = () => new Promise(resolve => setImmediate(resolve));
  const finish = index => calls[index].resolve({ok: true, json: async () => ({result: {
    summary: '검증 결과', features: ['특징'], considerations: ['확인 사항'],
  }})});
  assert.equal(calls.length, 0, 'initial load does not call AI');
  swap('chart-sort');
  assert.equal(calls.length, 0, 'sorting does not call AI');
  swap(); swap();
  assert.equal(calls.length, 1, 'duplicate events do not overlap');
  const old = current;
  old.isConnected = old.card.isConnected = false;
  current = makeButton('강동구'); swap();
  current.isConnected = current.card.isConnected = false;
  current = makeButton('강서구'); swap();
  assert.equal(calls.length, 1, 'latest selection waits for the active request');
  finish(0); await settle();
  assert.equal(calls.length, 2);
  assert.equal(calls[1].district, '강서구');
  assert.equal(old.fields.result.children.length, 0, 'stale result is not rendered');
  finish(1); await settle();
  assert.equal(current.fields.status.textContent, '분석 완료');
  swap();
  assert.equal(calls.length, 3, 'another query starts another analysis request');
  calls[2].resolve({ok: false, json: async () => ({error: '일시 오류'})});
  await settle();
  assert.equal(current.fields.status.textContent, '분석 실패');
  assert.equal(current.disabled, false, 'failure leaves retry available');
});
