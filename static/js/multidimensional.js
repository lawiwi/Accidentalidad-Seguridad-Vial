/* =====================================================================
   Etapa 5 · Análisis multidimensional
   Controlador de las cuatro vistas interactivas.

   - Mantiene el "estado" de la vista (filtros, nivel de cada gráfico,
     ruta de drill-down, pivot y métrica de la matriz).
   - Cada cambio envía el estado a /analisis-multidimensional/api/pregunta/<n>;
     el servidor vuelve a consultar el modelo estrella y responde con
     indicadores, dos visualizaciones y la matriz ya recalculados.
   - Compatible con la navegación SPA de app-shell.js: el script puede
     cargarse varias veces; solo inicializa cada vista una vez.
   ===================================================================== */
(function () {
  'use strict';

  var COLORES = ['#232A54', '#2E9C93', '#D9A441', '#8C4E7E', '#5B7DB1', '#C8553D', '#6A994E', '#9C89B8',
                 '#3D5A80', '#E07A5F', '#81B29A', '#B5838D', '#F2CC8F', '#5E548E', '#118AB2', '#999999'];
  var nf = new Intl.NumberFormat('es-CO');

  function formatear(valor, formato) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) { return 's. d.'; }
    if (formato === 'pct') { return (valor * 100).toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' %'; }
    if (formato === 'pp') { return (valor >= 0 ? '+' : '−') + Math.abs(valor).toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' p. p.'; }
    if (formato === 'anios') { return valor.toLocaleString('es-CO', { maximumFractionDigits: 1 }) + ' años'; }
    return nf.format(Math.round(valor));
  }

  function cargarChartJs(url) {
    if (window.Chart) { return Promise.resolve(window.Chart); }
    if (window.__mdChartPromise) { return window.__mdChartPromise; }
    window.__mdChartPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = url;
      s.onload = function () { resolve(window.Chart); };
      s.onerror = function () { reject(new Error('No se pudo cargar Chart.js')); };
      document.head.appendChild(s);
    });
    return window.__mdChartPromise;
  }

  function el(tag, attrs, texto) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (texto !== undefined) { e.textContent = texto; }
    return e;
  }

  function Vista(raiz) {
    this.raiz = raiz;
    this.numero = parseInt(raiz.getAttribute('data-md-vista'), 10);
    this.api = raiz.getAttribute('data-api');
    this.chartUrl = raiz.getAttribute('data-chartjs');
    this.graficos = {};
    this.datos = null;
    this.reiniciarEstado();
    this.enlazar();
  }

  Vista.prototype.reiniciarEstado = function () {
    this.estado = { filtros: {}, g1: {}, g2: {}, matriz: {}, ultima_operacion: null };
  };

  /* ---------------- Eventos ---------------- */
  Vista.prototype.enlazar = function () {
    var self = this;

    // Filtros (slice / dice): casillas dentro de un <details>
    this.raiz.querySelectorAll('[data-filtro]').forEach(function (det) {
      var id = det.getAttribute('data-filtro');
      var buscar = det.querySelector('[data-buscar]');
      if (buscar) {
        buscar.addEventListener('input', function () {
          var t = buscar.value.toLowerCase();
          det.querySelectorAll('label').forEach(function (l) { l.style.display = l.textContent.toLowerCase().indexOf(t) >= 0 ? '' : 'none'; });
        });
      }
      det.addEventListener('change', function () {
        var valores = Array.prototype.map.call(det.querySelectorAll('input[type=checkbox]:checked'), function (c) { return c.value; });
        self.estado.filtros[id] = valores;
        det.querySelector('[data-resumen]').textContent = valores.length === 0 ? 'Todos' : (valores.length === 1 ? valores[0] : valores.length + ' seleccionados');
        self.estado.ultima_operacion = self.tipoFiltro();
        self.consultar();
      });
      det.querySelector('[data-limpiar]').addEventListener('click', function () {
        det.querySelectorAll('input[type=checkbox]').forEach(function (c) { c.checked = false; });
        det.dispatchEvent(new Event('change'));
      });
      det.querySelector('[data-cerrar]').addEventListener('click', function () { det.open = false; });
    });

    this.raiz.querySelector('[data-accion=reiniciar]').addEventListener('click', function () {
      self.raiz.querySelectorAll('[data-filtro] input[type=checkbox]').forEach(function (c) { c.checked = false; });
      self.raiz.querySelectorAll('[data-resumen]').forEach(function (r) { r.textContent = 'Todos'; });
      self.reiniciarEstado();
      self.consultar();
    });

    // Gráficos: drill-down / roll-up, medida y dimensión
    ['g1', 'g2'].forEach(function (g) {
      var card = self.raiz.querySelector('[data-grafico=' + g + ']');
      card.querySelector('[data-accion=drilldown]').addEventListener('click', function () { self.bajarGrafico(g, null); });
      card.querySelector('[data-accion=rollup]').addEventListener('click', function () { self.subirGrafico(g); });
      card.querySelector('[data-medida]').addEventListener('change', function (e) {
        self.estado[g].medida = e.target.value; self.estado.ultima_operacion = 'Cambio de medida'; self.consultar();
      });
      card.querySelector('[data-dim]').addEventListener('change', function (e) {
        self.estado[g] = { dim: e.target.value, medida: self.estado[g].medida };
        self.estado.ultima_operacion = 'Cambio de dimensión del gráfico'; self.consultar();
      });
    });

    // Matriz: pivot, drill, métrica, dimensiones
    var m = this.raiz.querySelector('[data-matriz]');
    m.querySelector('[data-accion=pivot]').addEventListener('click', function () {
      self.estado.matriz.pivot = !self.estado.matriz.pivot; self.estado.ultima_operacion = 'Pivot'; self.consultar();
    });
    m.querySelector('[data-accion=drilldown]').addEventListener('click', function () { self.bajarMatriz(null); });
    m.querySelector('[data-accion=rollup]').addEventListener('click', function () { self.subirMatriz(); });
    m.querySelector('[data-metrica]').addEventListener('change', function (e) {
      self.estado.matriz.metrica = e.target.value; self.estado.ultima_operacion = 'Cambio de métrica'; self.consultar();
    });
    m.querySelector('[data-nivel-columnas]').addEventListener('change', function (e) {
      self.estado.matriz.nivel_columnas = e.target.value; self.estado.ultima_operacion = 'Cambio de nivel de columnas'; self.consultar();
    });
    m.querySelector('[data-dim-filas]').addEventListener('change', function (e) {
      self.estado.matriz = { dim_filas: e.target.value, metrica: self.estado.matriz.metrica, pivot: self.estado.matriz.pivot,
                             dim_columnas: self.estado.matriz.dim_columnas, nivel_columnas: self.estado.matriz.nivel_columnas };
      self.estado.ultima_operacion = 'Cambio de dimensión de filas'; self.consultar();
    });
    m.querySelector('[data-dim-columnas]').addEventListener('change', function (e) {
      self.estado.matriz.dim_columnas = e.target.value; self.estado.matriz.nivel_columnas = null;
      self.estado.ultima_operacion = 'Cambio de dimensión de columnas'; self.consultar();
    });
  };

  Vista.prototype.tipoFiltro = function () {
    var f = this.estado.filtros, dims = 0, valores = 0;
    Object.keys(f).forEach(function (k) { if (f[k] && f[k].length) { dims += 1; valores += f[k].length; } });
    if (dims >= 2) { return 'Dice'; }
    if (dims === 1 && valores === 1) { return 'Slice'; }
    return dims ? 'Selección múltiple' : 'Sin filtros';
  };

  /* ---------------- Operaciones de jerarquía ---------------- */
  Vista.prototype.bajarGrafico = function (g, miembro) {
    var d = this.datos && this.datos[g];
    if (!d || !d.puede_bajar) { return; }
    var e = this.estado[g];
    e.dim = d.dim; e.medida = d.medida;
    e.ruta = (d.ruta || []).slice();
    if (miembro !== null && miembro !== undefined && String(miembro).indexOf('Otros (') !== 0) {
      e.ruta.push({ nivel: d.nivel, valor: miembro });   // drill-down sobre un miembro
    }
    e.nivel = d.nivel_inferior;
    this.estado.ultima_operacion = 'Drill-down';
    this.consultar();
  };

  Vista.prototype.subirGrafico = function (g) {
    var d = this.datos && this.datos[g];
    if (!d || !d.puede_subir) { return; }
    var e = this.estado[g];
    e.dim = d.dim; e.medida = d.medida;
    e.ruta = (d.ruta || []).slice();
    if (e.ruta.length) {
      var paso = e.ruta.pop();          // roll-up: se quita el último miembro elegido
      e.nivel = paso.nivel;
    } else {
      e.nivel = d.nivel_superior;
    }
    this.estado.ultima_operacion = 'Roll-up';
    this.consultar();
  };

  Vista.prototype.bajarMatriz = function (miembro) {
    var d = this.datos && this.datos.matriz;
    if (!d || !d.puede_bajar) { return; }
    var e = this.estado.matriz;
    e.dim_filas = d.dim_filas_base;
    e.ruta_filas = (d.ruta_filas || []).slice();
    if (miembro !== null && miembro !== undefined && String(miembro).indexOf('Otros (') !== 0) {
      e.ruta_filas.push({ nivel: d.nivel_filas_base, valor: miembro });
    }
    e.nivel_filas = d.nivel_inferior;
    this.estado.ultima_operacion = 'Drill-down';
    this.consultar();
  };

  Vista.prototype.subirMatriz = function () {
    var d = this.datos && this.datos.matriz;
    if (!d || !d.puede_subir) { return; }
    var e = this.estado.matriz;
    e.dim_filas = d.dim_filas_base;
    e.ruta_filas = (d.ruta_filas || []).slice();
    if (e.ruta_filas.length) { e.nivel_filas = e.ruta_filas.pop().nivel; } else { e.nivel_filas = d.nivel_superior; }
    this.estado.ultima_operacion = 'Roll-up';
    this.consultar();
  };

  /* ---------------- Consulta ---------------- */
  Vista.prototype.consultar = function () {
    var self = this;
    var error = this.raiz.querySelector('[data-error]');
    this.raiz.classList.add('md-loading');
    return fetch(this.api, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(this.estado)
    }).then(function (r) {
      return r.json().then(function (j) { if (!r.ok) { throw new Error(j.error || 'Error en la consulta'); } return j; });
    }).then(function (datos) {
      self.datos = datos;
      error.hidden = true;
      return cargarChartJs(self.chartUrl).then(function () { self.pintar(); });
    }).catch(function (e) {
      error.hidden = false;
      error.textContent = 'No se pudo actualizar la vista: ' + e.message;
    }).then(function () { self.raiz.classList.remove('md-loading'); });
  };

  /* ---------------- Pintado ---------------- */
  Vista.prototype.pintar = function () {
    this.pintarSeleccion();
    this.pintarKpis();
    this.pintarGrafico('g1');
    this.pintarGrafico('g2');
    this.pintarMatriz();
  };

  Vista.prototype.pintarSeleccion = function () {
    var s = this.datos.seleccion, cont = this.raiz.querySelector('[data-seleccion]');
    cont.textContent = '';
    cont.appendChild(el('strong', {}, 'Selección activa:'));
    s.filtros.forEach(function (f) { cont.appendChild(el('span', { 'class': 'md-chip' }, f)); });
    s.operaciones.forEach(function (o) { cont.appendChild(el('span', { 'class': 'md-chip md-chip--op' }, o)); });
    if (this.estado.ultima_operacion) {
      cont.appendChild(el('span', { 'class': 'md-chip' }, 'Última acción: ' + this.estado.ultima_operacion));
    }
  };

  Vista.prototype.pintarKpis = function () {
    var cont = this.raiz.querySelector('[data-kpis]');
    var colores = ['#232A54', '#2E9C93', '#D9A441'];
    cont.textContent = '';
    this.datos.kpis.forEach(function (k, i) {
      var a = el('article', { 'class': 'md-kpi', style: '--kpi:' + colores[i % 3] });
      a.appendChild(el('span', { 'class': 'md-kpi-label' }, k.etiqueta));
      a.appendChild(el('strong', { 'class': 'md-kpi-value' }, formatear(k.valor, k.formato)));
      a.appendChild(el('span', { 'class': 'md-kpi-detail' }, k.detalle || ''));
      a.appendChild(el('span', { 'class': 'md-kpi-note' }, k.nota));
      cont.appendChild(a);
    });
  };

  function rutaTexto(d, nombreNivel) {
    var partes = (d.ruta || []).map(function (p) { return p.valor; });
    return 'Nivel: ' + nombreNivel + (partes.length ? ' · Ruta: ' + partes.join(' › ') : ' · Ruta: todos los miembros');
  }

  Vista.prototype.pintarGrafico = function (g) {
    var self = this, d = this.datos[g];
    var card = this.raiz.querySelector('[data-grafico=' + g + ']');
    card.querySelector('[data-titulo]').textContent = d.titulo;
    var selMed = card.querySelector('[data-medida]');
    selMed.textContent = '';
    d.medidas.forEach(function (m) { var o = el('option', { value: m.id }, m.nombre); if (m.id === d.medida) { o.selected = true; } selMed.appendChild(o); });
    selMed.hidden = d.medidas.length < 2;
    var selDim = card.querySelector('[data-dim]');
    selDim.textContent = '';
    d.dims.forEach(function (x) { var o = el('option', { value: x.id }, x.nombre); if (x.id === d.dim) { o.selected = true; } selDim.appendChild(o); });
    selDim.hidden = d.dims.length < 2;
    card.querySelector('[data-accion=drilldown]').disabled = !d.puede_bajar;
    card.querySelector('[data-accion=rollup]').disabled = !d.puede_subir;
    var ruta = card.querySelector('[data-ruta]');
    ruta.textContent = '';
    ruta.appendChild(el('b', {}, d.nombre_dim));
    ruta.appendChild(document.createTextNode(' · ' + rutaTexto(d, d.nombre_nivel) + ' · Jerarquía: ' +
      d.jerarquia.map(function (j) { return j.nombre; }).join(' > ')));
    card.querySelector('[data-pie]').textContent = 'Medida: ' + d.nombre_medida +
      (d.formato === 'pct' && d.medida === 'participacion' ? ' (denominador: ' + formatear(d.total_seleccion, 'n') + ' vehículos de la selección)' : '') +
      (d.drill_por_miembro ? '. Haga clic en un elemento para hacer drill-down sobre él.' : '.');
    card.querySelector('[data-sql]').textContent = d.sql;

    var canvas = card.querySelector('canvas');
    if (this.graficos[g]) { this.graficos[g].destroy(); }
    var tipo = d.tipo, horizontal = tipo === 'barh', apilado = tipo === 'stacked' || tipo === 'stacked100';
    var datasets = d.datasets.map(function (ds, i) {
      var color = d.datasets.length > 1 ? COLORES[i % COLORES.length] : (tipo === 'line' ? '#2E9C93' : '#232A54');
      return { label: ds.label, data: ds.data, n: ds.n, backgroundColor: tipo === 'line' ? color : color + 'D9',
               borderColor: color, borderWidth: tipo === 'line' ? 2.5 : 0, pointRadius: tipo === 'line' ? 3 : 0,
               tension: 0.25, spanGaps: true, borderRadius: tipo === 'line' ? 0 : 6, maxBarThickness: 46 };
    });
    var formato = d.formato;
    this.graficos[g] = new window.Chart(canvas, {
      type: tipo === 'line' ? 'line' : 'bar',
      data: { labels: d.etiquetas, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: horizontal ? 'y' : 'x',
        animation: { duration: 250 },
        plugins: {
          legend: { display: d.datasets.length > 1, position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: { callbacks: { label: function (c) {
            var t = c.dataset.label + ': ' + formatear(c.raw, formato);
            if (c.dataset.n && c.dataset.n[c.dataIndex] !== undefined) { t += ' · ' + formatear(c.dataset.n[c.dataIndex], 'n') + ' vehículos'; }
            return t;
          } } }
        },
        scales: (function () {
          var valor = { stacked: apilado, beginAtZero: true, max: tipo === 'stacked100' ? 1 : undefined,
                        ticks: { callback: function (v) { return formato === 'pct' ? Math.round(v * 1000) / 10 + ' %' : nf.format(v); }, font: { size: 11 } },
                        grid: { color: 'rgba(35,42,84,0.08)' } };
          var cat = { stacked: apilado, ticks: { autoSkip: !horizontal, maxRotation: 50, font: { size: 11 },
                      callback: function (v) { var l = this.getLabelForValue(v); return String(l).length > 26 ? String(l).slice(0, 25) + '…' : l; } },
                      grid: { display: false } };
          return horizontal ? { x: valor, y: cat } : { x: cat, y: valor };
        })(),
        onClick: function (evt, elementos) {
          if (!elementos.length || !d.drill_por_miembro) { return; }
          self.bajarGrafico(g, d.etiquetas[elementos[0].index]);
        }
      }
    });
  };

  Vista.prototype.pintarMatriz = function () {
    var self = this, d = this.datos.matriz;
    var cont = this.raiz.querySelector('[data-matriz]');
    cont.querySelector('[data-titulo]').textContent = d.nombre_filas + ' × ' + d.nombre_columnas + ' · ' + d.nombre_metrica;
    function llenar(sel, opciones, actual) {
      sel.textContent = '';
      opciones.forEach(function (o) { var op = el('option', { value: o.id }, o.nombre); if (o.id === actual) { op.selected = true; } sel.appendChild(op); });
      sel.hidden = opciones.length < 2;
    }
    llenar(cont.querySelector('[data-metrica]'), d.metricas, d.metrica);
    llenar(cont.querySelector('[data-dim-filas]'), d.dims_filas, d.dim_filas_base);
    llenar(cont.querySelector('[data-dim-columnas]'), d.dims_columnas, d.dim_columnas_base);
    llenar(cont.querySelector('[data-nivel-columnas]'), d.niveles_columnas, d.nivel_columnas_base);
    cont.querySelector('[data-accion=drilldown]').disabled = !d.puede_bajar;
    cont.querySelector('[data-accion=rollup]').disabled = !d.puede_subir;
    var piv = cont.querySelector('[data-accion=pivot]');
    piv.classList.toggle('md-btn--on', d.pivot);
    piv.setAttribute('aria-pressed', d.pivot ? 'true' : 'false');
    var ruta = cont.querySelector('[data-ruta]');
    ruta.textContent = '';
    ruta.appendChild(el('b', {}, 'Filas: ' + d.nombre_filas + ' · Columnas: ' + d.nombre_columnas));
    var partes = (d.ruta_filas || []).map(function (p) { return p.valor; });
    ruta.appendChild(document.createTextNode((d.pivot ? ' · Pivot activo (ejes intercambiados)' : '') +
      (partes.length ? ' · Ruta de drill-down: ' + partes.join(' › ') : '')));

    var tabla = cont.querySelector('[data-tabla]');
    tabla.textContent = '';
    var max = 0;
    d.valores.forEach(function (fila) { fila.forEach(function (v) { if (v !== null && v > max) { max = v; } }); });
    var thead = el('thead'), trh = el('tr');
    trh.appendChild(el('th', { scope: 'col' }, d.nombre_filas + ' \\ ' + d.nombre_columnas));
    d.columnas.forEach(function (c) { trh.appendChild(el('th', { scope: 'col' }, c)); });
    trh.appendChild(el('th', { scope: 'col' }, 'Total'));
    thead.appendChild(trh);
    tabla.appendChild(thead);
    var tbody = el('tbody');
    var drill = d.puede_bajar && !d.pivot;
    d.filas.forEach(function (f, i) {
      var tr = el('tr');
      var th = el('th', { scope: 'row', title: f });
      if (drill && f.indexOf('Otros (') !== 0) {
        var b = el('button', { type: 'button', title: 'Drill-down en ' + f }, f);
        b.addEventListener('click', function () { self.bajarMatriz(f); });
        th.appendChild(b);
      } else { th.textContent = f; }
      tr.appendChild(th);
      d.valores[i].forEach(function (v, j) {
        var td = el('td', {}, formatear(v, d.formato));
        if (v !== null && max > 0) {
          var a = Math.min(0.55, 0.06 + 0.5 * (v / max));
          td.style.background = 'rgba(46,156,147,' + a.toFixed(3) + ')';
        }
        if (d.formato !== 'n') { td.appendChild(el('small', {}, formatear(d.n[i][j], 'n') + ' veh.')); }
        tr.appendChild(td);
      });
      tr.appendChild(el('td', { 'class': 'md-total' }, formatear(d.total_fila[i], d.formato)));
      tbody.appendChild(tr);
    });
    var trt = el('tr', { 'class': 'md-total' });
    trt.appendChild(el('th', { scope: 'row' }, 'Total'));
    d.total_columna.forEach(function (v) { trt.appendChild(el('td', {}, formatear(v, d.formato))); });
    trt.appendChild(el('td', {}, formatear(d.total_general, d.formato)));
    tbody.appendChild(trt);
    tabla.appendChild(tbody);
    cont.querySelector('[data-pie]').textContent = d.denominador + '. Total de la matriz: ' + formatear(d.n_total, 'n') +
      ' vehículos.' + (drill ? ' Haga clic en el nombre de una fila para hacer drill-down sobre ella.' : '');
    cont.querySelector('[data-sql]').textContent = d.sql;
  };

  /* ---------------- Arranque ---------------- */
  function iniciar() {
    document.querySelectorAll('[data-md-vista]').forEach(function (raiz) {
      if (raiz.__mdVista) { return; }
      raiz.__mdVista = new Vista(raiz);
      raiz.__mdVista.consultar();
    });
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', iniciar); } else { iniciar(); }
})();
