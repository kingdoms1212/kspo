// node main/app/dashboard/test_region_selection.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const handlers = {};
let submits = 0;
let configured = 0;
const highlights = new Set();
const actions = [];
const map = {};
const timers = [];
const chart = {getOption(){return {series:[{map:'sport-insight-municipalities-11', data:[{name:'A'},{name:'B'}], selectedMap:Object.fromEntries([...highlights].map(name=>[name,true]))}]};},
  setOption(option){configured++;assert.equal(option.series[0].select.itemStyle.areaColor,'#FFD54F');},
  dispatchAction(action){actions.push(action);assert.ok(['select','unselect'].includes(action.type));const name=['A','B'][action.dataIndex];if(action.type==='select')highlights.add(name);else highlights.delete(name);}};
let field = {value: ''};
function node() {
  return {dataset: {}, children: [], classList: {toggle() {}},
    setAttribute(k,v) {this[k]=v;}, appendChild(n) {this.children.push(n);},
    replaceChildren() {this.children=[];}, focus() {}};
}
const buttons = ['', 'A', 'B'].map(name => {const b=node();b.dataset.district=name;return b;});
const list = node();
const document = {
  addEventListener(name, handler) {handlers[name]=handler;},
  getElementById(id) {return id==='dashboard-region-map'?map:id==='dashboard-district'?field:id==='dashboard-selected-districts'?list:{requestSubmit(){submits++;}};},
  querySelectorAll() {return buttons;}, querySelector() {return buttons[0];}, createElement: node
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../static/dashboard-region-map.js'),'utf8'), {
  document,
  // No renderer event listeners or mutation observers may trigger recursive updates.
  window: {echarts:{getInstanceByDom(){return chart;}}},
  setTimeout(fn){timers.push(fn);return timers.length;},clearTimeout(){},
  MutationObserver: class {constructor(){throw Error('Unexpected mutation observer');}}
});
function click(selector, target) {handlers.click({target:{closest(s){return s===selector?target:null;}}});}
click('.db-district-picker [data-district]',buttons[1]);
actions.length=0;
click('.db-district-picker [data-district]',buttons[2]);
assert.deepEqual(actions.map(action=>[action.type,action.dataIndex]),[['select',1]], 'Adding B must leave A untouched');
assert.equal(field.value,'A,B');assert.deepEqual([...highlights],['A','B']);assert.equal(configured,1);assert.equal(list.children.length,2);assert.equal(buttons[0]['aria-pressed'],'false');
handlers['regionmap:select']({target:{id:'dashboard-region-map'},detail:{level:'district',name:'A'}});
assert.equal(field.value,'B');assert.equal(list.children[0].dataset.removeDistrict,'B');
// ECharts may toggle the clicked area after the custom selection event.
highlights.add('A');
actions.length=0;
while(timers.length) timers.shift()();
assert.deepEqual(actions.map(action=>[action.type,action.dataIndex]),[['unselect',0]], 'Click reconciliation must leave B untouched');
actions.length=0;
handlers['htmx:afterSwap']();
assert.equal(actions.length,0, 'Unchanged selection must not restart transitions');
click('[data-remove-district]',list.children[0]);
assert.equal(field.value,'');assert.equal(buttons[0]['aria-pressed'],'true');
assert.equal(submits,0);
// Replacing the form through HTMX must not leave stale state in event handlers.
field={value:'A'};
click('.db-district-picker [data-district]',buttons[2]);assert.equal(field.value,'A,B');
click('.db-district-picker [data-district]',buttons[0]);assert.equal(field.value,'');
handlers['regionmap:select']({target:{id:'dashboard-region-map'},detail:{level:'district',name:'unknown'}});
assert.equal(field.value,'');
click('.db-district-picker [data-district]',buttons[1]);
click('#dashboard-reset',{});assert.equal(field.value,'');assert.equal(submits,1);
while(timers.length) timers.shift()();
assert.equal(configured,1);assert.equal(highlights.size,0);
console.log('PASS: selection, yellow map highlights, reset and one-time map setup without observers');
