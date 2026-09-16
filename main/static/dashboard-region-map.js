/* Delegation survives HTMX replacement of the dashboard. */
(function () {
  'use strict';
  function submit() {
    var form = document.getElementById('dashboard-filters');
    if (form) form.requestSubmit();
  }
  document.addEventListener('change', function (event) {
    if (event.target.id === 'dashboard-region') {
      var district = document.getElementById('dashboard-district');
      district.value = '';
      district.disabled = !event.target.value;
      submit();
    } else if (event.target.id === 'dashboard-district') submit();
  });
  document.addEventListener('regionmap:select', function (event) {
    if (event.target.id !== 'dashboard-region-map') return;
    var select = document.getElementById(event.detail.level === 'region' ? 'dashboard-region' : 'dashboard-district');
    var map = window.SportInsightRegionMap;
    var match = select && map && Array.from(select.options).find(function (option) {
      return event.detail.level === 'region'
        ? map.shortName(option.value) === event.detail.shortName
        : option.value === event.detail.name;
    });
    if (!match) return;
    select.value = match.value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
})();
