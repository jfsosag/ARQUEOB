/* ================================================================
   ARQUEOB — app.js
   ================================================================ */

/* ---- Toasts ---- */
document.querySelectorAll('.toast').forEach(el => new bootstrap.Toast(el, {delay: 5000}).show());

/* ---- Confirmation dialogs ---- */
document.querySelectorAll('[data-confirm]').forEach(form => form.addEventListener('submit', e => { if (!confirm(form.dataset.confirm)) e.preventDefault(); }));

/* ---- Old arqueo lines removed (handled inline in arqueo/formulario.html) ---- */

/* ================================================================
   COBROS — Client listing search (real-time filter)
   ================================================================ */
const clientSearch = document.querySelector('#client-search');
if (clientSearch && (document.querySelector('#clients-table') || document.querySelector('#clients-cards'))) {
  clientSearch.addEventListener('input', () => {
    const q = clientSearch.value.toLowerCase().trim();
    document.querySelectorAll('.client-row, .client-card').forEach(el => {
      const nombre = (el.dataset.nombre || '').toLowerCase();
      const telefono = (el.dataset.telefono || '').toLowerCase();
      const rnc = (el.dataset.rnc || '').toLowerCase();
      el.style.display = (!q || nombre.includes(q) || telefono.includes(q) || rnc.includes(q)) ? '' : 'none';
    });
  });
}

/* ================================================================
   COBRAR — Payment form
   ================================================================ */
