/* 대시보드 전용 지도 연결 모듈.
 *
 * 공통 지도에서 발생한 `regionmap:select` 이벤트를 받아 대시보드 지역
 * 필터를 변경하고 htmx 조회를 실행한다. 지도 렌더링이나 프로그램 검색
 * 동작은 담당하지 않는다. 대시보드의 지도 클릭 동작만 수정할 때 이
 * 파일을 변경한다.
 */
(function () {
  'use strict';

  // 전국 지도에서 시도를 선택하면 상단 지역 선택창과 동일한 조회를 실행한다.
  document.addEventListener('regionmap:select', function (event) {
    if (event.detail.level !== 'region') return;

    var select = document.getElementById('dashboard-region');
    var map = window.SportInsightRegionMap;
    var match = select && map && Array.from(select.options).find(function (option) {
      return map.shortName(option.value) === event.detail.shortName;
    });
    if (!match) return;

    select.value = match.value;
    select.dispatchEvent(new Event('change'));
  });
})();
