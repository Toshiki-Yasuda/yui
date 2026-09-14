/* Optional 3D island. No model, decoder or viewer download until the visitor asks. */
const section = document.querySelector('.marimba-model');
if (section) {
    const stage = section.querySelector('.model-stage');
    const mount = section.querySelector('.model-mount');
    const start = section.querySelector('.model-start');
    const toolbar = section.querySelector('.model-toolbar');
    const status = section.querySelector('.model-status');
    const help = section.querySelector('.model-help');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    const initialOrbit = '-25deg 65deg 105%';
    let viewer = null;
    let timeout = 0;
    let attempt = 0;
    let state = 'idle';
    let events = new AbortController();

    start.hidden = false;
    status.textContent = 'ボタンを押すと3Dモデルを読み込みます。';

    function fail(message) {
        state = 'error';
        clearTimeout(timeout);
        attempt++;
        events.abort();
        viewer?.remove();
        viewer = null;
        stage.classList.remove('is-ready');
        stage.setAttribute('aria-busy', 'false');
        toolbar.hidden = true;
        help.hidden = true;
        start.hidden = false;
        start.removeAttribute('aria-disabled');
        start.textContent = 'ページを再読み込み';
        status.textContent = `${message} 確認画像をご覧いただけます。`;
    }

    async function load() {
        if (state === 'loading' || state === 'ready') return;
        if (state === 'error') { location.reload(); return; }
        state = 'loading';
        const current = ++attempt;
        start.setAttribute('aria-disabled', 'true');
        start.textContent = '読み込み中…';
        stage.setAttribute('aria-busy', 'true');
        status.textContent = '3Dモデルを読み込んでいます。';
        timeout = setTimeout(() => fail('読み込みに時間がかかっています。通信状態を確認して再度お試しください。'), 60000);
        try {
            await import('./vendor/model-viewer/model-viewer-4.3.1.min.js');
            if (current !== attempt) return;
            const ModelViewer = customElements.get('model-viewer');
            ModelViewer.dracoDecoderLocation = new URL('./vendor/model-viewer/draco/', import.meta.url).href;
            ModelViewer.minimumRenderScale = 0.5;
            viewer = document.createElement('model-viewer');
            const attrs = {
                alt: 'マリンバの3Dモデル。音板、共鳴管、脚の調整機構を回転して見ることができます。',
                'aria-describedby': 'model-help',
                'camera-controls': '',
                'touch-action': 'pan-y',
                'disable-pan': '',
                'disable-tap': '',
                'camera-orbit': initialOrbit,
                'min-camera-orbit': 'auto 10deg 35%',
                'max-camera-orbit': 'auto 110deg 150%',
                'field-of-view': '30deg',
                'interaction-prompt': 'none',
                'shadow-intensity': '0',
                exposure: '1',
                loading: 'eager',
                'interpolation-decay': reducedMotion.matches ? '0' : '60',
                src: new URL('../models/marimba.glb', import.meta.url).href
            };
            for (const [key, value] of Object.entries(attrs)) viewer.setAttribute(key, value);
            const signal = events.signal;
            viewer.addEventListener('load', () => {
                if (current !== attempt) return;
                clearTimeout(timeout);
                state = 'ready';
                stage.classList.add('is-ready');
                stage.setAttribute('aria-busy', 'false');
                toolbar.hidden = false;
                help.hidden = false;
                status.textContent = '3Dモデルを表示しました。下のボタンでも操作できます。';
                if (document.activeElement === start) toolbar.querySelector('button').focus({ preventScroll: true });
                start.hidden = true;
            }, { signal, once: true });
            viewer.addEventListener('error', () => fail('3D表示を読み込めませんでした。'), { signal });
            mount.append(viewer);
        } catch {
            if (current === attempt) fail('この環境では3D表示を開始できませんでした。');
        }
    }

    start.addEventListener('click', load);
    toolbar.addEventListener('click', event => {
        const action = event.target.closest('[data-model-action]')?.dataset.modelAction;
        if (!action || state !== 'ready' || !viewer) return;
        if (action === 'reset') {
            viewer.cameraOrbit = initialOrbit;
            viewer.fieldOfView = '30deg';
        } else if (action === 'in' || action === 'out') {
            viewer.zoom(action === 'in' ? 2 : -2);
        } else {
            const orbit = viewer.getCameraOrbit();
            const theta = orbit.theta * 180 / Math.PI + (action === 'left' ? -20 : action === 'right' ? 20 : 0);
            const phi = Math.max(10, Math.min(110, orbit.phi * 180 / Math.PI + (action === 'up' ? -15 : action === 'down' ? 15 : 0)));
            viewer.cameraOrbit = `${theta}deg ${phi}deg ${orbit.radius}m`;
        }
        if (reducedMotion.matches) viewer.jumpCameraToGoal();
    });
    reducedMotion.addEventListener('change', () => {
        if (viewer) viewer.interpolationDecay = reducedMotion.matches ? 0 : 60;
    });
    // Disconnect the component from rendering; bfcache gets a clean restart.
    window.addEventListener('pagehide', () => {
        clearTimeout(timeout);
        attempt++;
        events.abort();
        viewer?.remove();
        viewer = null;
    });
    window.addEventListener('pageshow', event => {
        if (!event.persisted) return;
        events = new AbortController();
        state = 'idle';
        stage.classList.remove('is-ready');
        stage.setAttribute('aria-busy', 'false');
        toolbar.hidden = true;
        help.hidden = true;
        start.hidden = false;
        start.removeAttribute('aria-disabled');
        start.textContent = '3Dで見る ↗';
        status.textContent = 'ボタンを押すと3Dモデルを読み込みます。';
    });
}
