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
    const knot = document.querySelector('.knot');
    const conceptStory = document.querySelector('.concept-story');
    const conceptStatement = document.querySelector('.concept-statement');
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
        const knotTop = !reducedMotion.matches && knot && conceptStory && conceptStatement
            ? conceptStory.getBoundingClientRect().top + y
                + knot.getBoundingClientRect().top - conceptStatement.getBoundingClientRect().top
            : 0;
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
                // The stacked mobile layout needs an earlier start; on wide screens the
                // knot remains beside the copy, so its more deliberate timing is retained.
                const startLine = viewportHeight * (mobile.matches ? .82 : .52);
                const travel = viewportHeight * (mobile.matches ? .82 : .75);
                const progress = knot ? clamp((y - (knotTop - startLine)) / travel) : 0;
                for (const [index, path] of knotPaths.entries()) {
                    const delay = index * .055;
                    const lineProgress = clamp((progress - delay) / (1 - delay));
                    path.style.strokeDashoffset = String(1 - lineProgress);
                    path.style.visibility = lineProgress > 0 ? 'visible' : 'hidden';
                }
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
            path.style.strokeDashoffset = reducedMotion.matches ? '0' : '1';
            path.style.visibility = reducedMotion.matches ? 'visible' : 'hidden';
        }
        scheduleFrame();
    }

    // The thank-you video loads only once the concert has ended, and plays only while visible.
    // With reduced motion it stays on its poster frame.
    const thanks = document.getElementById('thanks');
    const thanksVideo = thanks?.querySelector('.thanks-video');
    let thanksObserver;
    let thanksVisible = true;
    function playThanks() {
        if (!thanksVideo || thanks.hidden) return;
        if (reducedMotion.matches || !thanksVisible) thanksVideo.pause();
        else thanksVideo.play().catch(() => {});
    }
    function showThanks(show) {
        if (!thanks || thanks.hidden === !show) return;
        thanks.hidden = !show;
        thanks.classList.toggle('is-shown', show);
        if (show && thanksVideo && !thanksVideo.getAttribute('src')) thanksVideo.src = thanksVideo.dataset.src;
        playThanks();
    }

    // JST calendar days, including a stable same-day state and midnight rollover.
    function updateCountdown() {
        const now = Date.now();
        const at = time => Date.parse(`2026-10-25T${time}:00+09:00`);
        const ended = now >= at('15:15');
        showThanks(ended);
        const ticket = document.querySelector('.hero-actions .btn--primary');
        if (ticket) ticket.parentElement.hidden = ended;
        const countdown = document.getElementById('countdown');
        if (!countdown) return;
        countdown.hidden = ended;
        if (ended) return;
        const day = ms => Math.floor((ms + 9 * 3600000) / 86400000);
        const days = day(Date.parse('2026-10-25T00:00:00+09:00')) - day(now);
        if (days === 0) {
            // The concert day follows the published door and start times.
            const [main, sub] = now < at('13:00') ? ['本日開催', '13:00 開場 ／ 13:30 開演']
                : now < at('13:30') ? ['ただいま開場中', '13:30 開演']
                : ['ただいま公演中です', '15:15 終演予定'];
            countdown.classList.add('is-today');
            countdown.closest('.hero-bottom')?.prepend(countdown);
            if (countdown.textContent !== `Today${main}${sub}`) {
                const span = (className, text) => Object.assign(document.createElement('span'), { className, textContent: text });
                countdown.replaceChildren(span('hero-countdown-label', 'Today'), span('hero-countdown-main', main), sub);
            }
            if (ticket) ticket.textContent = '当日券のご案内';
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
        reducedMotion.addEventListener('change', playThanks, { signal });
        if (thanks && 'IntersectionObserver' in window) {
            thanksObserver = new IntersectionObserver(([entry]) => { thanksVisible = entry.isIntersecting; playThanks(); });
            thanksObserver.observe(thanks);
        }
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
        thanksObserver?.disconnect();
        thanksVideo?.pause();
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
