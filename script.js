const API_BASE = '/api';

async function fetchState() {
    try {
        const res = await fetch(`${API_BASE}/tasks`);
        const data = await res.json();
        renderDashboard(data);
    } catch (e) {
        console.error("Failed to fetch state", e);
    }
}

let editingId = null;

async function addTask() {
    const titleIn = document.getElementById('taskTitle');
    const dueIn = document.getElementById('taskDue');
    const weightIn = document.getElementById('taskWeight');
    const btn = document.querySelector('button[onclick="addTask()"]');

    const title = titleIn.value;
    const due = dueIn.value;
    const weight = weightIn.value;

    if (!title) return;

    if (editingId) {
        // Update existing
        await fetch(`${API_BASE}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: editingId, title, due_date: due, weight })
        });
        editingId = null;
        btn.innerText = "Add Task";
        btn.style.background = ""; // Reset color
    } else {
        // Create new
        await fetch(`${API_BASE}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, due_date: due, weight })
        });
    }

    titleIn.value = '';
    fetchState();
}

function editTask(id, title, due, weight) {
    editingId = id;
    document.getElementById('taskTitle').value = title;
    document.getElementById('taskDue').value = due; // might fail if simple date string vs 'today'
    // Map date back to select if possible, else just keep as is? 
    // The select has generic options. If the date doesn't match 'today/tomorrow', we might need to handle it.
    // For simplicity, let's just leave the date select as is or try to match.
    // Actually, let's not force the select to match arbitrary dates, just title/weight.
    document.getElementById('taskWeight').value = weight;

    document.getElementById('taskTitle').focus();

    // Change Button
    const btn = document.querySelector('button[onclick="addTask()"]');
    btn.innerText = "Update Task";
    btn.style.background = "#fb923c"; // Orange for edit
}

async function toggleComplete(id) {
    await fetch(`${API_BASE}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    fetchState();
}

async function deleteTask(id) {
    if (!confirm("Delete this task?")) return;
    await fetch(`${API_BASE}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    fetchState();
}

async function runAuto50() {
    await fetch(`${API_BASE}/auto-50`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    fetchState();
}

function renderDashboard(data) {
    // 1. Render Tasks
    const list = document.getElementById('taskList');
    list.innerHTML = '';

    // Grouping could be done here, but let's just show sorted list for now or group by date
    // Simple list rendering with visual indicators
    data.tasks.forEach(task => {
        const el = document.createElement('div');
        el.className = `task-item ${task.completed ? 'completed' : ''}`;

        let dateClass = 'week';
        const todayStr = new Date().toISOString().split('T')[0];
        // Simple date logic for pill color
        if (task.due_date.includes(todayStr)) dateClass = 'today';
        else if (task.due_date.includes('tomorrow')) dateClass = 'tomorrow';

        el.innerHTML = `
            <div class="info" onclick="toggleComplete(${task.id})" style="cursor: pointer;">
                <span class="task-title">${task.title}</span>
                <div class="task-meta">
                    <span class="pill ${dateClass}">${task.due_date}</span>
                    <span class="pill">Weight: ${task.weight}</span>
                </div>
            </div>
            <div class="actions" style="display:flex; gap:5px;">
                <button onclick="editTask(${task.id}, '${task.title.replace(/'/g, "\\'")}', '${task.due_date}', ${task.weight})" style="background:transparent; border:1px solid rgba(255,255,255,0.2); padding:5px 10px;">
                    ✎
                </button>
                <button onclick="toggleComplete(${task.id})" style="background:transparent; border:1px solid rgba(255,255,255,0.2); padding:5px 10px;">
                    ${task.completed ? 'Undo' : 'Done'}
                </button>
                <button onclick="deleteTask(${task.id})" style="background:rgba(239, 68, 68, 0.2); color:#fca5a5; border:1px solid rgba(239, 68, 68, 0.3); padding:5px 10px;">
                    ✕
                </button>
            </div>
        `;
        list.appendChild(el);
    });

    // 2. Update Progress
    const progress = data.progress.progress;
    document.getElementById('progressBar').style.width = `${progress}%`;
    document.getElementById('progressPercentage').innerText = `${Math.round(progress)}%`;
    document.getElementById('interpretation').innerText = data.interpretation;

    // 3. Update Pie Chart (CSS/SVG)
    const totalW = data.progress.total_weight;
    const doneW = data.progress.completed_weight;
    if (totalW > 0) {
        const percent = doneW / totalW;
        const circumference = 2 * Math.PI * 16; // r=16
        const offset = circumference * (1 - percent);

        // Remove old circle if exists (or update)
        const svg = document.querySelector('.pie-chart');
        let circle = svg.querySelector('.value-circle');
        if (!circle) {
            circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('class', 'value-circle');
            circle.setAttribute('r', '16');
            circle.setAttribute('cx', '16');
            circle.setAttribute('cy', '16');
            circle.setAttribute('fill', 'transparent');
            circle.setAttribute('stroke', '#4ade80');
            circle.setAttribute('stroke-width', '32');
            circle.setAttribute('stroke-dasharray', `${circumference} ${circumference}`);
            svg.appendChild(circle);
        }
        circle.setAttribute('stroke-dashoffset', offset);
    }
}

// Init
fetchState();
