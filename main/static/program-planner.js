/* In-memory wizard: no localStorage, sessionStorage or saved plan endpoint. */
(function () {
  'use strict';
  const root = document.getElementById('program-planner');
  if (!root) return;
  const el = id => document.getElementById(id);
  const selected = new Map();
  let scope = {}, page = 1, pages = 1, rows = [], listVersion = 0, detailVersion = 0;
  let confirmed = false, generating = false;
  const message = text => { el('plan-status').textContent = text; };
  function stage(index) {
    document.body.dataset.planStep = index;
    el('dashboard-body').hidden = index !== 0;
    root.hidden = index === 0;
    el('plan-region-again').hidden = index === 0;
    document.querySelectorAll('.planner-steps li').forEach((item, i) => {
      item.classList.toggle('complete', i < index);
      if (i === index) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    if (index === 0) window.dispatchEvent(new Event('resize'));
  }
  function updateCount() {
    el('plan-selected-count').textContent = `선택 ${selected.size}곳 / 최대 20곳`;
    el('plan-confirm').disabled = !selected.size;
  }
  function resetSelection() {
    listVersion++; detailVersion++;
    selected.clear(); confirmed = false; rows = []; page = 1;
    el('plan-candidates').replaceChildren();
    el('plan-detail').textContent = '시설의 상세보기를 눌러 정보를 확인하세요.';
    el('plan-count').textContent = ''; el('plan-page').textContent = '';
    el('plan-prev').disabled = true; el('plan-next').disabled = true;
    el('plan-entry').hidden = true;
    updateCount();
  }
  function readScope() {
    const node = el('plan-scope');
    if (!node) return;
    const next = {region: node.dataset.region, district: node.dataset.district};
    if (next.region !== scope.region || next.district !== scope.district) {
      resetSelection(); el('plan-sport').value = ''; el('plan-query').value = '';
      el('plan-selection').hidden = true; el('plan-start').hidden = false;
      stage(0); message('');
    }
    scope = next;
    el('plan-context').textContent = scope.region
      ? `선택 지역: ${scope.region} ${scope.district || '전체'} · 지역은 언제든 다시 선택할 수 있습니다.`
      : '위 지도에서 시·도를 선택한 후 계획서 생성을 시작하세요.';
    el('plan-start').disabled = !scope.region;
  }
  function params() {
    return new URLSearchParams({...scope, sport: el('plan-sport').value});
  }
  async function response(url, options) {
    const result = await fetch(url, {cache: 'no-store', ...options});
    if (!result.ok) {
      const error = await result.json().catch(() => ({}));
      throw new Error(error.errors ? Object.values(error.errors).flat().join(' ') : error.error || '요청에 실패했습니다. 잠시 후 다시 시도하세요.');
    }
    return result;
  }
  async function inspect(row) {
    const version = ++detailVersion;
    el('plan-detail').textContent = '시설 상세와 교통 정보를 불러오는 중입니다…';
    root.querySelectorAll('[data-inspect]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.inspect === row.id)));
    const query = params(); query.set('id', row.id);
    try {
      const result = await response(root.dataset.detailUrl + '?' + query);
      const html = await result.text();
      if (version !== detailVersion) return;
      el('plan-detail').innerHTML = html;
      el('plan-detail').dataset.facility = row.id;
      const label = document.createElement('label'); label.className = 'detail-select';
      const check = document.createElement('input'); check.type = 'checkbox';
      check.checked = selected.has(row.id); check.id = 'plan-detail-check';
      check.addEventListener('change', () => {
        if (check.checked && selected.size >= 20) {check.checked = false; message('시설은 최대 20곳까지 선택할 수 있습니다.'); return;}
        if (check.checked) selected.set(row.id, row); else selected.delete(row.id);
        renderRows(); updateCount();
      });
      label.append(check, document.createTextNode('이 시설을 계획서에 포함하기'));
      el('plan-detail').append(label);
    } catch (error) {
      if (version === detailVersion) el('plan-detail').textContent = error.message + ' 상세보기를 다시 눌러 재시도하세요.';
    }
  }
  function renderRows() {
    el('plan-candidates').replaceChildren();
    rows.forEach(row => {
      const card = document.createElement('div'); card.className = 'plan-candidate';
      const check = document.createElement('input'); check.type = 'checkbox';
      check.id = 'choose-' + row.id; check.checked = selected.has(row.id);
      const label = document.createElement('label'); label.htmlFor = check.id; label.textContent = '계획서에 포함';
      const address = document.createElement('small'); address.textContent = row.address;
      check.addEventListener('change', () => {
        if (check.checked && selected.size >= 20) {check.checked = false; message('시설은 최대 20곳까지 선택할 수 있습니다.'); return;}
        if (check.checked) selected.set(row.id, row); else selected.delete(row.id);
        confirmed = false; updateCount();
        const detailCheck = el('plan-detail-check');
        if (detailCheck && el('plan-detail').dataset.facility === row.id) detailCheck.checked = check.checked;
      });
      const button = document.createElement('button'); button.type = 'button';
      const photo = document.createElement('img'); photo.src = row.photo; photo.alt = '대표 이미지';
      const copy = document.createElement('span'); copy.textContent = row.name; copy.append(address);
      const hint = document.createElement('small'); hint.textContent = row.type + ' · 상세정보 보기 →'; copy.append(hint);
      button.append(photo, copy);
      button.dataset.inspect = row.id; button.setAttribute('aria-label', row.name + ' 상세보기');
      button.setAttribute('aria-pressed', String(el('plan-detail').dataset.facility === row.id));
      button.addEventListener('click', () => inspect(row));
      label.prepend(check); card.append(button, label); el('plan-candidates').append(card);
    });
  }
  async function load() {
    if (!el('plan-sport').value) return;
    const version = ++listVersion; detailVersion++;
    const query = params(); query.set('page', page); query.set('q', el('plan-query').value);
    message('조건에 맞는 시설을 불러오는 중입니다…');
    el('plan-candidates').replaceChildren();
    el('plan-detail').textContent = '시설 목록을 불러오는 중입니다…';
    el('plan-prev').disabled = true; el('plan-next').disabled = true;
    try {
      const data = await (await response(root.dataset.listUrl + '?' + query)).json();
      if (version !== listVersion) return;
      rows = data.rows; page = data.page; pages = data.pages;
      // Refresh signed identities for already selected rows on the current page.
      rows.forEach(row => {if (selected.has(row.id)) selected.set(row.id, row);});
      renderRows();
      el('plan-count').textContent = `조건에 맞는 시설 ${data.count.toLocaleString()}곳`;
      el('plan-page').textContent = `${page} / ${pages}`;
      el('plan-prev').disabled = page <= 1; el('plan-next').disabled = page >= pages;
      message(data.count ? '상세 정보를 확인한 후 이용할 시설을 체크하세요.' : '조건에 맞는 시설이 없습니다. 종목·지역 또는 검색어를 변경하세요.');
      if (rows.length) inspect(rows[0]); else el('plan-detail').textContent = '조회된 시설이 없습니다.';
    } catch (error) {if (version === listVersion) {message(error.message); el('plan-detail').textContent = '시설 검색을 눌러 다시 시도하세요.';}}
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('#plan-start')) return;
    confirmed = false; el('plan-entry').hidden = true;
    el('plan-start').hidden = true; el('plan-selection').hidden = false; stage(1); el('plan-sport').focus();
    if (el('plan-sport').value) load();
  });
  function backToRegion() {
    stage(0); el('plan-start').hidden = false;
    el('dashboard-region').scrollIntoView({behavior: 'smooth', block: 'center'}); el('dashboard-region').focus();
  }
  el('plan-region-again').addEventListener('click', backToRegion);
  el('plan-back-region').addEventListener('click', backToRegion);
  el('plan-sport').addEventListener('change', () => {resetSelection(); stage(1); el('plan-query').value = ''; load();});
  el('plan-search').addEventListener('submit', event => {event.preventDefault(); page = 1; load();});
  el('plan-prev').addEventListener('click', () => {page--; load();});
  el('plan-next').addEventListener('click', () => {page++; load();});
  el('plan-confirm').addEventListener('click', () => {
    if (!selected.size) return;
    confirmed = true; el('plan-selection').hidden = true; el('plan-entry').hidden = false;
    el('plan-confirmed').replaceChildren();
    selected.forEach(row => {const li = document.createElement('li'); li.textContent = row.name + ' · ' + row.address; el('plan-confirmed').append(li);});
    stage(2); message('시설을 확정했습니다. 프로그램 내용을 입력하세요.'); el('plan-form').elements.name.focus();
  });
  el('plan-reselect').addEventListener('click', () => {
    confirmed = false; el('plan-entry').hidden = true; el('plan-selection').hidden = false; stage(1); load();
  });
  el('plan-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (generating || !confirmed || !selected.size) return;
    generating = true; root.inert = true; el('dashboard-body').inert = true;
    const data = new FormData(event.target);
    data.set('region', scope.region); data.set('district', scope.district); data.set('sport', el('plan-sport').value);
    selected.forEach(row => data.append('facilities', row.token));
    message('입력 내용을 확인하고 계획서를 만드는 중입니다…');
    try {
      const html = await (await response(root.dataset.previewUrl, {method: 'POST', body: data})).text();
      el('plan-result-content').innerHTML = html;
      el('plan-share-status').textContent = '';
      el('plan-result').showModal();
      el('plan-form').reset(); resetSelection();
      el('plan-sport').value = ''; el('plan-query').value = ''; el('plan-selection').hidden = true;
      el('plan-start').hidden = false; stage(0); message('');
      window.htmx.ajax('GET', '/dashboard', {target: '#dashboard-body', swap: 'innerHTML'}).then(() => {
        history.replaceState(null, '', '/dashboard');
      }).catch(() => message('계획서는 생성되었습니다. 지역 초기화 조회에 실패하여 기존 현황이 남아 있습니다.'));
    } catch (error) {message(error.message);}
    finally {generating = false; root.inert = false; el('dashboard-body').inert = false;}
  });
  el('plan-print').addEventListener('click', () => window.print());
  let printDetails = [];
  window.addEventListener('beforeprint', () => {
    printDetails = Array.from(el('plan-result-content').querySelectorAll('details:not([open])'));
    printDetails.forEach(detail => {detail.open = true;});
  });
  window.addEventListener('afterprint', () => {
    printDetails.forEach(detail => {detail.open = false;}); printDetails = [];
  });
  el('plan-sms').addEventListener('click', () => {
    openShare('문자 보내기', '문자 전송 서비스를 연결하지 않아 발송할 수 없습니다. 발신번호·수신자 및 서비스 설정이 필요합니다.', true);
  });
  el('plan-kakao').addEventListener('click', () => {
    openShare('카카오톡 보내기', '카카오톡 공유 서비스를 연결하지 않아 전송할 수 없습니다. 앱 키와 공유 도메인 설정이 필요합니다.', false);
  });
  function openShare(title, help, recipient) {
    el('plan-share-title').textContent = title;
    el('plan-share-help').textContent = help;
    el('plan-recipient-label').hidden = !recipient;
    el('plan-share-message').value = el('plan-result-content').innerText;
    el('plan-share-dialog').showModal();
  }
  el('plan-share-close').addEventListener('click', () => el('plan-share-dialog').close());
  el('plan-share-dialog').addEventListener('close', () => {
    el('plan-share-message').value = ''; el('plan-recipient').value = '';
  });
  el('plan-close').addEventListener('click', () => el('plan-result').close());
  el('plan-result').addEventListener('close', () => {
    el('plan-result-content').replaceChildren(); el('plan-share-status').textContent = ''; el('plan-start').focus();
  });
  document.addEventListener('htmx:beforeRequest', event => {
    if (event.detail.target && event.detail.target.id === 'dashboard-body') root.inert = true;
  });
  document.addEventListener('htmx:afterRequest', event => {
    if (event.detail.target && event.detail.target.id === 'dashboard-body') root.inert = false;
  });
  document.addEventListener('htmx:afterSwap', event => {if (event.detail.target.id === 'dashboard-body') readScope();});
  readScope();
})();
