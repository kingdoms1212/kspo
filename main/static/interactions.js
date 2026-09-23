/* Keyboard focus across htmx swaps.
 *
 * A swap destroys the control the user just activated, so the browser drops
 * focus to <body> and the next Tab restarts at the top of the document. The
 * page did not reload and the viewport did not move, so re-focusing the
 * replaced counterpart must not move it either: preventScroll keeps the
 * caret where the reader left it.
 *
 * Elements opt in with data-focus-key. Keys are stable across renders, so the
 * counterpart is found even though the element itself is a new node. */
(function () {
  'use strict';

  var pending = null;
  var dashboardScroll = null;

  function keyOf(element) {
    return element && element.dataset ? element.dataset.focusKey || null : null;
  }

  document.body.addEventListener('htmx:beforeRequest', function (event) {
    pending = keyOf(event.detail.elt) || keyOf(document.activeElement);
    if (event.detail.elt.closest && event.detail.elt.closest('#dashboard-filters')) {
      dashboardScroll = {x: window.scrollX, y: window.scrollY};
    }
  });

  document.body.addEventListener('htmx:afterSettle', function (event) {
    if (!dashboardScroll || event.detail.target.id !== 'dashboard-body') return;
    window.scrollTo({left: dashboardScroll.x, top: dashboardScroll.y, behavior: 'instant'});
    dashboardScroll = null;
  });
  document.body.addEventListener('htmx:afterRequest', function (event) {
    if (event.detail.failed) dashboardScroll = null;
  });

  document.body.addEventListener('htmx:afterSettle', function (event) {
    if (!pending) {
      return;
    }
    var key = pending;
    pending = null;
    if (event.detail.target.id === 'policy-dialog-body') {
      return;  // the dialog moves focus into itself
    }
    var target = document.querySelector('[data-focus-key="' + CSS.escape(key) + '"]');
    // A disabled counterpart (last page, deselected facility) has no focusable
    // node; fall back to the region that replaced it so Tab resumes nearby.
    if (!target) {
      target = event.target.querySelector('[data-focus-fallback]') || event.target;
    }
    if (target && typeof target.focus === 'function') {
      target.focus({ preventScroll: true });
    }
  });

  /* Open the policy dialog before the external listing request completes so
   * Render users get immediate feedback while the crawler is working. */
  var dialog = document.getElementById('policy-dialog');
  var policyBody = document.getElementById('policy-dialog-body');
  var policyLoading = document.getElementById('policy-dialog-loading');

  function showPolicyLoading() {
    if (!dialog || !policyBody || !policyLoading) return;
    policyBody.replaceChildren(policyLoading.content.cloneNode(true));
    if (!dialog.open) dialog.showModal();
  }

  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (dialog && event.detail.target.id === 'policy-dialog-body' && !dialog.open) {
      dialog.showModal();
    }
  });

  document.body.addEventListener('click', function (event) {
    if (!dialog) {
      return;
    }
    if (event.target.closest('.policy-open')) {
      showPolicyLoading();
    } else if (event.target.closest('[data-close-dialog],[data-policy-loading-close]')) {
      dialog.close();
    } else if (dialog && dialog.open && event.target === dialog) {
      dialog.close();
    }
  });

  document.body.addEventListener('htmx:afterRequest', function (event) {
    if (!dialog || !policyBody || event.detail.target.id !== 'policy-dialog-body' || !event.detail.failed) return;
    policyBody.innerHTML = '<div class="policy-empty" role="alert"><h3>정책 정보를 가져오지 못했습니다.</h3><p>잠시 후 주요 정책 보기를 다시 눌러 주세요.</p><button type="button" class="button ghost" data-close-dialog>닫기</button></div>';
  });



  /* Scroll position inside a swapped region.
   *
   * Picking a facility replaces the whole workspace, so the list is rebuilt and
   * its own scrollbar starts at the top again -- the row just clicked is gone
   * from view. The position is carried across the swap.
   *
   * Only controls that opt in with data-keep-scroll do this. Paging replaces
   * the list with different rows, where starting at the top is right. */
  var keptScroll = null;

  document.body.addEventListener('htmx:beforeRequest', function (event) {
    keptScroll = null;
    var control = event.detail.elt.closest && event.detail.elt.closest('[data-keep-scroll]');
    if (!control) {
      return;
    }
    var name = control.dataset.keepScroll;
    var region = document.querySelector('[data-scroll-region="' + CSS.escape(name) + '"]');
    if (region) {
      keptScroll = { name: name, top: region.scrollTop };
    }
  });

  document.body.addEventListener('htmx:afterSettle', function () {
    if (!keptScroll) {
      return;
    }
    var region = document.querySelector('[data-scroll-region="' + CSS.escape(keptScroll.name) + '"]');
    if (region) {
      region.scrollTop = keptScroll.top;
    }
    keptScroll = null;
  });

  /* Splash while a menu link loads.
   *
   * Navigation is a normal page load, so the browser keeps showing the old
   * screen until the next one is ready -- several seconds on a first visit,
   * which reads a CSV. The overlay says the click was received.
   *
   * It appears after a short delay so a warm, fast navigation does not flash,
   * and `pageshow` hides it again, including when the back button restores
   * this page from the cache with the overlay still up. */
  var SPLASH_DELAY = 150;
  var SPLASH_SAFETY = 60000;
  var splash = document.getElementById('app-splash');
  var splashText = document.getElementById('app-splash-text');
  var splashTimer = null;
  var splashSafety = null;

  function hideSplash() {
    window.clearTimeout(splashTimer);
    window.clearTimeout(splashSafety);
    if (splash) {
      splash.hidden = true;
      document.body.removeAttribute('aria-busy');
    }
  }

  function scheduleSplash(label) {
    if (!splash) {
      return;
    }
    window.clearTimeout(splashTimer);
    splashTimer = window.setTimeout(function () {
      // Writing the text as it appears gives the live region something to read.
      if (splashText) {
        splashText.textContent = label + ' 화면을 불러오는 중입니다. 자료를 읽느라 잠시 걸립니다.';
      }
      splash.hidden = false;
      document.body.setAttribute('aria-busy', 'true');
      splashSafety = window.setTimeout(hideSplash, SPLASH_SAFETY);
    }, SPLASH_DELAY);
  }

  document.body.addEventListener('click', function (event) {
    var link = event.target.closest('.nav-link, .global-brand');
    if (!link || event.defaultPrevented) {
      return;
    }
    // Leave modified clicks alone: they open a tab rather than navigating here.
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    if (link.target && link.target !== '_self') {
      return;
    }
    if (link.getAttribute('aria-current') === 'page') {
      return;
    }
    scheduleSplash(link.textContent.trim() || '요청한');
  });

  window.addEventListener('pageshow', hideSplash);

  document.body.addEventListener('htmx:responseError', function (event) {
    var region = event.detail.target;
    if (region) {
      region.setAttribute('data-load-error', event.detail.xhr.status);
    }
  });
})();
