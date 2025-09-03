// Dynamic form helpers + collect data before submit
function addProblem(prefill=''){
  const c = document.getElementById('problems-container');
  const div = document.createElement('div');
  div.className = 'd-flex gap-2';
  div.innerHTML = `<input class="form-control form-control-sm bg-800 text-light" placeholder="Problem statement" value="${prefill || ''}" />
                   <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('div').remove()">×</button>`;
  c.appendChild(div);
}

function addExtra(key='', val=''){
  const c = document.getElementById('extra-container');
  const div = document.createElement('div');
  div.className = 'd-flex gap-2';
  div.innerHTML = `<input class="form-control form-control-sm bg-800 text-light" placeholder="Key" value="${key}" />
                   <input class="form-control form-control-sm bg-800 text-light" placeholder="Value" value="${val}" />
                   <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('div').remove()">×</button>`;
  c.appendChild(div);
}

function collectAndSubmit(form){
  // collect domains
  const ds = [];
  const sel = document.getElementById('domains-select');
  if(sel){
    for(const opt of sel.options) if(opt.selected) ds.push(opt.value);
  }
  document.getElementById('domains_json').value = JSON.stringify(ds);

  // problems
  const probs = [];
  const pc = document.getElementById('problems-container');
  if(pc){
    for(const child of pc.children){
      const ip = child.querySelector('input');
      if(ip && ip.value.trim()) probs.push(ip.value.trim());
    }
  }
  document.getElementById('problems_json').value = JSON.stringify(probs);

  // extra
  const ext = {};
  const ec = document.getElementById('extra-container');
  if(ec){
    for(const child of ec.children){
      const k = child.children[0].value.trim();
      const v = child.children[1].value.trim();
      if(k) ext[k] = v;
    }
  }
  document.getElementById('extra_json').value = JSON.stringify(ext);

  return true;
}

// upvote helper used in home.html: show toast
function showToast(message, type='info'){
  const area = document.getElementById('toast-area');
  const id = 't' + Math.random().toString(36).slice(2,8);
  area.insertAdjacentHTML('beforeend', `<div id="${id}" class="toast align-items-center text-bg-${type} border-0 mb-2 show"><div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="document.getElementById('${id}').remove()"></button></div></div>`);
  setTimeout(()=>{ const n = document.getElementById(id); if(n) n.remove(); }, 4000);
}
