// node --test main/app/dashboard/test_region_ai_ui.js
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('AI clicks work without optional captions and recover after failures', async () => {
  const handlers = {}, calls = [];
  const element = () => ({textContent: '', children: [], setAttribute() {},
    append(...items) { this.children.push(...items); }, replaceChildren() { this.children = []; }});
  function makeButton(district) {
    const fields = Object.fromEntries(['result', 'status', 'label', 'title'].map(k => [k, element()]));
    const card = {isConnected: true, dataset: {aiDistrict: district}, querySelector(selector) {
      if (selector.includes('csrf')) return {value: 'test'};
      if (selector === '[data-ai-region]') return button;
      return fields[selector.match(/region-(\w+)/)[1]];
    }};
    const button = {isConnected: true, disabled: false, setAttribute() {}, closest: () => card, card, fields};
    return button;
  }
  let current = makeButton('강남구');
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/region-ai.js'), 'utf8'), {
    document: {addEventListener: (name, callback) => {handlers[name] = callback;},
      querySelector: () => current, createElement: element},
    performance: {now: () => 0}, setInterval, clearInterval,
    FormData: class {set(key, value) {this[key] = value;}},
    fetch: (url, options) => new Promise(resolve => calls.push({district: options.body.district, resolve})),
  });
  const click = () => handlers.click({target: {closest: () => current}});
  const settle = () => new Promise(resolve => setImmediate(resolve));
  const finish = index => calls[index].resolve({ok: true, json: async () => ({result: {
    summary: '검증 결과', features: ['특징'], considerations: ['확인 사항'],
  }})});
  assert.equal(calls.length, 0, 'initial load does not call AI');
  assert.equal(typeof handlers['htmx:afterSwap'], 'function', 'completed analysis can survive a dashboard query');
  click(); click();
  assert.equal(calls.length, 1, 'duplicate events do not overlap');
  const old = current;
  old.isConnected = old.card.isConnected = false;
  current = makeButton('강동구'); click();
  current.isConnected = current.card.isConnected = false;
  current = makeButton('강서구'); click();
  assert.equal(calls.length, 1, 'latest selection waits for the active request');
  finish(0); await settle();
  assert.equal(calls.length, 2);
  assert.equal(calls[1].district, '강서구');
  assert.equal(old.fields.result.children.length, 0, 'stale result is not rendered');
  finish(1); await settle();
  assert.equal(current.fields.status.textContent, '분석 완료');
  assert.equal(current.disabled, true, 'same-region analysis cannot be requested again');
  click();
  assert.equal(calls.length, 2, 'disabled completed analysis does not request another score');
  current.isConnected = current.card.isConnected = false;
  current = makeButton('강동구');
  handlers['htmx:afterSwap']({detail: {target: {id: 'dashboard-body'}}});
  assert.equal(current.fields.status.textContent, '지역 변경 · 재분석 필요');
  assert.equal(current.fields.label.textContent, 'AI로 다시 분석하기');
  assert.equal(current.fields.result.children.length, 3, 'previous analysis remains visible after a region query');
  assert.equal(current.disabled, false, 'changed region enables analysis');
  handlers['regionai:reset']();
  current = makeButton('강북구');
  handlers['htmx:afterSwap']({detail: {target: {id: 'dashboard-body'}}});
  assert.equal(current.fields.result.children.length, 0, 'explicit planner reset clears the retained region analysis');
  assert.equal(current.disabled, false);
  click();
  assert.equal(calls.length, 3, 'changed region starts a new analysis request');
  calls[2].resolve({ok: false, json: async () => ({error: '일시 오류'})});
  await settle();
  assert.equal(current.fields.status.textContent, '분석 실패');
  assert.equal(current.disabled, false, 'failure leaves retry available');
});
