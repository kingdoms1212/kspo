/* Shared choropleth of Korea, used by more than one screen.
 *
 * A screen declares a map with `components/region_map.html`; this file finds
 * every declared container and draws it. Nothing here knows which screen it is
 * on: values, labels and click behaviour arrive as data attributes, and a click
 * leaves as a `regionmap:select` event for the page to act on.
 *
 * Containers are re-scanned after an htmx swap, so a map inside a swapped
 * region is redrawn with the new numbers. Drawing disposes any chart already
 * bound to the element, which keeps a redraw from stacking instances.
 */
(function () {
  'use strict';

  var ECHARTS_CDN = 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js';
  var COUNTRY_GEOJSON = 'https://cdn.jsdelivr.net/gh/southkorea/southkorea-maps@master/kostat/2013/json/skorea_provinces_geo_simple.json';
  var SEOUL_GEOJSON = 'https://cdn.jsdelivr.net/gh/southkorea/seoul-maps@master/juso/2015/json/seoul_municipalities_geo_simple.json';
  var COUNTRY_MAP = 'sport-insight-provinces';
  var SEOUL_MAP = 'sport-insight-seoul-districts';

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

  var geoJsonCache = {};
  var librariesReady = null;

  function shortName(name) {
    return REGION_ALIASES[name] || name;
  }

  function isSeoul(name) {
    return shortName(name) === '서울';
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

  function readPairs(id) {
    var node = id && document.getElementById(id);
    if (!node) return [];
    try {
      var parsed = JSON.parse(node.textContent);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
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
    var regionData = readPairs(config.regionSource).map(function (pair) {
      return { name: shortName(pair[0]), value: pair[1] };
    });
    var districtData = readPairs(config.districtSource).map(function (pair) {
      return { name: pair[0], value: pair[1] };
    });
    var level = document.getElementById(config.levelTarget);
    var help = document.getElementById(config.helpTarget);
    var back = document.getElementById(config.backTarget);
    var valueLabel = config.valueLabel || '건수';
    var unit = config.unit || '';
    var countryHelp = config.countryHelp || '';
    var districtHelp = config.districtHelp || '';
    var chart;
    var countryGeoJson;

    function fail(error) {
      console.error('Region map failed:', error);
      element.innerHTML = '<p class="region-map-status">지도 데이터를 불러오지 못했습니다. 아래 목록을 확인해 주세요.</p>';
    }

    function emit(mapLevel, name) {
      element.dispatchEvent(new CustomEvent('regionmap:select', {
        bubbles: true,
        detail: { level: mapLevel, name: name, shortName: shortName(name) }
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
          if (isSeoul(params.name) && districtData.length) showSeoul().catch(fail);
          return;
        }
        emit('region', params.name);
      });
      element.setAttribute('aria-label', config.countryDescription || '시도별 분포 지도');
      if (level) level.textContent = config.countryLevel || '전국 시·도';
      if (help) help.textContent = countryHelp;
      if (back) back.hidden = true;
    }

    function showSeoul() {
      return loadGeoJson(SEOUL_GEOJSON).then(function (geoJson) {
        geoJson.features.forEach(function (feature) {
          feature.properties.name = feature.properties.SIG_KOR_NM || feature.properties.name;
        });
        window.echarts.registerMap(SEOUL_MAP, geoJson);

        chart.off('click');
        chart.setOption(mapOption({
          mapName: SEOUL_MAP,
          data: districtData,
          description: config.districtDescription || '서울특별시 자치구별 분포 지도입니다.',
          valueLabel: valueLabel,
          unit: unit,
          labels: true
        }), true);
        chart.on('click', function (params) {
          if (params.componentType === 'series') emit('district', params.name);
        });
        element.setAttribute('aria-label', config.districtDescription || '서울특별시 자치구별 분포 지도');
        if (level) level.textContent = config.districtLevel || '서울 25개 자치구';
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

      var onlySeoulHasValues = regionData.length > 0 &&
        regionData.filter(function (item) { return Number(item.value) > 0; })
          .every(function (item) { return isSeoul(item.name); });
      var startOnSeoul = districtData.length > 0 &&
        (isSeoul(config.focusRegion || '') || onlySeoulHasValues);

      var ready = startOnSeoul ? showSeoul() : Promise.resolve(showCountry());
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

  window.SportInsightRegionMap = { draw: draw, drawAll: drawAll, shortName: shortName, isSeoul: isSeoul };
})();
