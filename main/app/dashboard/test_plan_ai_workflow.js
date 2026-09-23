const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('optional AI generation and unchanged-input review locking', async () => {
  const nodes = new Map();
  const el = id => {
    if (!nodes.has(id)) nodes.set(id, {checked:false, disabled:false, dataset:{}, handlers:{},
      addEventListener(k,v){this.handlers[k]=v;}, querySelector(s){return el(s);},
      replaceChildren(){}, reportValidity(){return true;}, setAttribute(){}});
    return nodes.get(id);
  };
  let name = '기존 프로그램', calls = 0;
  class FormData {
    constructor(){this.values = new Map([['name',name]]);}
    set(k,v){this.values.set(k,v);} append(k,v){this.values.set(k,v);}
    entries(){return this.values.entries();}
  }
  const source = fs.readFileSync(path.join(__dirname,'../../static/program-planner.js'),'utf8');
  const block = source.slice(source.indexOf("  let aiToken ="), source.indexOf("  el('plan-form').addEventListener('submit'"));
  const context = {el, FormData, scope:{region:'서울',district:'강남구'}, selected:new Map(),
    withoutFacility:()=>true, confirmed:true, generating:false, performance:{now:()=>0},
    setTimeout:()=>1, clearTimeout(){}, setInterval:()=>1, clearInterval(){},
    response:async()=>{calls++; return {json:async()=>({html:'분석 결과',token:'signed-token'})};}};
  vm.createContext(context);
  vm.runInContext(block+';globalThis.sync=syncGenerate;',context);
  context.sync();
  assert.equal(el('plan-generate').disabled,true);
  el('plan-ai-skip').checked=true;
  el('plan-ai-skip').handlers.change();
  assert.equal(el('plan-generate').disabled,false);
  assert.equal(el('plan-ai-include').disabled,true);
  el('plan-ai-skip').checked=false; el('plan-ai-skip').handlers.change();
  assert.equal(el('plan-generate').disabled,true);
  await el('plan-ai-open').handlers.click();
  assert.equal(calls,1);
  assert.equal(el('plan-generate').disabled,false);
  assert.equal(el('plan-ai-open').disabled,true);
  assert.equal(el('plan-ai-skip-row').hidden,true);
  await el('plan-ai-open').handlers.click();
  assert.equal(calls,1,'unchanged input cannot request another score');
  el('plan-form').handlers.change();
  assert.equal(el('plan-ai-open').disabled,true,'no-op changes retain result');
  name='변경된 프로그램'; el('plan-form').handlers.input();
  assert.equal(el('plan-ai-content').innerHTML,'분석 결과');
  assert.equal(el('plan-ai-panel').dataset.aiState,'stale');
  assert.equal(el('plan-ai-open').disabled,false);
  assert.equal(el('plan-ai-skip-row').hidden,false);
  assert.equal(el('plan-generate').disabled,true);
  assert.equal(el('plan-ai-include').checked,false);
  await el('plan-ai-open').handlers.click();
  assert.equal(calls,2);
});
