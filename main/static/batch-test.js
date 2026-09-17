(function () {
  'use strict';

  var dialog = document.getElementById('batch-test-dialog');
  if (!dialog) {
    return;
  }

  var openButton = document.querySelector('[data-batch-dialog-open]');
  var closeButton = dialog.querySelector('[data-batch-dialog-close]');
  var runButton = dialog.querySelector('[data-batch-run]');
  var clearLogButton = dialog.querySelector('[data-batch-clear-log]');
  var runForm = document.getElementById('batch-test-run-form');
  var clearLogForm = document.getElementById('batch-test-clear-log-form');
  var statusBody = document.getElementById('batch-test-status-body');
  var progressBadge = dialog.querySelector('[data-batch-progress]');
  var pollTimer = null;

  function stopPolling() {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }

  function csrfToken() {
    var item = document.cookie.split('; ').find(function (cookie) {
      return cookie.startsWith('csrftoken=');
    });
    return item ? decodeURIComponent(item.split('=').slice(1).join('=')) : '';
  }

  function showLoadError() {
    statusBody.replaceChildren();
    var message = document.createElement('p');
    message.className = 'batch-test-error';
    message.textContent = '배치 상태를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
    statusBody.appendChild(message);
    runButton.disabled = false;
    clearLogButton.disabled = false;
  }

  function syncControls() {
    stopPolling();
    var status = statusBody.querySelector('[data-batch-running]');
    var running = status && status.dataset.batchRunning === 'true';
    var progress = status ? status.dataset.batchProgress : '0';
    progressBadge.textContent = progress + '%';
    runButton.disabled = Boolean(running);
    clearLogButton.disabled = Boolean(running);
    runButton.textContent = running ? '배치 실행 중' : '최신화 실행';
    if (running && dialog.open) {
      pollTimer = window.setTimeout(loadStatus, 1500);
    }
  }

  async function renderResponse(response) {
    statusBody.innerHTML = await response.text();
    syncControls();
  }

  async function loadStatus() {
    try {
      var response = await fetch(dialog.dataset.statusUrl, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      if (!response.ok) {
        throw new Error('상태 조회 실패');
      }
      await renderResponse(response);
    } catch (error) {
      stopPolling();
      showLoadError();
    }
  }

  openButton.addEventListener('click', function () {
    if (!dialog.open) {
      dialog.showModal();
    }
    loadStatus();
  });

  closeButton.addEventListener('click', function () {
    dialog.close();
  });

  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  dialog.addEventListener('close', stopPolling);

  runForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (!window.confirm('서울 운영 데이터를 지금 최신화하시겠습니까?')) {
      return;
    }

    runButton.disabled = true;
    runButton.textContent = '실행 요청 중';
    try {
      var response = await fetch(runForm.action, {
        method: 'POST',
        body: new FormData(runForm),
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      await renderResponse(response);
    } catch (error) {
      stopPolling();
      showLoadError();
    }
  });

  clearLogForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (!window.confirm('최근 배치 로그를 초기화하시겠습니까? Manifest와 실행 상태는 유지됩니다.')) {
      return;
    }

    clearLogButton.disabled = true;
    clearLogButton.textContent = '초기화 중';
    try {
      var response = await fetch(clearLogForm.action, {
        method: 'POST',
        body: new FormData(clearLogForm),
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      await renderResponse(response);
      clearLogButton.textContent = '로그 초기화';
    } catch (error) {
      clearLogButton.textContent = '로그 초기화';
      stopPolling();
      showLoadError();
    }
  });
})();
