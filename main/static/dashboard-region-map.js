/* Selection updates are event-driven; no mutation/render observation loops. */
(function () {
  'use strict';
  var prepared = new WeakSet();
  var loadTimer;
  function paintSelection() {
    var element = document.getElementById('dashboard-region-map');
    var chart = element && window.echarts && window.echarts.getInstanceByDom(element);
    if (!chart || !input()) return false;
    var series = (chart.getOption().series || [])[0];
    if (!series || String(series.map).indexOf('sport-insight-municipalities-') !== 0) return false;
    if (!prepared.has(chart)) {
      chart.setOption({series: [{selectedMode: 'multiple', select: {itemStyle: {areaColor: '#FFD54F', borderColor: '#967100', borderWidth: 2}, label: {color: '#172B4D'}}}]}, {silent: true});
      prepared.add(chart);
    }
    // Compare with the chart itself: ECharts also toggles selection on map clicks.
    // Reapplying every district restarts selection transitions on unchanged areas.
    var selectedMap = series.selectedMap || {};
    var names = values();
    var batch = Array.from(document.querySelectorAll('.db-district-picker [data-district]')).filter(function (b) { return b.dataset.district; });
    batch.forEach(function (button) {
      var name = button.dataset.district;
      var selected = names.indexOf(name) >= 0;
      if (Boolean(selectedMap[name]) === selected) return;
      chart.dispatchAction({type: selected ? 'mapSelect' : 'mapUnSelect', seriesIndex: 0, name: name}, {silent: true});
    });
    return true;
  }
  function initializeMap() {
    clearTimeout(loadTimer);
    var element = document.getElementById('dashboard-region-map');
    var attempts = 0;
    function ready() {
      if (element !== document.getElementById('dashboard-region-map') || !element) return;
      if (!paintSelection() && ++attempts < 80) loadTimer = setTimeout(ready, 250);
    }
    ready();
  }
  document.addEventListener('DOMContentLoaded', initializeMap);
  document.addEventListener('htmx:afterSwap', initializeMap);
  function input() { return document.getElementById('dashboard-district'); }
  function values() { return input().value.split(',').filter(Boolean); }
  function apply(names) {
    var field = input();
    if (!field) return;
    names = Array.from(new Set(names)).sort();
    field.value = names.join(',');
    paintSelection();
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
      all.textContent = '행정구역을 선택해주세요';
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
    if (event.target.id === 'dashboard-region-map' && event.detail.level === 'district') {
      toggle(event.detail.name);
      // Reconcile after ECharts completes its own click selection handling.
      setTimeout(paintSelection, 0);
    }
  });
})();
