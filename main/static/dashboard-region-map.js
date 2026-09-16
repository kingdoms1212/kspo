/* 대시보드 전용 지도 연결 모듈.
 * 지도 선택과 지역 필터 변경을 반영한 후 HTMX 조회를 실행한다.
 * HTMX가 폼을 교체하므로 각 동작에서 현재 DOM을 다시 조회한다.
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
    // change 이벤트를 함께 발생시키면 조회가 중복되므로 여기서 한 번만 제출한다.
    form.requestSubmit();
  }

  document.addEventListener('regionmap:select', event => {
    if (event.target.id !== 'dashboard-region-map') return;
    const { level, region, name, shortName } = event.detail;
    if (level === 'region') selectArea(region || name || shortName);
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
