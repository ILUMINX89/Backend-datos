(() => {
    const normalize = value => String(value ?? '').toLocaleLowerCase('es');
    function applyFilters() {
        const query = normalize(document.querySelector('#busqueda')?.value);
        const type = document.querySelector('#filtro-tipo')?.value ?? '';
        const state = document.querySelector('#filtro-estado')?.value ?? '';
        document.querySelectorAll('#tabla-alarmas tbody tr').forEach(row => {
            const matchesQuery = normalize(row.textContent).includes(query);
            const matchesType = !type || row.dataset.tipo === type;
            const matchesState = !state || row.dataset.estado === state;
            row.hidden = !(matchesQuery && matchesType && matchesState);
        });
    }
    ['busqueda', 'filtro-tipo', 'filtro-estado'].forEach(id => {
        document.querySelector(`#${id}`)?.addEventListener(id === 'busqueda' ? 'input' : 'change', applyFilters);
    });
    window.NocTable = { applyFilters };
})();
