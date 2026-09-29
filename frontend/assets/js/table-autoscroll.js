(() => {
    'use strict';

    const instances = new WeakMap();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    class TableAutoScroll {
        constructor(region) {
            this.region = region;
            this.speed = 24;
            this.bottomPauseMs = 1600;
            this.topPauseMs = 1200;
            this.resumeAt = performance.now() + 1200;
            this.lastFrame = performance.now();
            this.bottomSince = null;
            this.hovered = false;
            this.focused = false;
            this.raf = null;

            this.bind();
            this.start();
        }

        bind() {
            this.region.addEventListener('mouseenter', () => {
                this.hovered = true;
            });

            this.region.addEventListener('mouseleave', () => {
                this.hovered = false;
                this.hold(1200);
            });

            this.region.addEventListener('focusin', () => {
                this.focused = true;
            });

            this.region.addEventListener('focusout', (event) => {
                if (!this.region.contains(event.relatedTarget)) {
                    this.focused = false;
                    this.hold(1200);
                }
            });

            ['wheel', 'touchstart', 'pointerdown'].forEach((eventName) => {
                this.region.addEventListener(eventName, () => this.hold(4500), {
                    passive: true,
                });
            });
        }

        hold(ms = 2500) {
            this.resumeAt = performance.now() + ms;
            this.lastFrame = performance.now();
        }

        toTop(ms = 2500) {
            this.region.scrollTop = 0;
            this.bottomSince = null;
            this.hold(ms);
        }

        canScroll() {
            return (
                !this.region.hidden
                && this.region.scrollHeight > this.region.clientHeight + 2
            );
        }

        start() {
            if (this.raf !== null) {
                return;
            }

            const step = (now) => {
                const elapsed = Math.max(0, now - this.lastFrame);
                this.lastFrame = now;

                if (
                    !document.hidden
                    && !reducedMotion.matches
                    && !this.hovered
                    && !this.focused
                    && now >= this.resumeAt
                    && this.canScroll()
                ) {
                    const maxScroll = Math.max(
                        0,
                        this.region.scrollHeight - this.region.clientHeight
                    );

                    if (this.region.scrollTop >= maxScroll - 1) {
                        if (this.bottomSince === null) {
                            this.bottomSince = now;
                        }

                        if (now - this.bottomSince >= this.bottomPauseMs) {
                            this.region.scrollTo({
                                top: 0,
                                behavior: 'smooth',
                            });
                            this.bottomSince = null;
                            this.hold(this.topPauseMs);
                        }
                    } else {
                        this.bottomSince = null;
                        this.region.scrollTop = Math.min(
                            maxScroll,
                            this.region.scrollTop + (elapsed / 1000) * this.speed
                        );
                    }
                } else {
                    this.bottomSince = null;
                }

                this.raf = requestAnimationFrame(step);
            };

            this.raf = requestAnimationFrame(step);
        }
    }

    function initialize() {
        document.querySelectorAll('[data-auto-scroll]').forEach((region) => {
            if (instances.has(region)) {
                return;
            }

            instances.set(region, new TableAutoScroll(region));
        });
    }

    window.GKPTableAutoScroll = {
        get(region) {
            return region ? instances.get(region) || null : null;
        },

        toTop(region, holdMs = 2500) {
            instances.get(region)?.toTop(holdMs);
        },

        initialize,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
})();
