(() => {
    'use strict';

    const REGIONS = [
        'gkp-table-region',
        'perdida-latencia-table-region',
        'temperatura-table-region',
    ];
    const SPEED_PX_SECOND = 22;
    const START_DELAY = 1500;
    const BOTTOM_DELAY = 1500;
    const TOP_DELAY = 1000;
    const USER_PAUSE = 4000;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const states = REGIONS.map((id) => ({
        region: document.getElementById(id),
        hovered: false,
        focused: false,
        resumeAt: performance.now() + START_DELAY,
        bottomSince: null,
    })).filter((state) => state.region);
    let enabled = false;
    let lastFrame = performance.now();

    function hold(state, duration) {
        state.resumeAt = performance.now() + duration;
        state.bottomSince = null;
    }

    function scrollToTop(state) {
        state.region.scrollTop = 0;
        hold(state, TOP_DELAY);
    }

    states.forEach((state) => {
        const region = state.region;
        region.addEventListener('mouseenter', () => { state.hovered = true; });
        region.addEventListener('mouseleave', () => {
            state.hovered = false;
            hold(state, TOP_DELAY);
        });
        region.addEventListener('focusin', () => { state.focused = true; });
        region.addEventListener('focusout', (event) => {
            if (!region.contains(event.relatedTarget)) {
                state.focused = false;
                hold(state, TOP_DELAY);
            }
        });
        ['wheel', 'touchstart', 'pointerdown'].forEach((name) => {
            region.addEventListener(name, () => hold(state, USER_PAUSE), { passive: true });
        });
    });

    function frame(now) {
        const elapsed = Math.min(Math.max(now - lastFrame, 0), 100);
        lastFrame = now;

        if (enabled && !document.hidden && !reducedMotion.matches) {
            states.forEach((state) => {
                const region = state.region;
                const maxScroll = region.scrollHeight - region.clientHeight;
                if (state.hovered || state.focused || now < state.resumeAt || maxScroll <= 2) {
                    return;
                }
                if (region.scrollTop >= maxScroll - 1) {
                    state.bottomSince ??= now;
                    if (now - state.bottomSince >= BOTTOM_DELAY) {
                        scrollToTop(state);
                    }
                } else {
                    state.bottomSince = null;
                    region.scrollTop = Math.min(
                        maxScroll,
                        region.scrollTop + elapsed * SPEED_PX_SECOND / 1000
                    );
                }
            });
        }
        requestAnimationFrame(frame);
    }

    window.GKPTableAutoScroll = {
        setEnabled(value) {
            enabled = Boolean(value);
            lastFrame = performance.now();
        },
        resetAll() {
            states.forEach((state) => scrollToTop(state));
        },
        scrollToTop(id) {
            const state = states.find((item) => item.region.id === id);
            if (state) scrollToTop(state);
        },
    };

    requestAnimationFrame(frame);
})();
