(function () {
  'use strict';

  var dialog = document.getElementById('manual-dialog');
  if (!dialog) return;

  var openButton = document.querySelector('[data-manual-open]');
  var closeButton = dialog.querySelector('[data-manual-close]');
  var tabs = Array.from(dialog.querySelectorAll('[data-manual-tab]'));
  var panels = Array.from(dialog.querySelectorAll('[data-manual-panel]'));
  var supportedSections = tabs.map(function (tab) { return tab.dataset.manualTab; });

  function selectSection(section, moveFocus) {
    var selected = supportedSections.includes(section) ? section : 'overview';
    tabs.forEach(function (tab) {
      var active = tab.dataset.manualTab === selected;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && moveFocus) tab.focus();
    });
    panels.forEach(function (panel) {
      panel.hidden = panel.dataset.manualPanel !== selected;
    });
    dialog.querySelector('.manual-body').scrollTop = 0;
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener('click', function () {
      selectSection(tab.dataset.manualTab, false);
    });
    tab.addEventListener('keydown', function (event) {
      var targetIndex = null;
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') targetIndex = (index + 1) % tabs.length;
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') targetIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') targetIndex = 0;
      if (event.key === 'End') targetIndex = tabs.length - 1;
      if (targetIndex === null) return;
      event.preventDefault();
      selectSection(tabs[targetIndex].dataset.manualTab, true);
    });
  });

  openButton.addEventListener('click', function () {
    if (!dialog.open) dialog.showModal();
    selectSection(dialog.dataset.defaultSection, true);
  });

  closeButton.addEventListener('click', function () {
    dialog.close();
  });

  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) dialog.close();
  });
})();
