/* Small, dependency-free enhancements. Content is never hidden for animation. */
(() => {
    'use strict';
    const root = document.documentElement;
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    const mobile = matchMedia('(max-width: 900px)');
    const nav = document.querySelector('.nav');
    const toggle = document.querySelector('.nav-toggle');
    const menu = document.querySelector('.nav-menu');
    const topButton = document.querySelector('.scroll-top');
    let controller;
    let observer;
    let sectionObserver;
    let resizeObserver;
    let frame = 0;
    const visibleScenes = new Set();
    const scenes = [...document.querySelectorAll('.hero, .concept, .marimba-intro')];
    const knotPaths = [...document.querySelectorAll('.knot-ink path')];
    const portrait = document.querySelector('.hero-figure');
    const heroTitle = document.querySelector('.hero-title');
    const instrument = document.querySelector('.marimba-media');
    let opener = null;
    let countdownTimer;
    const clamp = value => Math.min(1, Math.max(0, value));

    function setNavOpen(open, restore = false) {
        if (!toggle || !menu) return;
        menu.classList.toggle('active', open);
        toggle.classList.toggle('active', open);
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
        if (restore) toggle.focus();
    }

    function updateFrame() {
        frame = 0;
        // Batch layout reads before any writes; no perpetual animation loop.
        const viewportHeight = window.innerHeight;
        const y = window.scrollY;
        const maxScroll = document.documentElement.scrollHeight - viewportHeight;
        const metrics = reducedMotion.matches ? [] : [...visibleScenes].map(element => ({
            element, bounds: element.getBoundingClientRect()
        }));
        if (topButton) topButton.classList.toggle('visible', y > viewportHeight);
        if (nav) nav.style.setProperty('--reading-progress', String(maxScroll > 0 ? clamp(y / maxScroll) : 0));
        if (y < 100) menu?.querySelectorAll('[aria-current]').forEach(link => link.removeAttribute('aria-current'));
        for (const { element, bounds } of metrics) {
            if (element.classList.contains('hero') && window.innerWidth > 600) {
                const amount = clamp(-bounds.top / bounds.height);
                if (portrait) portrait.style.transform = `translateY(${amount * 32}px)`;
                if (heroTitle) heroTitle.style.transform = `translateY(${-amount * 20}px)`;
            } else if (element.classList.contains('concept')) {
                const progress = clamp((viewportHeight * .7 - bounds.top) / (bounds.height * .85));
                for (const path of knotPaths) path.style.strokeDashoffset = String(1 - progress);
            } else if (instrument && window.innerWidth > 600) {
                const progress = clamp((viewportHeight - bounds.top) / (viewportHeight + bounds.height));
                instrument.style.transform = `translateY(${(1 - progress) * 24 - 12}px)`;
            }
        }
    }
    function scheduleFrame() {
        if (!frame) frame = requestAnimationFrame(updateFrame);
    }
    function resetMotion() {
        for (const item of [portrait, heroTitle, instrument]) item?.style.removeProperty('transform');
        for (const path of knotPaths) {
            path.style.strokeDasharray = reducedMotion.matches ? 'none' : '1';
            path.style.strokeDashoffset = '0';
        }
        scheduleFrame();
    }

    // JST calendar days, including a stable same-day state and midnight rollover.
    function updateCountdown() {
        const countdown = document.getElementById('countdown');
        if (!countdown) return;
        const day = ms => Math.floor((ms + 9 * 3600000) / 86400000);
        const days = day(Date.parse('2026-10-25T00:00:00+09:00')) - day(Date.now());
        countdown.hidden = days < 0;
        if (days < 0) return;
        if (days === 0) {
            if (countdown.textContent !== '本日開催！') countdown.textContent = '本日開催！';
        } else {
            const number = document.getElementById('countdown-days');
            if (number) number.textContent = String(days);
        }
    }

    function initialize() {
        controller = new AbortController();
        const { signal } = controller;
        root.classList.replace('no-js', 'js');
        toggle?.addEventListener('click', () => setNavOpen(toggle.getAttribute('aria-expanded') !== 'true'), { signal });
        menu?.addEventListener('click', event => {
            if (event.target.closest('a')) setNavOpen(false);
        }, { signal });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && toggle?.getAttribute('aria-expanded') === 'true') setNavOpen(false, true);
        }, { signal });
        document.addEventListener('pointerdown', event => {
            if (nav && !nav.contains(event.target)) setNavOpen(false);
        }, { signal });
        nav?.addEventListener('focusout', event => {
            if (!nav.contains(event.relatedTarget)) setNavOpen(false);
        }, { signal });
        mobile.addEventListener('change', () => setNavOpen(false), { signal });
        topButton?.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: reducedMotion.matches ? 'instant' : 'smooth' });
            const main = document.querySelector('main');
            main?.setAttribute('tabindex', '-1');
            main?.focus({ preventScroll: true });
        }, { signal });
        if ('IntersectionObserver' in window) {
            observer = new IntersectionObserver(entries => {
                for (const entry of entries) {
                    if (entry.isIntersecting) visibleScenes.add(entry.target);
                    else visibleScenes.delete(entry.target);
                }
                scheduleFrame();
            }, { rootMargin: '40px' });
            scenes.forEach(scene => observer.observe(scene));
            sectionObserver = new IntersectionObserver(entries => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) continue;
                    const link = menu?.querySelector(`a[href="#${entry.target.id}"]`);
                    if (!link) continue;
                    menu.querySelectorAll('[aria-current]').forEach(item => item.removeAttribute('aria-current'));
                    link.setAttribute('aria-current', 'location');
                }
            }, { rootMargin: '-15% 0px -65% 0px' });
            document.querySelectorAll('main > section[id]').forEach(section => sectionObserver.observe(section));
        }
        if ('ResizeObserver' in window) {
            resizeObserver = new ResizeObserver(scheduleFrame);
            resizeObserver.observe(document.body);
        }
        window.addEventListener('scroll', scheduleFrame, { passive: true, signal });
        window.addEventListener('resize', resetMotion, { passive: true, signal });
        reducedMotion.addEventListener('change', resetMotion, { signal });
        resetMotion();
        updateCountdown();
        countdownTimer = setInterval(updateCountdown, 60000);
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) { updateCountdown(); scheduleFrame(); }
        }, { signal });

        // The original privacy-conscious video facade: YouTube loads only on a click.
        document.querySelectorAll('.video[data-video-id]').forEach(wrap => {
            const poster = wrap.querySelector('.video-poster');
            poster?.addEventListener('click', event => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                const iframe = document.createElement('iframe');
                iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(wrap.dataset.videoId) + '?autoplay=1&rel=0&playsinline=1';
                iframe.title = wrap.dataset.videoTitle || 'YouTube動画';
                iframe.allow = 'autoplay; encrypted-media; picture-in-picture; web-share';
                iframe.referrerPolicy = 'strict-origin-when-cross-origin';
                iframe.allowFullscreen = true;
                wrap.classList.add('is-playing');
                wrap.replaceChildren(iframe);
                iframe.focus();
            }, { signal });
        });

        const dialog = document.querySelector('.lightbox');
        if (dialog && typeof dialog.showModal === 'function') {
            const image = dialog.querySelector('.lightbox-img');
            const close = dialog.querySelector('.lightbox-close');
            document.querySelectorAll('[data-lightbox]').forEach(link => {
                link.addEventListener('click', event => {
                    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                    event.preventDefault();
                    opener = link;
                    image.src = link.href;
                    image.alt = link.dataset.caption || '';
                    image.hidden = false;
                    dialog.showModal();
                    close.focus();
                }, { signal });
            });
            close.addEventListener('click', () => dialog.close(), { signal });
            dialog.addEventListener('click', event => {
                if (event.target === dialog) dialog.close();
            }, { signal });
            image.addEventListener('error', () => {
                // The original image URL is also the no-JS fallback.
                dialog.close();
                if (opener) window.location.assign(opener.href);
            }, { signal });
            dialog.addEventListener('close', () => {
                image.hidden = true;
                image.removeAttribute('src');
                image.alt = '';
                opener?.focus({ preventScroll: true });
            }, { signal });
        }
    }
    function cleanup() {
        controller?.abort();
        observer?.disconnect();
        sectionObserver?.disconnect();
        resizeObserver?.disconnect();
        visibleScenes.clear();
        cancelAnimationFrame(frame);
        frame = 0;
        clearInterval(countdownTimer);
        setNavOpen(false);
    }
    initialize();
    window.addEventListener('pagehide', cleanup);
    window.addEventListener('pageshow', event => { if (event.persisted) initialize(); });
})();
