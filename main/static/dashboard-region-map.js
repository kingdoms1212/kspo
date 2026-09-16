/* Dashboard adapter for the same region/district event contract as programs.
 * Look up the form on every interaction because HTMX replaces the fragment.
 */
(() => {
  'use strict';

  function updateDistrictOptions(regionName, selected = '') {
    const district = document.getElementById('dashboard-district');
    const data = document.getElementById('dashboard-district-options');
    if (!district || !data) return;
    const groups = JSON.parse(data.textContent);
    const names = groups[regionName] || [];
    district.replaceChildren(new Option('전체', ''));
    names.forEach(name => district.add(new Option(name, name, false, name === selected)));
    district.disabled = !regionName;
  }

  function selectArea(regionName, districtName = '') {
    const form = document.getElementById('dashboard-filters');
    const region = document.getElementById('dashboard-region');
    const district = document.getElementById('dashboard-district');
    const map = window.SportInsightRegionMap;
    if (!form || !region || !district || !map) return;
    const option = Array.from(region.options).find(item =>
      map.shortName(item.value) === map.shortName(regionName));
    if (!option) return;
    region.value = option.value;
    updateDistrictOptions(option.value, districtName);
    district.value = districtName;
    form.requestSubmit();
  }

  document.addEventListener('regionmap:select', event => {
    if (event.target.id !== 'dashboard-region-map') return;
    const { level, region, name } = event.detail;
    if (level === 'region') selectArea(region || name);
    if (level === 'district') selectArea(region, name);
  });

  document.addEventListener('click', event => {
    if (event.target.closest('#dashboard-region-map-back')) selectArea('');
  });

  document.addEventListener('change', event => {
    if (event.target.id === 'dashboard-region') {
      updateDistrictOptions(event.target.value);
      event.target.form.requestSubmit();
    } else if (event.target.id === 'dashboard-district') {
      event.target.form.requestSubmit();
    }
  });
})();
