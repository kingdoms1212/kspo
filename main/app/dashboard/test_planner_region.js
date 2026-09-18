// node main/app/dashboard/test_planner_region.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function node() {
  return {
    dataset: {}, value: '', hidden: false, checked: false, children: [], handlers: {},
    addEventListener(name, handler) { this.handlers[name] = handler; },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute() {}, focus() {}, scrollIntoView() {}, querySelectorAll() { return []; },
  };
}
const nodes = new Map();
const el = id => {
  if (!nodes.has(id)) nodes.set(id, node());
  return nodes.get(id);
};
const handlers = {};
const requests = [];
const templateDirectory = path.join(__dirname, '../../templates/dashboard');
const templateIds = new Set(fs.readdirSync(templateDirectory)
  .filter(name => name.endsWith('.html'))
  .flatMap(name => Array.from(fs.readFileSync(path.join(templateDirectory, name), 'utf8')
    .matchAll(/\bid="([^"]+)"/g), match => match[1])));
const document = {
  body: node(), getElementById(id) { return templateIds.has(id) ? el(id) : null; },
  createElement: node, querySelectorAll() { return []; },
  addEventListener(name, handler) { handlers[name] = handler; },
};
el('plan-scope').dataset = {region: '서울', district: '중구'};
el('dashboard-region').value = '서울';
el('dashboard-district').value = '중구';
el('program-planner').dataset.listUrl = '/dashboard/plan/facilities';
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/program-planner.js'), 'utf8'), {
  document, window: {dispatchEvent() {}, addEventListener() {}}, Event: class {}, URLSearchParams, setTimeout,
  fetch(url) {
    requests.push(new URL(url, 'http://localhost'));
    return Promise.resolve({ok: true, json: async () => ({rows: [], count: 0, eligible_count: 0, page: 1, pages: 1})});
  },
});
function start() {
  handlers.click({target: {closest(selector) { return selector === '#plan-start' ? el('plan-start') : null; }}});
  assert.equal(document.body.dataset.planStep, 1);
  assert.equal(el('program-planner').hidden, false);
}
function chips() { return el('plan-context').children.map(child => child.textContent); }
async function search(district) {
  el('plan-sport').value = '농구';
  el('plan-sport').handlers.change();
  await new Promise(resolve => setImmediate(resolve));
  const query = requests.at(-1).searchParams;
  assert.equal(query.get('region'), '서울');
  assert.equal(query.get('district'), district);
  assert.equal(query.get('sport'), '농구');
}
async function run() {
  // Proceed without submitting the statistics form: use the latest multiple selection.
  el('dashboard-district').value = '강남구,송파구';
  start();
  assert.deepEqual(chips(), ['서울 강남구', '서울 송파구']);
  await search('강남구,송파구');

  // Returning to step 1 and changing selection also clears the prior sport.
  el('plan-back-region').handlers.click();
  el('dashboard-district').value = '마포구';
  start();
  assert.deepEqual(chips(), ['서울 마포구']);
  assert.equal(el('plan-sport').value, '');
  await search('마포구');

  // An empty selection means all districts, not the previous queried district.
  el('plan-back-region').handlers.click();
  el('dashboard-district').value = '';
  start();
  assert.deepEqual(chips(), ['서울 전체']);
  await search('');

  // HTMX replaces the input nodes after a statistics query.
  el('plan-back-region').handlers.click();
  nodes.set('dashboard-district', Object.assign(node(), {value: '종로구'}));
  el('plan-scope').dataset.district = '종로구';
  handlers['htmx:afterSwap']({detail: {target: {id: 'dashboard-body'}}});
  start();
  assert.deepEqual(chips(), ['서울 종로구']);
  await search('종로구');
  // Confirm step 2, then return from step 3 using the actual template button.
  el('plan-form').elements = {name: node()};
  el('plan-form').elements.name.value = '입력한 프로그램';
  el('plan-without-facility-check').checked = true;
  el('plan-confirm').handlers.click();
  assert.equal(document.body.dataset.planStep, 2);
  assert.equal(el('plan-entry').hidden, false);
  assert.equal(el('plan-sport-summary-row').hidden, false);
  const requestCount = requests.length;
  el('plan-back-selection').handlers.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(document.body.dataset.planStep, 1);
  assert.equal(el('plan-selection').hidden, false);
  assert.equal(el('plan-entry').hidden, true);
  assert.equal(el('plan-sport-summary-row').hidden, true);
  assert.equal(el('plan-step-actions').hidden, false);
  assert.equal(el('plan-sport').value, '농구');
  assert.equal(el('plan-form').elements.name.value, '입력한 프로그램');
  assert.equal(requests.length, requestCount + 1);
  assert.equal(requests.at(-1).searchParams.get('district'), '종로구');
  console.log('PASS: current districts reach step 2 and facility requests before/after query and reselection');
  console.log('PASS: step 3 returns to facility selection and retains sport, region and form input');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
