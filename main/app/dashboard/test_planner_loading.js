// node main/app/dashboard/test_planner_loading.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const nodes = new Map();
// Missing template elements must return null, as they do in the browser.
const templateIds = new Set(['index.html', '_planner.html', '_body.html'].flatMap(file =>
  Array.from(fs.readFileSync(path.join(__dirname, '../../templates/dashboard', file), 'utf8')
    .matchAll(/\bid="([^"]+)"/g), match => match[1])));
function node() {
  return {
    dataset: {}, value: '', hidden: false, disabled: false, textContent: '',
    children: [], handlers: {}, classList: {toggle() {}},
    addEventListener(type, handler) {this.handlers[type] = handler;},
    setAttribute(key, value) {this[key] = value;},
    replaceChildren(...children) {this.children = children;},
    append(...children) {this.children.push(...children);},
    querySelectorAll() {return [];}, focus() {}, scrollIntoView() {},
  };
}
function el(id) {
  if (!templateIds.has(id)) return null;
  if (!nodes.has(id)) nodes.set(id, node());
  return nodes.get(id);
}
el('program-planner').dataset = {listUrl: '/facilities', detailUrl: '/detail'};
el('plan-scope').dataset = {region: '서울', district: '중구'};
el('dashboard-region').value = '서울';
el('dashboard-district').value = '중구';
const document = {
  body: node(), handlers: {}, getElementById: el, createElement: node,
  querySelectorAll() {return [];},
  addEventListener(type, handler) {this.handlers[type] = handler;},
};
const requests = [];
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/program-planner.js'), 'utf8'), {
  document, window: {dispatchEvent() {}, addEventListener() {}}, Event: class {}, URLSearchParams,
  setTimeout() {},
  fetch() {return new Promise((resolve, reject) => requests.push({resolve, reject}));},
});
const tick = () => new Promise(resolve => setImmediate(resolve));
function sport(value) {
  el('plan-sport').value = value;
  el('plan-sport').handlers.change();
}
function resolveList(index, eligibleCount = 1) {
  requests[index].resolve({ok: true, json: async () => ({rows: [], page: 1, pages: 1, count: 0, eligible_count: eligibleCount})});
}
(async () => {
  document.handlers.click({target: {closest: () => true}});
  assert.equal(el('plan-step-one-result').hidden, false);
  assert.equal(el('plan-step-actions').hidden, false);
  assert.equal(el('plan-sport-summary-row').hidden, true);
  assert.equal(el('plan-context').children[0].textContent, '서울 중구');
  sport('수영');
  assert.equal(el('plan-loading').hidden, false);
  assert.equal(el('plan-facility-grid').inert, true);
  assert.equal(el('plan-facility-grid')['aria-busy'], 'true');
  assert.equal(el('plan-confirm').disabled, true);
  sport('축구');
  resolveList(0); await tick();
  assert.equal(el('plan-loading').hidden, false, 'An old response cannot hide a newer request');
  resolveList(1); await tick();
  assert.equal(el('plan-loading').hidden, true);
  assert.equal(el('plan-facility-grid').inert, false);
  assert.equal(el('plan-detail').children[0].children[0].children[0].textContent, '매칭되는 후보 시설이 없습니다.');
  assert.equal(el('plan-error').textContent, '');
  assert.equal(el('plan-detail').children[0].className, 'plan-detail-content');
  assert.equal(el('plan-detail').children[0].children[0].className, 'plan-empty');
  assert.equal(el('plan-candidates').children.length, 0);
  assert.equal(el('plan-page').textContent, '');
  assert.equal(el('plan-next').disabled, true);
  assert.equal(el('plan-confirm').disabled, true);
  sport('농구');
  requests[2].reject(new Error('Network failure')); await tick();
  assert.equal(el('plan-loading').hidden, true);
  assert.equal(el('plan-error').textContent, 'Network failure');
  assert.equal(el('plan-detail').children[0].children[0].children[0].textContent, '시설 목록을 불러오지 못했습니다.');
  sport('수영'); sport('');
  assert.equal(el('plan-loading').hidden, true, 'Clearing the sport cancels the loading state');
  resolveList(3); await tick();
  assert.equal(el('plan-count').textContent, '');
  sport('축구');
  el('plan-back-region').handlers.click();
  assert.equal(el('plan-loading').hidden, true);
  assert.equal(el('plan-step-actions').hidden, true);
  assert.equal(el('plan-step-one-result').hidden, true);
  resolveList(4); await tick();
  assert.equal(el('plan-count').textContent, '');
  sport('수영');
  resolveList(5); await tick();
  el('plan-query').value = '없는 시설';
  el('plan-search').handlers.submit({preventDefault() {}});
  resolveList(6); await tick();
  assert.equal(el('plan-detail').children[0].children[0].children[0].textContent, '검색 결과가 없습니다.');
  assert.equal(el('plan-error').textContent, '');
  el('plan-scope').dataset.district = '중구,종로구';
  el('dashboard-district').value = '중구,종로구';
  document.handlers['htmx:afterSwap']({detail: {target: {id: 'dashboard-body'}}});
  assert.deepEqual(el('plan-context').children.map(chip => chip.textContent), ['서울 중구', '서울 종로구']);
  sport('농구'); resolveList(7, 0); await tick();
  assert.equal(el('plan-pagination').hidden, true);
  assert.equal(el('plan-without-facility').hidden, false);
  assert.equal(el('plan-confirm').disabled, true);
  el('plan-without-facility-check').checked = true;
  el('plan-without-facility-check').handlers.change();
  assert.equal(el('plan-confirm').disabled, false);
  el('plan-form').elements = {name: {focus() {}}};
  el('plan-confirm').handlers.click();
  assert.equal(el('plan-entry').hidden, false);
  assert.equal(el('plan-sport-summary'), null);
  assert.equal(el('plan-entry-actions').hidden, false);
  assert.equal(el('plan-confirmed').children[0].textContent, '매칭 후보 시설 없음 · 시설 미정으로 진행');
  assert.equal(el('plan-sport-summary-row').hidden, false);
  el('plan-back-selection').handlers.click();
  assert.equal(el('plan-entry-actions').hidden, true);
  assert.equal(el('plan-sport-summary-row').hidden, true);
  assert.equal(el('plan-entry').hidden, true);
  assert.equal(el('plan-selection').hidden, false);
  resolveList(8, 0); await tick();
  sport('');
  assert.equal(el('plan-confirm').disabled, true);
  assert.equal(el('plan-without-facility-check').checked, false);
  assert.equal(el('plan-detail').children[0].children[0].children[0].textContent, '종목과 시설을 선택해 주세요.');
  assert.equal(el('plan-candidates-section').hidden, true);
  assert.equal(el('plan-facility-grid').dataset.empty, 'true');
  console.log('PASS: step summary, navigation, loading success/failure and stale responses');
})().catch(error => {console.error(error); process.exitCode = 1;});
