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

  function keyOf(element) {
    return element && element.dataset ? element.dataset.focusKey || null : null;
  }

  document.body.addEventListener('htmx:beforeRequest', function (event) {
    pending = keyOf(event.detail.elt) || keyOf(document.activeElement);
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

  /* The policy dialog is filled by htmx and opened once the content lands, so
   * the reader never sees an empty modal. <dialog> supplies the focus trap and
   * Escape handling; a click on the backdrop falls outside the inner panel. */
  var dialog = document.getElementById('policy-dialog');

  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (dialog && event.detail.target.id === 'policy-dialog-body' && !dialog.open) {
      dialog.showModal();
    }
  });

  document.body.addEventListener('click', function (event) {
    if (!dialog) {
      return;
    }
    if (event.target.closest('[data-close-dialog]')) {
      dialog.close();
    } else if (dialog && dialog.open && event.target === dialog) {
      dialog.close();
    }
  });

  document.body.addEventListener('htmx:responseError', function (event) {
    var region = event.detail.target;
    if (region) {
      region.setAttribute('data-load-error', event.detail.xhr.status);
    }
  });
})();
