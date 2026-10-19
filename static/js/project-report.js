(() => {
    const search = document.getElementById('projectReportSearch');
    const results = document.getElementById('projectSearchResults');
    const content = document.getElementById('projectReportContent');
    const searchStatus = document.getElementById('projectSearchStatus');
    let timer, searchVersion = 0, reportVersion = 0;
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    const number = value => new Intl.NumberFormat('es-MX', {maximumFractionDigits: 3}).format(value);
    const date = value => value ? esc(value.slice(0, 10).split('-').reverse().join('/')) : '—';
    async function getJSON(url) {
        const response = await fetch(url);
        if (!response.ok) throw new Error('No se pudo completar la consulta. Intenta nuevamente.');
        const data = await response.json();
        if (!data.success) throw new Error(data.message || 'No se pudo completar la consulta.');
        return data;
    }
    search.addEventListener('input', () => {
        clearTimeout(timer);
        const version = ++searchVersion;
        const query = search.value.trim();
        results.replaceChildren();
        searchStatus.textContent = query ? 'Buscando proyectos…' : 'Escribe una FP, nombre de proyecto o cliente.';
        if (!query) return;
        timer = setTimeout(async () => {
            try {
                const data = await getJSON(`/api/projects/search?q=${encodeURIComponent(query)}`);
                if (version !== searchVersion) return;
                searchStatus.textContent = data.projects.length
                    ? (data.has_more ? 'Se muestran 50 coincidencias. Afina tu búsqueda.' : `${data.projects.length} coincidencias. Selecciona un proyecto.`)
                    : 'No se encontraron proyectos.';
                data.projects.forEach(project => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'list-group-item list-group-item-action';
                    button.textContent = `${project.fp_code} · ${project.name} · ${project.client || 'Sin cliente'}`;
                    button.addEventListener('click', () => {
                        ++searchVersion;
                        clearTimeout(timer);
                        results.replaceChildren();
                        search.value = `${project.fp_code} · ${project.name}`;
                        searchStatus.textContent = 'Proyecto seleccionado. Puedes buscar otro proyecto.';
                        loadReport(project);
                    });
                    results.appendChild(button);
                });
            } catch (error) {
                if (version === searchVersion) searchStatus.textContent = error.message;
            }
        }, 250);
    });
    async function loadReport(project) {
        const version = ++reportVersion;
        content.innerHTML = '<p class="text-muted py-4" role="status">Cargando resumen…</p>';
        try {
            const data = await getJSON(`/api/projects/${project.id}/report`);
            if (version !== reportVersion) return;
            const p = data.project;
            const groups = new Map();
            data.materials.forEach(material => {
                if (!groups.has(material.area)) groups.set(material.area, []);
                groups.get(material.area).push(material);
            });
            let materials = '';
            for (const [area, rows] of groups) {
                materials += `<section class="mb-4"><h6 class="bg-light border rounded p-2">${esc(area)}</h6>
                    <div class="table-responsive"><table class="table table-sm table-striped align-middle">
                    <thead><tr><th>Material</th><th>Categoría</th><th class="text-end">Solicitado</th><th class="text-end">Entregado</th><th class="text-end">Pendiente</th><th>Estado</th></tr></thead><tbody>`;
                rows.forEach(m => {
                    const pending = m.quantity_pending;
                    const status = pending < -0.001 ? ['info', 'Entrega excedente'] : pending > 0.001
                        ? (m.quantity_delivered > 0 ? ['warning', 'Parcial'] : ['secondary', 'Sin entregar'])
                        : ['success', 'Completo'];
                    materials += `<tr><td>${esc(m.name)}</td><td>${esc(m.category)}</td>
                        <td class="text-end text-nowrap">${number(m.quantity_requested)} ${esc(m.unit)}</td>
                        <td class="text-end text-nowrap">${number(m.quantity_delivered)} ${esc(m.unit)}</td>
                        <td class="text-end text-nowrap">${number(pending)} ${esc(m.unit)}</td>
                        <td><span class="badge bg-${status[0]}">${status[1]}</span></td></tr>`;
                });
                materials += '</tbody></table></div></section>';
            }
            const reqRows = data.requests.map(r => `<tr><td>${esc(r.request_number)}${r.is_incident ? ' <span class="badge bg-warning text-dark">Incidencia</span>' : ''}</td>
                <td>${esc(r.area || r.department)}</td><td>${esc((r.status || '').replaceAll('_', ' '))}</td>
                <td>${date(r.created_at)}</td><td>${date(r.acquisition_deadline)}</td>
                <td><button type="button" class="btn btn-sm btn-outline-primary report-request" data-request-id="${Number(r.id)}" data-bs-toggle="modal" data-bs-target="#requestDetailModal" aria-label="Ver ${esc(r.request_number)}"><i class="fas fa-eye"></i></button></td></tr>`).join('');
            content.innerHTML = `<div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-4">
                <div><h5>${esc(p.fp_code)} · ${esc(p.name)}</h5><p class="text-muted mb-0">${esc(p.client || 'Sin cliente')} · Entrega: ${date(p.delivery_date)}</p></div>
                <a class="btn btn-sm btn-outline-primary" href="/api/projects/${encodeURIComponent(p.fp_code)}/export-report"><i class="fas fa-download me-1"></i>Exportar reporte</a></div>
                <h5>Materiales por área</h5>
                <p class="small text-muted">Entregas calculadas con los movimientos de almacén. Un pendiente negativo indica una entrega mayor a lo solicitado.</p>
                ${materials || '<p class="text-muted">Este proyecto no tiene materiales registrados.</p>'}
                <details class="border rounded p-3"><summary class="fw-bold">Requisiciones del proyecto (${data.requests.length})</summary>
                <div class="table-responsive mt-3"><table class="table table-sm table-hover"><thead><tr><th>Requisición</th><th>Área</th><th>Estado</th><th>Solicitud</th><th>Límite de adquisición</th><th>Detalle</th></tr></thead>
                <tbody>${reqRows || '<tr><td colspan="6">Sin requisiciones registradas.</td></tr>'}</tbody></table></div></details>`;
            content.querySelectorAll('.report-request').forEach(button => {
                button.addEventListener('click', () => viewRequest(Number(button.dataset.requestId)));
            });
        } catch (error) {
            if (version !== reportVersion) return;
            content.innerHTML = `<div class="alert alert-danger" role="alert">${esc(error.message)} <button type="button" class="btn btn-sm btn-outline-danger" id="retryProjectReport">Reintentar</button></div>`;
            document.getElementById('retryProjectReport').addEventListener('click', () => loadReport(project));
        }
    }
})();
