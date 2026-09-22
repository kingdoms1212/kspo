/* Overview UI stays independent of CSV readiness and other page controls. */
(() => {
  const root = document.getElementById('overview-document');
  if (!root) return;
  const details = [...root.querySelectorAll('details')];
  const toggle = root.querySelector('#toggle-details');
  function updateLabel() {
    const expanded = details.every(detail => detail.open);
    toggle.textContent = expanded ? '상세 모두 접기' : '상세 모두 펼치기';
    toggle.setAttribute('aria-expanded', String(expanded));
  }
  toggle.addEventListener('click', () => {
    const open = details.some(detail => !detail.open);
    details.forEach(detail => { detail.open = open; });
    updateLabel();
  });
  details.forEach(detail => detail.addEventListener('toggle', updateLabel));
  updateLabel();
  const links = [...root.querySelectorAll('.rail a')];
  const sections = links.map(link => document.getElementById(link.hash.slice(1)));
  let frame = null;
  function updateActiveSection() {
    frame = null;
    const page = document.scrollingElement || document.documentElement;
    const atBottom = page.scrollHeight > page.clientHeight
      && page.scrollHeight - page.clientHeight - page.scrollTop <= 2;
    let active = sections[0];
    // Short final sections may never reach the heading threshold before the
    // document ends. The bottom edge must therefore select the last section.
    if (atBottom) active = sections[sections.length - 1];
    else sections.forEach(section => {
      if (!section) return;
      const offset = parseFloat(getComputedStyle(section).scrollMarginTop) || 0;
      if (section.getBoundingClientRect().top <= offset + 2) active = section;
    });
    links.forEach(link => {
      if (active && link.hash === '#' + active.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function scheduleActiveSection() {
    if (frame === null) frame = requestAnimationFrame(updateActiveSection);
  }
  window.addEventListener('scroll', scheduleActiveSection, {passive: true});
  window.addEventListener('resize', scheduleActiveSection);
  window.addEventListener('pageshow', scheduleActiveSection);
  details.forEach(detail => detail.addEventListener('toggle', scheduleActiveSection));
  if ('ResizeObserver' in window) new ResizeObserver(scheduleActiveSection).observe(root);
  scheduleActiveSection();
})();
