function addRound() {
  const c = document.querySelector('#rounds-container');
  const div = document.createElement('div');
  div.className = 'row g-2 align-items-end';
  div.innerHTML = `
    <div class="col-md-3"><label class="form-label">Name</label><input class="form-control r-name" placeholder="Round 1"/></div>
    <div class="col-md-3"><label class="form-label">Date</label><input type="date" class="form-control r-date"/></div>
    <div class="col-md-2"><label class="form-label">Time</label><input type="time" class="form-control r-time"/></div>
    <div class="col-md-3"><label class="form-label">Venue</label><input class="form-control r-venue" placeholder="Hall / Online"/></div>
    <div class="col-md-1 text-end"><button type="button" class="btn btn-outline-danger" onclick="this.closest('.row').remove()">×</button></div>
    <div class="col-12"><input class="form-control r-desc" placeholder="Description (optional)"/></div>
  `;
  c.appendChild(div);
}

function addLevel() {
  const c = document.querySelector('#levels-container');
  const div = document.createElement('div');
  div.className = 'row g-2 align-items-end';
  div.innerHTML = `
    <div class="col-md-3"><label class="form-label">Level</label><input class="form-control l-name" placeholder="Level 1"/></div>
    <div class="col-md-8"><label class="form-label">Description</label><input class="form-control l-desc" placeholder="Explain this level"/></div>
    <div class="col-md-1 text-end"><button type="button" class="btn btn-outline-danger" onclick="this.closest('.row').remove()">×</button></div>
  `;
  c.appendChild(div);
}

function addExtra() {
  const c = document.querySelector('#extra-container');
  const div = document.createElement('div');
  div.className = 'row g-2 align-items-end';
  div.innerHTML = `
    <div class="col-md-4"><label class="form-label">Key</label><input class="form-control e-key" placeholder="e.g., Prize Pool"/></div>
    <div class="col-md-7"><label class="form-label">Value</label><input class="form-control e-val" placeholder="₹50,000"/></div>
    <div class="col-md-1 text-end"><button type="button" class="btn btn-outline-danger" onclick="this.closest('.row').remove()">×</button></div>
  `;
  c.appendChild(div);
}

function serializeDynamicFields() {
  // Rounds
  const rounds = [...document.querySelectorAll('#rounds-container .row')].map(row => ({
    name: row.querySelector('.r-name')?.value || '',
    date: row.querySelector('.r-date')?.value || '',
    time: row.querySelector('.r-time')?.value || '',
    venue: row.querySelector('.r-venue')?.value || '',
    desc: row.querySelector('.r-desc')?.value || '',
  }));
  document.querySelector('#rounds_json').value = JSON.stringify(rounds);

  // Levels
  const levels = [...document.querySelectorAll('#levels-container .row')].map(row => ({
    name: row.querySelector('.l-name')?.value || '',
    desc: row.querySelector('.l-desc')?.value || '',
  }));
  document.querySelector('#levels_json').value = JSON.stringify(levels);

  // Extra
  const extras = {};
  [...document.querySelectorAll('#extra-container .row')].forEach(row => {
    const k = row.querySelector('.e-key')?.value?.trim();
    const v = row.querySelector('.e-val')?.value?.trim();
    if (k) extras[k] = v || '';
  });
  document.querySelector('#extra_json').value = JSON.stringify(extras);

  return true; // allow form submit
}
