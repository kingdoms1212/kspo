/* 전국 시도 및 시군구 지도를 그리는 공통 렌더링 모듈.
 *
 * 담당 범위:
 * - ECharts와 GeoJSON 로딩
 * - 전국 시도 및 선택 지역의 시군구 지도 렌더링
 * - 지도 색상, 툴팁, 확대·축소, 전국 보기 처리
 * - 선택 결과를 `regionmap:select` 이벤트로 전달
 *
 * 담당하지 않는 범위:
 * - 대시보드 조회 조건 변경
 * - 프로그램 검색 폼 제출
 *
 * 화면별 후속 동작은 dashboard-region-map.js와 programs-region-map.js가
 * 각각 담당한다. 이 파일을 변경하면 두 화면에 모두 영향을 줄 수 있다.
 * htmx 교체 이후에는 컨테이너를 다시 탐색하고 기존 차트를 폐기한 뒤
 * 새 데이터로 그려 차트 인스턴스가 중복되지 않게 한다.
 */
(function () {
  'use strict';

  var ECHARTS_CDN = 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js';
  var COUNTRY_GEOJSON = 'https://cdn.jsdelivr.net/gh/southkorea/southkorea-maps@master/kostat/2013/json/skorea_provinces_geo_simple.json';
  var MUNICIPALITY_GEOJSON = 'https://cdn.jsdelivr.net/gh/southkorea/southkorea-maps@master/kostat/2013/json/skorea_municipalities_geo_simple.json';
  var COUNTRY_MAP = 'sport-insight-provinces';
  var MUNICIPALITY_MAP_PREFIX = 'sport-insight-municipalities-';

  /* Registers write a province either in full or in short form. The map's own
   * names are the short ones, so both spellings resolve to the same area. */
  var REGION_ALIASES = {
    '서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구',
    '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전',
    '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기',
    '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북',
    '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북',
    '전라남도': '전남', '경상북도': '경북', '경상남도': '경남',
    '제주특별자치도': '제주'
  };

  /* The municipality file uses the first two digits of its KOSTAT code to
   * identify the containing province. */
  var REGION_CODES = {
    '서울': '11', '부산': '21', '대구': '22', '인천': '23', '광주': '24',
    '대전': '25', '울산': '26', '세종': '29', '경기': '31', '강원': '32',
    '충북': '33', '충남': '34', '전북': '35', '전남': '36', '경북': '37',
    '경남': '38', '제주': '39'
  };

  var REGION_FULL_NAMES = {
    '서울': '서울특별시', '부산': '부산광역시', '대구': '대구광역시',
    '인천': '인천광역시', '광주': '광주광역시', '대전': '대전광역시',
    '울산': '울산광역시', '세종': '세종특별자치시', '경기': '경기도',
    '강원': '강원특별자치도', '충북': '충청북도', '충남': '충청남도',
    '전북': '전북특별자치도', '전남': '전라남도', '경북': '경상북도',
    '경남': '경상남도', '제주': '제주특별자치도'
  };

  var geoJsonCache = {};
  var librariesReady = null;

  function shortName(name) {
    return REGION_ALIASES[name] || name;
  }

  function isSeoul(name) {
    return shortName(name) === '서울';
  }

  function fullRegionName(name) {
    var compact = shortName(name);
    return REGION_FULL_NAMES[compact] || name;
  }

  function compactName(name) {
    return String(name || '').replace(/\s+/g, '');
  }

  function displayMunicipalityName(name) {
    return String(name || '').replace(/^(.+시)([^시]+구)$/, '$1 $2');
  }

  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      var tag = document.createElement('script');
      tag.src = url;
      tag.onload = resolve;
      tag.onerror = function () { reject(new Error('ECharts를 불러오지 못했습니다.')); };
      document.head.appendChild(tag);
    });
  }

  function loadECharts() {
    if (window.echarts) {
      return Promise.resolve();
    }
    if (!librariesReady) {
      librariesReady = loadScript(ECHARTS_CDN);
    }
    return librariesReady;
  }

  function loadGeoJson(url) {
    if (!geoJsonCache[url]) {
      geoJsonCache[url] = fetch(url).then(function (response) {
        if (!response.ok) throw new Error('지도 데이터를 불러오지 못했습니다.');
        return response.json();
      });
    }
    return geoJsonCache[url];
  }

  function readJson(id, fallback) {
    var node = id && document.getElementById(id);
    if (!node) return fallback;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return fallback;
    }
  }

  function municipalityGeoJsonForRegion(geoJson, regionName, districtData) {
    var regionCode = REGION_CODES[shortName(regionName)];
    if (!regionCode) return null;

    var sourceNames = {};
    districtData.forEach(function (pair) {
      sourceNames[compactName(pair[0])] = pair[0];
    });
    return {
      type: 'FeatureCollection',
      features: geoJson.features.filter(function (feature) {
        return String(feature.properties.code || '').startsWith(regionCode);
      }).map(function (feature) {
        var sourceName = feature.properties.name || '';
        return Object.assign({}, feature, {
          properties: Object.assign({}, feature.properties, {
            name: sourceNames[compactName(sourceName)] || displayMunicipalityName(sourceName)
          })
        });
      })
    };
  }

  /* A single highlighted area is easier to read zoomed in, so the one active
   * province decides the centre and scale. */
  function featureFocus(feature) {
    var bounds = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
    (function visit(coordinates) {
      if (typeof coordinates[0] === 'number') {
        bounds.minX = Math.min(bounds.minX, coordinates[0]);
        bounds.maxX = Math.max(bounds.maxX, coordinates[0]);
        bounds.minY = Math.min(bounds.minY, coordinates[1]);
        bounds.maxY = Math.max(bounds.maxY, coordinates[1]);
        return;
      }
      coordinates.forEach(visit);
    })(feature.geometry.coordinates);
    var span = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY);
    return {
      center: [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2],
      zoom: Math.min(6, Math.max(2, 4.5 / span))
    };
  }

  function mapOption(settings) {
    var style = getComputedStyle(document.documentElement);
    var token = function (name) { return style.getPropertyValue(name).trim(); };
    var fontFamily = getComputedStyle(document.body).fontFamily;
    var maximum = Math.max(1, ...settings.data.map(function (item) {
      return Number(item.value) || 0;
    }));
    return {
      backgroundColor: token('--si-bg'),
      textStyle: { fontFamily: fontFamily },
      aria: { enabled: true, description: settings.description },
      tooltip: {
        trigger: 'item',
        backgroundColor: token('--si-surface'),
        borderColor: token('--si-border'),
        textStyle: { fontFamily: fontFamily, color: token('--si-text') },
        formatter: function (params) {
          var value = Number.isFinite(params.value) ? params.value : 0;
          return params.name + '<br>' + settings.valueLabel + ' ' +
            value.toLocaleString('ko-KR') + settings.unit;
        }
      },
      visualMap: {
        min: 0,
        max: maximum,
        left: 'center',
        bottom: 4,
        orient: 'horizontal',
        calculable: false,
        text: ['많음', '적음'],
        inRange: { color: ['--si-map-1', '--si-map-2', '--si-map-3', '--si-map-4', '--si-map-5'].map(token) },
        textStyle: { color: token('--si-text-muted'), fontFamily: fontFamily, fontSize: 10 }
      },
      series: [{
        name: settings.valueLabel,
        type: 'map',
        map: settings.mapName,
        roam: true,
        center: settings.center,
        zoom: settings.zoom || 1,
        scaleLimit: { min: 1, max: 8 },
        layoutCenter: ['50%', '43%'],
        layoutSize: '85%',
        selectedMode: false,
        label: { show: Boolean(settings.labels), color: token('--si-text'), fontFamily: fontFamily, fontSize: 9 },
        itemStyle: { areaColor: token('--si-map-no-data'), borderColor: token('--si-surface'), borderWidth: 1 },
        emphasis: { label: { show: true, color: token('--si-heading') }, itemStyle: { areaColor: token('--si-map-3') } },
        data: settings.data
      }]
    };
  }

  function draw(element) {
    var config = element.dataset;
    var regionPairs = readJson(config.regionSource, []);
    var districtGroups = readJson(config.districtSource, {});
    var regionData = (Array.isArray(regionPairs) ? regionPairs : []).map(function (pair) {
      return { name: shortName(pair[0]), value: pair[1] };
    });
    if (!districtGroups || Array.isArray(districtGroups) || typeof districtGroups !== 'object') {
      districtGroups = {};
    }
    var level = document.getElementById(config.levelTarget);
    var help = document.getElementById(config.helpTarget);
    var back = document.getElementById(config.backTarget);
    var valueLabel = config.valueLabel || '건수';
    var unit = config.unit || '';
    var countryHelp = config.countryHelp || '';
    var districtHelp = config.districtHelp || '';
    var chart;
    var countryGeoJson;

    function districtDataForRegion(regionName) {
      var key = Object.keys(districtGroups).find(function (candidate) {
        return shortName(candidate) === shortName(regionName);
      });
      return key ? districtGroups[key] : [];
    }

    function sourceRegionName(regionName) {
      return Object.keys(districtGroups).find(function (candidate) {
        return shortName(candidate) === shortName(regionName);
      }) || regionName;
    }

    function fail(error) {
      console.error('Region map failed:', error);
      element.innerHTML = '<p class="region-map-status">지도 데이터를 불러오지 못했습니다. 아래 목록을 확인해 주세요.</p>';
    }

    /* 공통 지도 선택 이벤트 계약.
     * level은 전국 지도의 시도 선택이면 region, 하위 지도의 시군구
     * 선택이면 district이다. region과 name을 화면별 전용 모듈에 넘기며,
     * 후속 조회 또는 폼 제출은 여기서 결정하지 않는다. */
    function emit(mapLevel, name, regionName) {
      element.dispatchEvent(new CustomEvent('regionmap:select', {
        bubbles: true,
        detail: {
          level: mapLevel,
          name: name,
          region: regionName || name,
          shortName: shortName(name)
        }
      }));
    }

    function showCountry() {
      var active = regionData.filter(function (item) { return Number(item.value) > 0; });
      var feature = active.length === 1 && countryGeoJson
        ? countryGeoJson.features.find(function (item) { return item.properties.name === active[0].name; })
        : null;
      var focus = feature ? featureFocus(feature) : {};

      chart.off('click');
      chart.setOption(mapOption({
        mapName: COUNTRY_MAP,
        data: regionData,
        description: config.countryDescription || '시도별 분포 지도입니다.',
        valueLabel: valueLabel,
        unit: unit,
        center: focus.center,
        zoom: focus.zoom || 1
      }), true);
      chart.on('click', function (params) {
        if (params.componentType !== 'series') return;
        if (config.regionClick === 'drilldown') {
          if (districtDataForRegion(params.name).length) showDistrict(params.name).catch(fail);
          return;
        }
        emit('region', params.name);
      });
      element.setAttribute('aria-label', config.countryDescription || '시도별 분포 지도');
      if (level) level.textContent = config.countryLevel || '전국 시·도';
      if (help) help.textContent = countryHelp;
      if (back) back.hidden = true;
    }

    /* 선택한 시도 코드에 속하는 시군구 경계만 추출해 표시한다.
     * 수치의 집계 기준은 각 화면의 서버 서비스가 결정하며, 공통 엔진은
     * 전달받은 값을 지도 경계와 연결하는 역할만 담당한다. */
    function showDistrict(regionName) {
      var districtPairs = districtDataForRegion(regionName);
      var selectedRegion = sourceRegionName(regionName);
      var displayRegion = fullRegionName(regionName);
      var mapName = MUNICIPALITY_MAP_PREFIX + (REGION_CODES[shortName(regionName)] || shortName(regionName));
      return loadGeoJson(MUNICIPALITY_GEOJSON).then(function (geoJson) {
        var regionalGeoJson = municipalityGeoJsonForRegion(geoJson, regionName, districtPairs);
        if (!regionalGeoJson || !regionalGeoJson.features.length) {
          throw new Error(displayRegion + '의 시군구 경계를 찾지 못했습니다.');
        }
        window.echarts.registerMap(mapName, regionalGeoJson);

        chart.off('click');
        chart.setOption(mapOption({
          mapName: mapName,
          data: districtPairs.map(function (pair) {
            return { name: pair[0], value: pair[1] };
          }),
          description: displayRegion + ' 시군구별 분포 지도입니다.',
          valueLabel: valueLabel,
          unit: unit,
          // Dense province maps remain readable through hover tooltips; compact
          // metropolitan maps keep the always-visible labels used by Seoul.
          labels: regionalGeoJson.features.length <= 25
        }), true);
        chart.on('click', function (params) {
          if (params.componentType === 'series') emit('district', params.name, selectedRegion);
        });
        element.setAttribute('aria-label', displayRegion + ' 시군구별 분포 지도');
        if (level) level.textContent = displayRegion + ' 시군구';
        if (help) help.textContent = districtHelp;
        if (back) back.hidden = false;
      });
    }

    return loadECharts().then(function () {
      // Canvas labels must be drawn after the local font has loaded.
      return Promise.all([
        loadGeoJson(COUNTRY_GEOJSON),
        document.fonts ? document.fonts.load('400 12px "Noto Sans KR"').catch(function () {
          // A font failure must not prevent the map from rendering in the fallback font.
        }) : Promise.resolve()
      ]).then(function (results) { return results[0]; });
    }).then(function (geoJson) {
      countryGeoJson = geoJson;
      countryGeoJson.features.forEach(function (feature) {
        feature.properties.name = shortName(feature.properties.name);
      });
      window.echarts.registerMap(COUNTRY_MAP, countryGeoJson);
      // A redraw after a swap must not leave the previous instance attached.
      window.echarts.dispose(element);
      chart = window.echarts.init(element);
      element.__regionMapChart = chart;

      var activeRegions = regionData.filter(function (item) { return Number(item.value) > 0; });
      var startRegion = config.focusRegion || (activeRegions.length === 1 ? activeRegions[0].name : '');
      var startOnDistrict = startRegion && districtDataForRegion(startRegion).length > 0;

      var ready = startOnDistrict ? showDistrict(startRegion) : Promise.resolve(showCountry());
      if (back) back.addEventListener('click', showCountry);
      new ResizeObserver(function () { chart.resize(); }).observe(element);
      return ready;
    }).catch(fail);
  }

  function drawAll(root) {
    (root || document).querySelectorAll('[data-region-map]').forEach(function (element) {
      draw(element);
    });
  }

  document.addEventListener('DOMContentLoaded', function () { drawAll(document); });
  // A map inside a swapped region is redrawn with the values that just arrived.
  document.body.addEventListener('htmx:afterSettle', function (event) {
    drawAll(event.detail.elt === document.body ? document : event.target);
  });

  window.SportInsightRegionMap = {
    draw: draw,
    drawAll: drawAll,
    shortName: shortName,
    isSeoul: isSeoul
  };
})();
