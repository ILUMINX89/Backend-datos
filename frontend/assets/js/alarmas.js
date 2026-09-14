(() => {
    const seen = new Set();
    let initialized = false;
    const card = document.querySelector('#alarm-card');
    const toast = document.querySelector('#alarm-toast');

    function stopAlert() {
        card?.classList.remove('alerting');
        toast?.classList.remove('alerting');
    }
    function startAlert() {
        card?.classList.add('alerting');
        if (toast) { toast.hidden = false; toast.classList.add('alerting'); }
    }
    function process(alarms) {
        const newCritical = initialized && alarms.some(alarm => !seen.has(String(alarm.id)) && Number(alarm.tipo) === 1);
        alarms.forEach(alarm => seen.add(String(alarm.id)));
        initialized = true;
        if (newCritical) startAlert();
    }
    ['click', 'keydown', 'touchstart'].forEach(event => window.addEventListener(event, stopAlert, {passive: true}));
    document.querySelector('#cerrar-alerta')?.addEventListener('click', () => { stopAlert(); toast.hidden = true; });
    window.addEventListener('dashboard:update', event => process(event.detail.alarmas ?? []));
})();
