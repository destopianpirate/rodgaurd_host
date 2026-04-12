const API_BASE = 'http://localhost:5000/api';
let allData = [];
let searchTerm = '';
let filterSev = 'all';
let filterStat = 'all';

document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    
    document.getElementById('refreshDataBtn').addEventListener('click', fetchData);
    document.getElementById('clearBtn').addEventListener('click', clearAll);
    document.getElementById('addBtn').addEventListener('click', () => openModal());
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.getElementById('potholeForm').addEventListener('submit', handleFormSubmit);

    // Filters and Search Setup
    const sInput = document.getElementById('searchInput');
    const fSev = document.getElementById('filterSeverity');
    const fStat = document.getElementById('filterStatus');

    if (sInput) sInput.addEventListener('input', (e) => { searchTerm = e.target.value.toLowerCase(); applyFilters(); });
    if (fSev) fSev.addEventListener('change', (e) => { filterSev = e.target.value; applyFilters(); });
    if (fStat) fStat.addEventListener('change', (e) => { filterStat = e.target.value; applyFilters(); });
});

async function fetchData() {
    try {
        const res = await fetch(`${API_BASE}/potholes?status=all`);
        const data = await res.json();
        allData = data;
        applyFilters(); // Uses the current search/filters instead of rendering map directly
    } catch (e) {
        console.error("Failed to fetch data", e);
        document.getElementById('potholeTableBody').innerHTML = '<tr><td colspan="7">Failed to load data. Ensure backend is running.</td></tr>';
    }
}

function applyFilters() {
    let filtered = allData;

    // Search
    if (searchTerm) {
        filtered = filtered.filter(p => 
            p.id.toString().includes(searchTerm) || 
            (p.description && p.description.toLowerCase().includes(searchTerm)) ||
            p.lat.toString().includes(searchTerm) ||
            p.lng.toString().includes(searchTerm)
        );
    }

    // Severity Filter
    if (filterSev !== 'all') {
        filtered = filtered.filter(p => p.severity === filterSev);
    }

    // Status Filter
    if (filterStat !== 'all') {
        filtered = filtered.filter(p => p.status === filterStat);
    }

    renderTable(filtered);
}

function renderTable(data) {
    const tbody = document.getElementById('potholeTableBody');
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No hazards match your filters.</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map((p, index) => `
        <tr class="animated-row" style="animation-delay: ${index * 0.05}s">
            <td>#${p.id}</td>
            <td style="font-family: monospace; font-size: 12px;">${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}</td>
            <td><span class="sev-badge sev-${p.severity}">${p.severity}</span></td>
            <td>${Math.round(p.confidence * 100)}%</td>
            <td><span class="status-badge stat-${p.status}">${p.status === 'active' ? 'ACTIVE' : 'RESOLVED'}</span></td>
            <td style="font-size: 13px; font-weight:600;">${p.verified_count || 1} time(s)</td>
            <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color:var(--text-secondary); font-size: 13px;" title="${p.description || '--'}">${p.description || '--'}</td>
            <td style="white-space: nowrap;">
                <button class="btn-edit" onclick="editPothole(${p.id})" title="Edit Information">Edit</button>
                <button class="btn-del" onclick="deletePothole(${p.id})" title="Delete Record">Del</button>
            </td>
        </tr>
    `).join('');
}

function editPothole(id) {
    const p = allData.find(x => x.id === id);
    if (!p) return;
    document.getElementById('pid').value = p.id;
    document.getElementById('plat').value = p.lat;
    document.getElementById('plng').value = p.lng;
    document.getElementById('pseverity').value = p.severity;
    document.getElementById('pconf').value = p.confidence;
    document.getElementById('pstatus').value = p.status;
    document.getElementById('pdesc').value = p.description;
    
    document.getElementById('modalTitle').textContent = 'Edit Pothole #' + id;
    document.getElementById('potholeModal').classList.add('active');
}

function openModal() {
    document.getElementById('potholeForm').reset();
    document.getElementById('pid').value = '';
    // default coords for convenience 
    document.getElementById('plat').value = '23.2156';
    document.getElementById('plng').value = '72.6869';
    document.getElementById('modalTitle').textContent = 'Add New Pothole';
    document.getElementById('potholeModal').classList.add('active');
}

function closeModal() {
    document.getElementById('potholeModal').classList.remove('active');
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('pid').value;
    
    const payload = {
        lat: parseFloat(document.getElementById('plat').value),
        lng: parseFloat(document.getElementById('plng').value),
        severity: document.getElementById('pseverity').value,
        confidence: parseFloat(document.getElementById('pconf').value),
        status: document.getElementById('pstatus').value,
        description: document.getElementById('pdesc').value
    };

    try {
        if (id) {
            // Update
            await fetch(`${API_BASE}/potholes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // Create
            payload.vehicle_id = 'Admin-Input';
            await fetch(`${API_BASE}/potholes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }
        closeModal();
        fetchData();
    } catch (e) {
        alert('Error saving data: ' + e.message);
    }
}

async function deletePothole(id) {
    if (!confirm(`Are you sure you want to delete pothole #${id}?`)) return;
    
    try {
        await fetch(`${API_BASE}/potholes/${id}`, {
            method: 'DELETE'
        });
        fetchData();
    } catch (e) {
        alert('Error deleting: ' + e.message);
    }
}

async function clearAll() {
    if (!confirm("🚨 Are you absolutely sure you want to WIPE THE ENTIRE DATABASE? This cannot be undone! 🚨")) return;
    
    try {
        await fetch(`${API_BASE}/clear`, {
            method: 'POST' // Corrected to POST as per Python backend
        });
        fetchData();
        alert('Database cleared successfully.');
    } catch(e) {
        alert('Error clearing database: ' + e.message);
    }
}
