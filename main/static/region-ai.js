(() => {
let running = false;
let pending = null;
async function analyze(button) {
  if (!button || !button.isConnected || button.disabled) return;
  // Queue only the latest region while a previous request finishes.
  if (running) { pending = button; return; }
  running = true;
  const card = button.closest('[data-ai-district]'), result = card.querySelector('[data-ai-region-result]');
  const status = card.querySelector('[data-ai-region-status]');
  const label = card.querySelector('[data-ai-region-label]');
  const title = card.querySelector('[data-ai-region-title]');
  const hint = card.querySelector('[data-ai-region-hint]');
  const elapsed = card.querySelector('[data-ai-region-elapsed]');
  const started = performance.now();
  let succeeded = false;
  card.dataset.aiState = 'loading';
  button.setAttribute('aria-busy', 'true');
  hint.textContent = '지역 데이터를 해석하고 있어요';
  elapsed.hidden = false;
  elapsed.textContent = '0초 경과';
  const timer = setInterval(() => {
    if (!card.isConnected) { clearInterval(timer); return; }
    elapsed.textContent = `${Math.floor((performance.now() - started) / 1000)}초 경과`;
  }, 1000);
  status.textContent = '분석 중'; label.textContent = '분석 중';
  title.textContent = '지역 데이터를 분석하고 있습니다';
  button.disabled = true; result.textContent = 'AI 현황 해석 중입니다. 재시도 시 수 분이 걸릴 수 있습니다.';
  result.setAttribute('aria-busy', 'true');
  const data = new FormData(); data.set('district', card.dataset.aiDistrict);
  data.set('csrfmiddlewaretoken', card.querySelector('[name=csrfmiddlewaretoken]').value);
  try {
    const response = await fetch('/dashboard/ai/region', {method: 'POST', body: data});
    // [SG003] AI기능 연동 시 예외처리 보완 — JSON이 아닌 오류 응답에도 안내를 표시합니다.
    const payload = await response.json().catch(() => {throw new Error('서버 응답을 읽지 못했습니다. 잠시 후 다시 시도해 주세요.');});
    if (!response.ok) throw new Error(payload.error || '분석을 가져오지 못했습니다.');
    if (!card.isConnected) return;
    if (!payload.result || typeof payload.result.summary !== 'string' || !Array.isArray(payload.result.features) || !Array.isArray(payload.result.considerations)) throw new Error('분석 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.');
    result.replaceChildren();
    status.textContent = payload.cached ? '저장된 분석' : '분석 완료';
    title.textContent = '선택 지역의 AI 분석 결과입니다';
    const paragraph = document.createElement('p'); paragraph.className = 'ai-region-summary'; paragraph.textContent = payload.result.summary; result.append(paragraph);
    const columns = document.createElement('div'); columns.className = 'ai-region-columns';
    for (const [key, title] of [['features', '눈여겨볼 특징'], ['considerations', '기획 시 확인할 점']]) {
      const heading = document.createElement('h3'); heading.textContent = title;
      const list = document.createElement('ul');
      payload.result[key].forEach(text => {const item = document.createElement('li'); item.textContent = text; list.append(item);});
      const section = document.createElement('section'); section.append(heading, list); columns.append(section);
    }
    result.append(columns);
    const note = document.createElement('p'); note.className = 'chart-note';
    note.textContent = '분석 근거: 시설 · 강좌 · 신청 실적. AI가 작성한 참고 의견이며, 신청 실적은 지역 전체 수요나 고유 이용자 수가 아닙니다.'; result.append(note);
    succeeded = true;
  } catch (error) {
    if (!card.isConnected) return;
    result.textContent = error.message; status.textContent = '분석 실패';
    title.textContent = '분석을 완료하지 못했습니다';
  }
  finally {
    clearInterval(timer);
    elapsed.hidden = true;
    card.dataset.aiState = succeeded ? 'complete' : 'error';
    hint.textContent = succeeded ? '분석 결과를 아래에서 확인하세요' : '잠시 후 다시 시도해 주세요';
    button.disabled = false;
    button.setAttribute('aria-busy', 'false');
    label.textContent = succeeded ? '다시 분석하기' : '다시 시도하기';
    result.setAttribute('aria-busy', 'false');
    running = false;
    const next = pending; pending = null;
    if (next && next.isConnected) analyze(next);
  }
}
document.addEventListener('click', event => analyze(event.target.closest('[data-ai-region]')));
// Analysis runs only when the user activates the AI button.
})();
