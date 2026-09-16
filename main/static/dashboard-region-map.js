/* Only update form controls: never mutate or observe the shared map renderer. */
(function () {
  'use strict';
  function input() { return document.getElementById('dashboard-district'); }
  function values() { return input().value.split(',').filter(Boolean); }
  function apply(names) {
    var field = input();
    if (!field) return;
    names = Array.from(new Set(names)).sort();
    field.value = names.join(',');
    document.querySelectorAll('.db-district-picker [data-district]').forEach(function (button) {
      var selected = button.dataset.district ? names.indexOf(button.dataset.district) >= 0 : !names.length;
      button.classList.toggle('selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    var list = document.getElementById('dashboard-selected-districts');
    if (!list) return;
    list.replaceChildren();
    if (!names.length) {
      var all = document.createElement('span');
      all.className = 'db-selection-all';
      all.textContent = '\uc11c\uc6b8 \uc804\uccb4';
      list.appendChild(all);
    }
    names.forEach(function (name) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'db-selected-chip';
      chip.dataset.removeDistrict = name;
      chip.setAttribute('aria-label', name + ' \uc120\ud0dd \ud574\uc81c');
      chip.textContent = name;
      var close = document.createElement('span');
      close.className = 'db-chip-remove';
      close.setAttribute('aria-hidden', 'true');
      close.textContent = '\u00d7';
      chip.appendChild(close);
      list.appendChild(chip);
    });
  }
  function toggle(name) {
    if (!input()) return;
    var known = Array.from(document.querySelectorAll('.db-district-picker [data-district]')).some(function (b) { return b.dataset.district === name; });
    if (!known) return;
    var names = values();
    apply(!name ? [] : names.indexOf(name) >= 0 ? names.filter(function (n) { return n !== name; }) : names.concat(name));
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest('.db-district-picker [data-district]');
    if (button) toggle(button.dataset.district);
    var remove = event.target.closest('[data-remove-district]');
    if (remove) {
      apply(values().filter(function (n) { return n !== remove.dataset.removeDistrict; }));
      var fallback = document.querySelector('.db-district-picker [data-district=""]');
      if (fallback) fallback.focus();
    }
    if (event.target.closest('#dashboard-reset')) {
      apply([]);
      var form = document.getElementById('dashboard-filters');
      if (form) form.requestSubmit();
    }
  });
  document.addEventListener('regionmap:select', function (event) {
    if (event.target.id === 'dashboard-region-map' && event.detail.level === 'district') toggle(event.detail.name);
  });
})();