const paymentForm = document.querySelector('#payment-form');
if (paymentForm) {
  const totalEl = document.querySelector('#payment-total');
  const submitBtn = document.querySelector('#submit-payment');
  const montoRecibido = document.querySelector('#monto-recibido');
  const cambioRow = document.querySelector('#cambio-row');
  const cambioDisplay = document.querySelector('#cambio-display');
  const selectAllCb = document.querySelector('#select-all-cb');
  const selectAllBtn = document.querySelector('#select-all-btn');
  let selectedTotal = 0;

  function formatCurrency(n) {
    return `RD$ ${n.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  }

  function updateTotal() {
    selectedTotal = 0;
    document.querySelectorAll('.select-invoice').forEach(cb => {
      if (cb.checked) {
        const card = cb.closest('tr') || cb.closest('.invoice-card');
        const balance = parseFloat(card.querySelector('.payment-amount')?.dataset.balance || card.dataset.balance || 0);
        selectedTotal += balance;
      }
    });
    totalEl.textContent = formatCurrency(selectedTotal);
    updateChange();
    submitBtn.disabled = selectedTotal <= 0;
  }

  function updateChange() {
    const recibido = parseFloat(montoRecibido?.value) || 0;
    if (recibido > 0 && selectedTotal > 0) {
      const cambio = recibido - selectedTotal;
      cambioDisplay.textContent = formatCurrency(cambio);
      cambioDisplay.className = `fs-5 fw-bold ${cambio >= 0 ? 'text-success' : 'text-danger'}`;
      cambioRow.classList.remove('d-none');
    } else {
      cambioRow.classList.add('d-none');
    }
  }

  /* Desktop table checkboxes */
  document.querySelectorAll('.select-invoice').forEach(cb => {
    cb.addEventListener('change', () => {
      const row = cb.closest('tr') || cb.closest('.invoice-card');
      const amountInput = row.querySelector('.payment-amount');
      if (amountInput) amountInput.disabled = !cb.checked;
      row.classList.toggle('selected', cb.checked);
      updateSelectAllState();
      updateTotal();
    });
  });

  /* Mobile card click */
  document.querySelectorAll('.invoice-card').forEach(card => {
    card.addEventListener('click', e => {
      if (e.target.tagName === 'INPUT') return;
      const cb = card.querySelector('.select-invoice');
      cb.checked = !cb.checked;
      cb.dispatchEvent(new Event('change'));
    });
  });

  /* Amount input changes */
  document.querySelectorAll('.payment-amount').forEach(input => {
    input.addEventListener('input', updateTotal);
  });

  /* Select all */
  function updateSelectAllState() {
    const checks = document.querySelectorAll('.select-invoice');
    const allChecked = checks.length > 0 && [...checks].every(c => c.checked);
    if (selectAllCb) selectAllCb.checked = allChecked;
  }

  selectAllCb?.addEventListener('change', () => {
    document.querySelectorAll('.select-invoice').forEach(cb => {
      cb.checked = selectAllCb.checked;
      const row = cb.closest('tr') || cb.closest('.invoice-card');
      const amountInput = row.querySelector('.payment-amount');
      if (amountInput) amountInput.disabled = !cb.checked;
      row.classList.toggle('selected', cb.checked);
    });
    updateTotal();
  });

  selectAllBtn?.addEventListener('click', () => {
    const allChecked = [...document.querySelectorAll('.select-invoice')].every(c => c.checked);
    document.querySelectorAll('.select-invoice').forEach(cb => {
      cb.checked = !allChecked;
      const row = cb.closest('tr') || cb.closest('.invoice-card');
      const amountInput = row.querySelector('.payment-amount');
      if (amountInput) amountInput.disabled = !cb.checked;
      row.classList.toggle('selected', cb.checked);
    });
    if (selectAllCb) selectAllCb.checked = !allChecked;
    updateTotal();
  });

  /* Payment method toggle */
  const formaPago = document.querySelector('#forma-pago');
  if (formaPago) {
    formaPago.addEventListener('change', () => {
      document.querySelectorAll('#cheque-fields, #transferencia-fields, #tarjeta-fields').forEach(f => f.style.display = 'none');
      const val = formaPago.value;
      if (val === 'Cheque') document.querySelector('#cheque-fields').style.display = '';
      else if (val === 'Transferencia Bancaria') document.querySelector('#transferencia-fields').style.display = '';
      else if (val === 'Tarjeta') document.querySelector('#tarjeta-fields').style.display = '';
    });
  }

  /* Change calculation */
  montoRecibido?.addEventListener('input', updateChange);

  /* Form submit — add hidden inputs for selected invoices */
  paymentForm.addEventListener('submit', e => {
    document.querySelectorAll('.select-invoice:checked').forEach(cb => {
      const row = cb.closest('tr') || cb.closest('.invoice-card');
      const amountInput = row.querySelector('.payment-amount');
      const value = amountInput ? amountInput.value : row.dataset.balance;
      paymentForm.insertAdjacentHTML('beforeend',
        `<input type="hidden" name="aplicacion[]" value="${cb.value}"><input type="hidden" name="monto_aplicado[]" value="${value}">`
      );
    });
  });

  updateTotal();
}

/* ================================================================
   COBRO INFORMAL — Client search inline
   ================================================================ */
const isCobroInformal = !!document.querySelector('#cobro-informal-form');
if (isCobroInformal) {
  const search = document.querySelector('#client-search');
  const results = document.querySelector('#client-results');
  if (search && results) {
    let timer;
    search.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        if (search.value.trim().length < 2) { results.replaceChildren(); return; }
        const clients = await fetch(`/clientes/api/buscar?q=${encodeURIComponent(search.value)}`).then(r => r.json());
        results.innerHTML = clients.map(c => `<button type="button" class="list-group-item list-group-item-action client-select-btn" data-id="${c.id}" data-nombre="${c.nombre}" data-telefono="${c.telefono}" data-rnc="${c.rnc_cedula || ''}"><strong>${c.nombre}</strong><small class="d-block">${c.telefono} · ${c.rnc_cedula || 'Sin RNC'}</small></button>`).join('');
        results.querySelectorAll('.client-select-btn').forEach(btn => btn.addEventListener('click', () => {
          document.querySelector('#cliente-id').value = btn.dataset.id;
          const display = document.querySelector('#selected-client-display');
          if (display) { display.style.display = ''; display.innerHTML = `<strong>${btn.dataset.nombre}</strong><small class="d-block text-secondary">${btn.dataset.telefono} · ${btn.dataset.rnc || 'Sin RNC'}</small>`; }
          results.replaceChildren();
          search.value = '';
        }));
      }, 250);
    });
  }
}

/* ================================================================
   CONCEPTO "OTRO" TOGGLE
   ================================================================ */
const conceptoSelect = document.querySelector('#concepto-select');
const conceptoOtro = document.querySelector('#concepto-otro');
if (conceptoSelect && conceptoOtro) {
  conceptoSelect.addEventListener('change', () => {
    conceptoOtro.style.display = conceptoSelect.value === 'Otro' ? '' : 'none';
    if (conceptoSelect.value !== 'Otro') conceptoOtro.value = '';
  });
}

/* ================================================================
   SALDO PENDIENTE CALCULATOR (cobro informal)
   ================================================================ */
const montoTotal = document.querySelector('#monto-total');
const montoPagado = document.querySelector('#monto-pagado');
const saldoPendiente = document.querySelector('#saldo-pendiente');
if (montoTotal && montoPagado && saldoPendiente) {
  const calc = () => {
    const total = parseFloat(montoTotal.value) || 0;
    const pagado = parseFloat(montoPagado.value) || 0;
    const saldo = total - pagado;
    saldoPendiente.value = `RD$ ${saldo.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    saldoPendiente.style.color = saldo < 0 ? '#dc3545' : '';
  };
  montoTotal.addEventListener('input', calc);
  montoPagado.addEventListener('input', calc);
  calc();
}

/* ================================================================
   NEW CLIENT MODAL (cobro informal desktop)
   ================================================================ */
const saveClientBtn = document.querySelector('#save-client-btn');
if (saveClientBtn) {
  saveClientBtn.addEventListener('click', async () => {
    const form = document.querySelector('#new-client-form');
    if (!form.reportValidity()) return;
    const data = Object.fromEntries(new FormData(form));
    try {
      const resp = await fetch('/clientes/api/buscar?q=' + encodeURIComponent(data.nombre), { method: 'GET' });
      const existing = await resp.json();
      if (existing.length > 0 && existing[0].nombre === data.nombre) {
        document.querySelector('#cliente-id').value = existing[0].id;
        const display = document.querySelector('#selected-client-display');
        if (display) { display.style.display = ''; display.innerHTML = `<strong>${existing[0].nombre}</strong><small class="d-block text-secondary">${existing[0].telefono} · ${existing[0].rnc_cedula || 'Sin RNC'}</small>`; }
        bootstrap.Modal.getInstance(document.querySelector('#newClientModal')).hide();
        return;
      }
    } catch(e) {}
    const fd = new FormData();
    fd.append('nombre', data.nombre);
    fd.append('telefono', data.telefono || '');
    fd.append('direccion', data.direccion || 'N/A');
    fd.append('rnc_cedula', data.rnc_cedula || '');
    try {
      const resp = await fetch('/clientes/api/crear', { method: 'POST', body: fd });
      if (resp.ok) {
        const c = await resp.json();
        document.querySelector('#cliente-id').value = c.id;
        const display = document.querySelector('#selected-client-display');
        if (display) { display.style.display = ''; display.innerHTML = `<strong>${c.nombre}</strong><small class="d-block text-secondary">${c.telefono} · ${c.rnc_cedula || 'Sin RNC'}</small>`; }
        bootstrap.Modal.getInstance(document.querySelector('#newClientModal')).hide();
      }
    } catch(e) { alert('Error al crear el cliente.'); }
  });
}
