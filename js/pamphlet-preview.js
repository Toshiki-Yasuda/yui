/* Fit the print spreads to the preview without changing the print layout. */
(() => {
  const frames = [...document.querySelectorAll('.sheet-frame')];
  const sheetWidth = 303 * 96 / 25.4;
  const sheetHeight = 216 * 96 / 25.4;
  function fit() {
    for (const frame of frames) {
      const scale = Math.min(1, frame.clientWidth / sheetWidth);
      frame.firstElementChild.style.transform = `scale(${scale})`;
      frame.style.height = `${sheetHeight * scale}px`;
    }
  }
  const observer = new ResizeObserver(fit);
  frames.forEach(frame => observer.observe(frame));
  fit();
  window.addEventListener('pagehide', () => observer.disconnect());
  window.addEventListener('pageshow', event => {
    if (event.persisted) { frames.forEach(frame => observer.observe(frame)); fit(); }
  });
})();
