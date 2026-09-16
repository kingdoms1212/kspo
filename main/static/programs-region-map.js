/* 프로그램 분석 전용 지도 연결 모듈.
 *
 * 시군구 지도에서 선택한 지역을 프로그램 검색 조건의 지역·시군구에
 * 반영한 후 검색 폼을 제출한다. 지도 렌더링이나 대시보드 조회 동작은
 * 담당하지 않는다. 프로그램 화면의 지도 검색 연동만 수정할 때 이
 * 파일을 변경한다.
 */
(function () {
  'use strict';

  // 시군구 선택 결과를 프로그램 검색 조건에 반영하고 전체 조회를 다시 실행한다.
  document.addEventListener('regionmap:select', function (event) {
    if (event.detail.level !== 'district') return;

    var form = document.getElementById('program-search-form');
    var regionSelect = document.getElementById('region');
    var districtSelect = document.getElementById('district');
    var map = window.SportInsightRegionMap;
    if (!form || !regionSelect || !districtSelect || !map) return;

    var region = Array.from(regionSelect.options).find(function (option) {
      return map.shortName(option.value) === map.shortName(event.detail.region);
    });
    if (!region) return;

    regionSelect.value = region.value;
    // 지역에 맞는 시군구 선택 항목을 먼저 구성한다.
    regionSelect.dispatchEvent(new Event('change'));
    if (!Array.from(districtSelect.options).some(function (option) {
      return option.value === event.detail.name;
    })) return;

    districtSelect.value = event.detail.name;
    form.requestSubmit();
  });
})();
