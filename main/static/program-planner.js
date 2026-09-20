/* Wizard inputs stay in memory; the last five signed results stay in this browser. */
(function () {
  'use strict';
  const root = document.getElementById('program-planner');
  if (!root) return;
  const el = id => document.getElementById(id);
  const printArea = document.getElementById('plan-print-area');
  const selected = new Map();
  let scope = {}, page = 1, pages = 1, rows = [], listVersion = 0, detailVersion = 0;
  let confirmed = false, generating = false, lastPlan = null, listLoading = false;
  const historyKey = 'sport-insight.plan-history.v1';
  let historyRows = [], restoring = false, resultOpener = null;
  function historyNote(text) { el('plan-history-status').textContent = text; }
  function readHistory() {
    try {
      const saved = JSON.parse(localStorage.getItem(historyKey) || '[]');
      if (!Array.isArray(saved)) throw new Error('Invalid history');
      return saved.filter(item => item && typeof item.snapshot === 'string'
        && item.snapshot.length <= 1000000 && typeof item.name === 'string'
        && typeof item.created === 'string' && Number.isFinite(Date.parse(item.created)))
        .slice(0, 5);
    } catch (error) {
      historyNote('브라우저 보관함을 읽을 수 없습니다. 새 계획서 생성과 인쇄는 계속 사용할 수 있습니다.');
      return [];
    }
  }
  function writeHistory(next) {
    try {
      localStorage.setItem(historyKey, JSON.stringify(next.slice(0, 5)));
      historyRows = next.slice(0, 5); renderHistory();
      return true;
    } catch (error) {
      historyNote('브라우저 저장 공간 또는 설정 때문에 보관함을 변경하지 못했습니다.');
      return false;
    }
  }
  function renderHistory() {
    el('plan-history-list').replaceChildren();
    el('plan-history-count').textContent = `${historyRows.length} / 5`;
    el('plan-history-empty').hidden = historyRows.length > 0;
    el('plan-history-clear').disabled = historyRows.length === 0 || restoring;
    el('plan-history-close').disabled = restoring;
    historyRows.forEach(item => {
      const li = document.createElement('li');
      const copy = document.createElement('div');
      const title = document.createElement('b'); title.textContent = item.name;
      const details = document.createElement('small');
      details.textContent = `${item.region || ''} ${item.district || ''} · ${item.sport || ''} · ${new Date(item.created).toLocaleString('ko-KR')}`;
      copy.append(title, details);
      const actions = document.createElement('div'); actions.className = 'plan-history-actions';
      const open = document.createElement('button'); open.type = 'button'; open.className = 'button ghost';
      open.textContent = '다시 열기'; open.disabled = restoring;
      open.setAttribute('aria-label', `${item.name} 다시 열기`);
      open.addEventListener('click', () => restoreHistory(item));
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'button ghost';
      remove.textContent = '삭제'; remove.disabled = restoring;
      remove.setAttribute('aria-label', `${item.name} 삭제`);
      remove.addEventListener('click', () => {
        if (writeHistory(readHistory().filter(row => row.snapshot !== item.snapshot))) historyNote('계획서를 삭제했습니다.');
      });
      actions.append(open, remove); li.append(copy, actions); el('plan-history-list').append(li);
    });
  }
  async function restoreHistory(item) {
    if (restoring || generating) return;
    restoring = true; renderHistory(); historyNote('저장된 계획서를 불러오는 중입니다…');
    root.inert = true; el('dashboard-body').inert = true;
    const data = new FormData();
    data.set('csrfmiddlewaretoken', el('plan-form').elements.csrfmiddlewaretoken.value);
    data.set('snapshot', item.snapshot);
    try {
      const result = await (await response(root.dataset.restoreUrl, {method: 'POST', body: data})).json();
      // Only verified server output goes into the preview, never stored HTML.
      lastPlan = result.summary;
      el('plan-result-content').innerHTML = result.html;
      el('plan-share-status').textContent = '최근 생성 목록에서 열었습니다. 생성 당시 자료 기준입니다.';
      resultOpener = el('plan-history-open');
      el('plan-history').close();
      // 과거 결과 조회는 새 설계 흐름의 단계를 변경하지 않는다.
      el('plan-result').showModal(); historyNote('');
    } catch (error) {historyNote(error.message);}
    finally {restoring = false; root.inert = false; el('dashboard-body').inert = false; renderHistory();}
  }
  el('plan-history-clear').addEventListener('click', () => {
    if (writeHistory([])) historyNote('최근 생성 목록을 모두 삭제했습니다.');
  });
  el('plan-history-open').addEventListener('click', () => {
    historyRows = readHistory(); renderHistory();
    el('plan-history').showModal();
  });
  el('plan-history-close').addEventListener('click', () => el('plan-history').close());
  el('plan-history').addEventListener('cancel', event => { if (restoring) event.preventDefault(); });
  window.addEventListener('storage', event => {
    if (event.key === historyKey || event.key === null) {historyRows = readHistory(); renderHistory();}
  });
  historyRows = readHistory(); renderHistory();
  const message = text => { el('plan-status').textContent = text; el('plan-error').textContent = ''; };
  /* A refusal or a failure reads differently from progress, so it gets its own
     alert region rather than sharing the polite status line. */
  const failure = text => {
    el('plan-error').textContent = text; el('plan-status').textContent = '';
    /* The submit button sits at the bottom of the wizard while this alert sits
       at the top, so a refusal used to look like a dead button. Deferred
       because the submit handler clears `inert` in its `finally`, and
       focus is ignored while an ancestor is still inert. A timeout, not
       requestAnimationFrame: a background tab suppresses the frame callback
       entirely, and this only needs to run after the current task. */
    if (!text) return;
    setTimeout(() => {
      const box = el('plan-error');
      if (box.textContent !== text) return;
      box.scrollIntoView({block: 'center', behavior: 'smooth'});
      box.focus();
    });
  };
  function detailNote(text) {
    const box = document.createElement('div');
    box.className = 'plan-detail-content';
    const line = document.createElement('p');
    line.textContent = text;
    box.append(line);
    el('plan-detail').replaceChildren(box);
    delete el('plan-detail').dataset.facility;
  }
  function stage(index) {
    document.body.dataset.planStep = index;
    el('plan-history-open').hidden = index !== 0;
    /* Step 4 marks the finished plan while the result dialog is open. The
       wizard behind it is already reset, so its visibility is left alone. */
    if (index < 3) {
      el('dashboard-body').hidden = index !== 0;
      root.hidden = index === 0;
      el('plan-step-one-result').hidden = index === 0;
      el('plan-step-actions').hidden = index !== 1;
      el('plan-entry-actions').hidden = index !== 2;
      el('plan-sport-summary-row').hidden = index !== 2;
    }
    document.querySelectorAll('.planner-steps li').forEach((item, i) => {
      const visibleStep = Math.min(index, 2);
      item.classList.toggle('complete', i < visibleStep);
      if (i === visibleStep) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    if (index === 0) window.dispatchEvent(new Event('resize'));
  }
  function updateCount() {
    el('plan-selected-count').textContent = `선택 ${selected.size}곳 / 최대 20곳`;
    el('plan-confirm').disabled = listLoading || (!selected.size && !withoutFacility());
  }
  function withoutFacility() {
    return !el('plan-without-facility').hidden && el('plan-without-facility-check').checked;
  }
  function resetWithoutFacility() {
    el('plan-without-facility').hidden = true;
    el('plan-without-facility-check').checked = false;
    el('plan-pagination').hidden = true;
  }
  function setListLoading(loading) {
    listLoading = loading;
    el('plan-loading').hidden = !loading;
    el('plan-facility-grid').inert = loading;
    el('plan-facility-grid').setAttribute('aria-busy', String(loading));
    updateCount();
  }
  function resetSelection() {
    listVersion++; detailVersion++;
    resetWithoutFacility();
    setListLoading(false);
    selected.clear(); confirmed = false; rows = []; page = 1;
    el('plan-candidates').replaceChildren();
    detailEmpty('종목과 시설을 선택해 주세요.', '종목을 선택하면 해당 지역의 후보 시설을 확인할 수 있습니다.');
    el('plan-count').textContent = ''; el('plan-page').textContent = '';
    el('plan-prev').disabled = true; el('plan-next').disabled = true;
    el('plan-entry').hidden = true;
    updateCount();
  }
  function readScope() {
    const node = el('plan-scope');
    if (!node) return;
    // The picker changes these fields before statistics are refreshed by HTMX.
    const next = {
      region: el('dashboard-region')?.value ?? node.dataset.region,
      district: el('dashboard-district')?.value ?? node.dataset.district,
    };
    if (next.region !== scope.region || next.district !== scope.district) {
      resetSelection(); el('plan-sport').value = ''; el('plan-query').value = '';
      el('plan-selection').hidden = true; el('plan-start').hidden = false;
      if (!el('plan-result').open) stage(0);
      message('');
    }
    scope = next;
    const regions = el('plan-context');
    regions.replaceChildren();
    const districts = scope.district ? scope.district.split(',').filter(Boolean) : ['전체'];
    districts.forEach(district => {
      const chip = document.createElement('span');
      chip.className = 'plan-region-chip';
      chip.textContent = scope.region ? `${scope.region} ${district}` : '지역 미선택';
      regions.append(chip);
    });
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
    detailNote('시설 상세와 교통 정보를 불러오는 중입니다…');
    root.querySelectorAll('[data-inspect]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.inspect === row.id)));
    const query = params(); query.set('id', row.id);
    try {
      const result = await response(root.dataset.detailUrl + '?' + query);
      const html = await result.text();
      if (version !== detailVersion) return;
      el('plan-detail').innerHTML = html;
      el('plan-detail').dataset.facility = row.id;
      const check = el('plan-detail-check');
      if (check) {
        check.checked = selected.has(row.id);
        check.addEventListener('change', () => {
          if (check.checked && selected.size >= 20) {check.checked = false; failure('시설은 최대 20곳까지 선택할 수 있습니다.'); return;}
          if (check.checked) selected.set(row.id, row); else selected.delete(row.id);
          renderRows(); updateCount();
        });
      }
    } catch (error) {
      if (version === detailVersion) detailNote(error.message + ' 상세보기를 다시 눌러 재시도하세요.');
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
        if (check.checked && selected.size >= 20) {check.checked = false; failure('시설은 최대 20곳까지 선택할 수 있습니다.'); return;}
        if (check.checked) selected.set(row.id, row); else selected.delete(row.id);
        confirmed = false; updateCount();
        const detailCheck = el('plan-detail-check');
        if (detailCheck && el('plan-detail').dataset.facility === row.id) detailCheck.checked = check.checked;
      });
      const button = document.createElement('button'); button.type = 'button';
      const photo = document.createElement('img'); photo.src = row.photo; photo.alt = '대표 이미지';
      const copy = document.createElement('span');
      const title = document.createElement('b'); title.textContent = row.name;
      copy.append(title, address);
      button.append(photo, copy);
      button.dataset.inspect = row.id; button.setAttribute('aria-label', row.name + ' 상세보기');
      button.setAttribute('aria-pressed', String(el('plan-detail').dataset.facility === row.id));
      button.addEventListener('click', () => inspect(row));
      label.prepend(check); card.append(button, label); el('plan-candidates').append(card);
    });
  }
  function detailEmpty(title, description) {
    el('plan-candidates-section').hidden = true;
    el('plan-facility-grid').dataset.empty = 'true';
    const content = document.createElement('div');
    content.className = 'plan-detail-content';
    const box = document.createElement('div');
    box.className = 'plan-empty';
    const heading = document.createElement('h4'); heading.textContent = title;
    const copy = document.createElement('p'); copy.textContent = description;
    box.append(heading, copy);
    content.append(box);
    el('plan-detail').replaceChildren(content);
    delete el('plan-detail').dataset.facility;
  }
  async function load() {
    if (!el('plan-sport').value) {
      detailEmpty('종목과 시설을 선택해 주세요.', '종목을 선택하면 해당 지역의 후보 시설을 확인할 수 있습니다.');
      return;
    }
    const version = ++listVersion; detailVersion++;
    resetWithoutFacility();
    setListLoading(true);
    const query = params(); query.set('page', page); query.set('q', el('plan-query').value);
    message('조건에 맞는 시설을 불러오는 중입니다…');
    el('plan-candidates').replaceChildren();
    el('plan-count').textContent = ''; el('plan-page').textContent = '';
    detailNote('시설 목록을 불러오는 중입니다…');
    el('plan-prev').disabled = true; el('plan-next').disabled = true;
    try {
      const data = await (await response(root.dataset.listUrl + '?' + query)).json();
      if (version !== listVersion) return;
      rows = data.rows; page = data.page; pages = data.pages;
      el('plan-candidates-section').hidden = !rows.length;
      el('plan-facility-grid').dataset.empty = String(!rows.length);
      el('plan-pagination').hidden = !rows.length;
      // Refresh signed identities for already selected rows on the current page.
      rows.forEach(row => {if (selected.has(row.id)) selected.set(row.id, row);});
      renderRows();
      el('plan-count').textContent = `${data.count.toLocaleString()}곳`;
      el('plan-page').textContent = rows.length ? `${page} / ${pages}` : '';
      el('plan-prev').disabled = !rows.length || page <= 1; el('plan-next').disabled = !rows.length || page >= pages;
      if (rows.length) message('상세 정보를 확인한 후 이용할 시설을 체크하세요.');
      else {
        // [SH260917] 검색어로 인한 빈 결과와 실제 매칭 후보 부재를 구분합니다.
        // 후보 자체가 없을 때만 체크 동의 후 시설 미정으로 다음 단계를 허용합니다.
        el('plan-without-facility').hidden = data.eligible_count !== 0 || selected.size > 0;
        const searched = Boolean(query.get('q').trim());
        const title = searched ? '검색 결과가 없습니다.' : '매칭되는 후보 시설이 없습니다.';
        detailEmpty(title, searched
          ? '시설명이나 주소 검색어를 바꾸거나 지운 뒤 다시 검색해 주세요.'
          : '선택한 지역·종목에 해당하는 시설이 자료에 없습니다. 종목을 변경하거나 이전 단계에서 지역을 다시 선택해 주세요. 실제 시설이 없다는 의미는 아닙니다.');
        message(title);
      }
      if (rows.length) inspect(rows[0]);
    } catch (error) {if (version === listVersion) {
      rows = [];
      detailEmpty('시설 목록을 불러오지 못했습니다.', '잠시 후 시설 검색 버튼을 눌러 다시 시도해 주세요.');
      failure(error.message);
    }}
    finally {if (version === listVersion) setListLoading(false);}
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('#plan-start')) return;
    readScope();
    if (!scope.region) return;
    confirmed = false; el('plan-entry').hidden = true;
    el('plan-start').hidden = true; el('plan-selection').hidden = false; stage(1); el('plan-sport').focus();
    if (el('plan-sport').value) load();
  });
  function backToRegion() {
    listVersion++; detailVersion++; setListLoading(false);
    stage(0); el('plan-start').hidden = false;
    el('dashboard-region').scrollIntoView({behavior: 'smooth', block: 'center'}); el('dashboard-region').focus();
  }
  el('plan-back-region').addEventListener('click', backToRegion);
  el('plan-without-facility-check').addEventListener('change', updateCount);
  el('plan-sport').addEventListener('change', () => {resetSelection(); stage(1); el('plan-query').value = ''; load();});
  el('plan-search').addEventListener('submit', event => {event.preventDefault(); page = 1; load();});
  el('plan-prev').addEventListener('click', () => {page--; load();});
  el('plan-next').addEventListener('click', () => {page++; load();});
  el('plan-confirm').addEventListener('click', () => {
    if (listLoading || (!selected.size && !withoutFacility())) return;
    confirmed = true; el('plan-selection').hidden = true; el('plan-entry').hidden = false;
    el('plan-confirmed').replaceChildren();
    if (!selected.size) {
      const note = document.createElement('li'); note.textContent = '매칭 후보 시설 없음 · 시설 미정으로 진행';
      el('plan-confirmed').append(note);
    }
    selected.forEach(row => {
      const li = document.createElement('li'); li.className = 'plan-confirmed-row';
      const photo = document.createElement('img'); photo.src = row.photo; photo.alt = ''; photo.loading = 'lazy';
      const copy = document.createElement('div');
      const title = document.createElement('b'); title.textContent = row.name;
      const note = document.createElement('small'); note.textContent = `${row.address} · ${row.type} · ${row.state}`;
      copy.append(title, note); li.append(photo, copy); el('plan-confirmed').append(li);
    });
    stage(2); message('시설을 확정했습니다. 프로그램 내용을 입력하세요.'); el('plan-form').elements.name.focus();
  });
  function backToSelection() {
    confirmed = false; el('plan-entry').hidden = true; el('plan-selection').hidden = false; stage(1); load();
    el('plan-sport').focus();
  }
  el('plan-back-selection').addEventListener('click', backToSelection);
  el('plan-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (generating || !confirmed || (!selected.size && !withoutFacility())) return;
    generating = true; root.inert = true; el('dashboard-body').inert = true;
    el('plan-entry-actions').inert = true;
    const data = new FormData(event.target);
    data.set('region', scope.region); data.set('district', scope.district); data.set('sport', el('plan-sport').value);
    selected.forEach(row => data.append('facilities', row.token));
    if (!selected.size && withoutFacility()) data.set('without_facility', 'on');
    message('입력 내용을 확인하고 계획서를 만드는 중입니다…');
    try {
      const result = await (await response(root.dataset.previewUrl, {
        method: 'POST', body: data, headers: {'Accept': 'application/json'},
      })).json();
      lastPlan = result.summary;
      const saved = result.snapshot && writeHistory([
        {...result.summary, snapshot: result.snapshot}, ...readHistory(),
      ]);
      el('plan-result-content').innerHTML = result.html;
      el('plan-share-status').textContent = saved
        ? '이 브라우저의 최근 생성 목록에 보관했습니다. (최대 5건)'
        : '계획서는 생성되었지만 브라우저에 보관하지 못했습니다. 지금 인쇄할 수 있습니다.';
      if (saved) historyNote('');
      resultOpener = el('plan-start');
      el('plan-result').showModal();
      el('plan-form').reset(); resetSelection();
      el('plan-sport').value = ''; el('plan-query').value = ''; el('plan-selection').hidden = true;
      el('plan-start').hidden = false; stage(0); message('');
      stage(3);
      window.htmx.ajax('GET', '/dashboard', {target: '#dashboard-body', swap: 'innerHTML'}).then(() => {
        history.replaceState(null, '', '/dashboard');
      }).catch(() => failure('계획서는 생성되었습니다. 지역 초기화 조회에 실패하여 기존 현황이 남아 있습니다.'));
    } catch (error) {failure(error.message);}
    finally {generating = false; root.inert = false; el('dashboard-body').inert = false; el('plan-entry-actions').inert = false;}
  });
  /* Reversed dates are the server's most common refusal (PlanForm.clean).
     The browser can rule them out up front: each date bounds the other, and
     an empty value lifts the bound. */
  const dateStart = el('plan-date-start'), dateEnd = el('plan-date-end');
  function syncDateBounds() {
    dateEnd.min = dateStart.value;
    dateStart.max = dateEnd.value;
  }
  dateStart.addEventListener('change', syncDateBounds);
  dateEnd.addEventListener('change', syncDateBounds);
  /* `reset` fires before the fields are cleared, so the bounds are recomputed
     on the next task rather than from the values still on screen. */
  el('plan-form').addEventListener('reset', () => setTimeout(syncDateBounds));
  el('plan-print').addEventListener('click', () => window.print());
  let printDetails = [];
  window.addEventListener('beforeprint', () => {
    printDetails = Array.from(el('plan-result-content').querySelectorAll('details:not([open])'));
    printDetails.forEach(detail => {detail.open = true;});
    /* A modal dialog sits in the top layer, and Chrome prints that layer as one
       page starting wherever the dialog is scrolled -- so a long plan comes out
       beginning halfway down. Print a copy placed in the ordinary document flow
       instead, which paginates like any other content. */
    if (printArea && el('plan-result').open) {
      document.body.append(printArea);
      printArea.replaceChildren(
        ...Array.from(el('plan-result-content').children, node => node.cloneNode(true)));
    }
  });
  window.addEventListener('afterprint', () => {
    printDetails.forEach(detail => {detail.open = false;}); printDetails = [];
    if (printArea) printArea.replaceChildren();
  });
  el('plan-sms').addEventListener('click', () => {
    openShare('문자 보내기', '문자 전송 서비스를 연결하지 않아 발송할 수 없습니다. 발신번호·수신자 및 서비스 설정이 필요합니다.', true);
  });
  el('plan-kakao').addEventListener('click', () => {
    openShare('카카오톡 보내기', '카카오톡 공유 서비스를 연결하지 않아 전송할 수 없습니다. 앱 키와 공유 도메인 설정이 필요합니다.', false);
  });
  function shareMessage() {
    if (!lastPlan) return '';
    const count = Number(lastPlan.fee) === 0 ? '무료'
      : Number(lastPlan.fee).toLocaleString('ko-KR') + '원 / 1인 / ' + lastPlan.unit + ' 기준';
    const names = lastPlan.facilities.length > 3
      ? lastPlan.facilities.slice(0, 3).join(', ') + ` 외 ${lastPlan.facilities.length - 3}곳`
      : lastPlan.facilities.join(', ');
    return ['[프로그램 설계안] ' + lastPlan.name,
            `${lastPlan.region} ${lastPlan.district || '전체'} · ${lastPlan.sport}`,
            `시설 ${lastPlan.facilities.length}곳: ${names}`,
            `시설별 모집 ${Number(lastPlan.capacity).toLocaleString('ko-KR')}명`,
            `수강료 ${count}`,
            '검토용 계획서이며 시설 대관·강좌 개설 확정 전입니다.'].join('\n');
  }
  function openShare(title, help, recipient) {
    el('plan-share-title').textContent = title;
    el('plan-share-help').textContent = help;
    el('plan-recipient-label').hidden = !recipient;
    el('plan-share-message').value = shareMessage();
    el('plan-share-dialog').showModal();
  }
  el('plan-share-close').addEventListener('click', () => el('plan-share-dialog').close());
  el('plan-share-dialog').addEventListener('close', () => {
    el('plan-share-message').value = ''; el('plan-recipient').value = '';
  });
  el('plan-close').addEventListener('click', () => el('plan-result').close());
  el('plan-close-top').addEventListener('click', () => el('plan-result').close());
  el('plan-result').addEventListener('close', () => {
    lastPlan = null;
    // 새로 생성한 결과만 초기 단계로 돌아간다. 최근 항목 조회는 그대로 유지한다.
    if (document.body.dataset.planStep === '3') stage(0);
    el('plan-result-content').replaceChildren(); el('plan-share-status').textContent = '';
    (resultOpener?.isConnected && !resultOpener.disabled ? resultOpener : el('plan-start')).focus();
    resultOpener = null;
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
