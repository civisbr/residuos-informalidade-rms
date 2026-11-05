// Observatório — painel data-driven. Lê data.json gerado pela pipeline.
let DATA = null,
  COEF = null,
  CITY = null;

const fmt = (n, d = 0) =>
  n == null
    ? "—"
    : Number(n).toLocaleString("pt-BR", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
const $ = (id) => document.getElementById(id);

async function boot() {
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    DATA = await res.json();
  } catch (e) {
    document.querySelector("main, body").insertAdjacentHTML(
      "afterbegin",
      `<div class="err"><b>Não consegui carregar data.json.</b><br>
       Rode <code>uv run obs build</code> e sirva a pasta <code>site/</code> com
       <code>python -m http.server</code> (abrir via file:// bloqueia o fetch).</div>`,
    );
    return;
  }
  COEF = DATA.coeficientes;
  $("regName").textContent = DATA.meta.regiao_nome;
  $("footMeta").textContent =
    `Gerado em ${DATA.meta.gerado_em} · região ${DATA.meta.regiao_key} · baseline: ${DATA.meta.fonte_baseline} · v0.1`;
  $("caveat").innerHTML =
    `<b>Leia antes de usar externamente.</b> ${DATA.meta.aviso} Os números de catadores
     informais são subcontados pelas bases oficiais — trate como piso, não total.`;
  buildAssumptions();
  buildRegionStrip();
  buildRegionDetail();
  buildCitySelect();
  wireSimulator();

  const d = DATA.simulador_defaults;
  $("sCli").value = d.clientes;
  $("sKg").value = d.kg_dia;
  $("sSh").value = d.partilha_pct;
  $("sFee").value = d.gate_fee;

  selectCity("");
  wireRegionViews();
}

function buildAssumptions() {
  const c = COEF;
  $("assumpBody").innerHTML =
    `Fração orgânica do RSU: <code>${c.composicao.organico * 100}%</code> (substituir pela gravimetria do PMGIRS).<br>
     Conversão BSF (larva úmida): <code>${c.bsf.conversao_larva_umida * 100}%</code> ·
     larva seca <code>${c.bsf.larva_seca_sobre_umida * 100}%</code> · frass <code>${c.bsf.frass_sobre_organico * 100}%</code>.<br>
     CO₂e evitado: <code>${c.clima.co2e_por_t_organico} t</code> por t de orgânico desviada.<br>
     Renda-alvo catador: <code>R$ ${fmt(c.operacao.renda_alvo_catador_mes)}</code>/mês.<br>
     Coeficientes conservadores — calibre com dados locais antes de publicar.`;
}

function buildRegionStrip() {
  const t = DATA.totais;
  const mil = (v) =>
    v != null ? `${fmt(v / 1000, 1)} <small>mil t/ano</small>` : "—";
  const cards = [
    [`${t.municipios_total}`, "municípios no painel", "Cobertura territorial"],
    [
      mil(t.rsu_t_ano),
      "resíduos coletados",
      "Soma das bases disponíveis • anos distintos",
    ],
    [
      mil(t.organico_t_ano),
      "orgânicos estimados",
      "Composição estimada • não é pesagem",
    ],
    [
      `${fmt(t.cooperados)}`,
      "cooperados registrados",
      "Cobertura parcial • não é total de catadores",
    ],
  ];
  $("regionStrip").innerHTML = cards
    .map(
      ([v, l, n], i) =>
        `<div class="kpi4c"><span class="k4-icon">${[`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 6-8 13-8 13S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`, `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M9 3h6M6 6l1 16h10l1-16M10 10v8M14 10v8"/></svg>`, `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4C9 2 3 9 5 16c7 4 15-1 15-12Z"/><path d="M3 22 16 9"/></svg>`, `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="7" r="3"/><circle cx="18" cy="9" r="2.5"/><path d="M2 21v-3a7 7 0 0 1 14 0v3ZM17 15c4 0 6 2 6 6"/></svg>`][i]}</span><div class="k4-v mono">${v}</div><div class="k4-l">${l}</div><div class="k4-n">${n}</div></div>`,
    )
    .join("");
}

// Painel "Explore sua região": chips de municípios + barras de destino (totais).
function buildRegionDetail() {
  const t = DATA.totais;
  $("munList").innerHTML = DATA.municipios
    .map(
      (m) =>
        `<button class="munchip" data-mun="${m.nome}"><span class="dot ${m.flag}"></span>${m.nome}</button>`,
    )
    .join("");
  $("munList")
    .querySelectorAll("button")
    .forEach((b) =>
      b.addEventListener("click", () => selectCity(b.dataset.mun)),
    );

  const dest = [
    ["Aterro", t.aterro_t_ano, "aterro"],
    ["Reciclagem", t.reciclado_t_ano, "recic"],
    ["Orgânicos: potencial estimado", t.organico_t_ano, "org"],
  ];
  const max = Math.max(1, ...dest.map(([, v]) => v || 0));
  $("destBars").innerHTML = dest
    .map(
      ([l, v, cls]) =>
        `<div class="drow"><span class="dlab">${l}</span>
     <div class="dbar"><div class="dfill ${cls}" style="width:${(((v || 0) / max) * 100).toFixed(1)}%"></div></div>
     <span class="dval mono">${v != null ? "~" + fmt(v / 1000, 1) + " mil t/ano" : "—"}</span></div>`,
    )
    .join("");
}

function markActiveChip() {
  document
    .querySelectorAll("#munList .munchip")
    .forEach((b) =>
      b.classList.toggle("on", CITY && b.dataset.mun === CITY.nome),
    );
}

function buildCitySelect() {
  const subs = {};
  DATA.municipios.forEach((m) => {
    const k = m.subregiao ?? "null";
    (subs[k] = subs[k] || []).push(m);
  });
  const somenteNull = Object.keys(subs).every((k) => k === "null");
  const keys = Object.keys(subs).sort((a, b) =>
    a === "null" ? 1 : b === "null" ? -1 : Number(a) - Number(b),
  );
  const flag = (m) =>
    m.flag === "real" ? " ✓" : m.flag === "estimativa" ? " ~" : " ⊘";
  let html = `<option value="">Todos os ${DATA.municipios.length} municípios</option>`;
  for (const sr of keys) {
    if (!subs[sr].length) continue;
    const lbl =
      sr === "null"
        ? somenteNull
          ? "Municípios"
          : "Outros"
        : `Sub-região ${sr}`;
    html +=
      `<optgroup label="${lbl}">` +
      subs[sr]
        .map((m) => `<option value="${m.nome}">${m.nome}${flag(m)}</option>`)
        .join("") +
      `</optgroup>`;
  }
  $("citySel").innerHTML = html;
  $("citySel").addEventListener("change", (e) => selectCity(e.target.value));
}

function selectCity(nome) {
  CITY = DATA.municipios.find((m) => m.nome === nome) || null;
  $("citySel").value = CITY ? CITY.nome : "";
  $("cityDetail").hidden = !CITY;
  $("infDetail").hidden = !CITY;
  $("popline").textContent = CITY
    ? CITY.populacao
      ? `pop. ~${fmt(CITY.populacao)} hab`
      : "população a levantar"
    : "";
  if (CITY) {
    $("cityName").textContent = CITY.nome;
    renderFlow();
    renderKpis();
    renderInformalidade();
  }
  renderOperacao();
  recalc();
  markActiveChip();
}

function wireRegionViews() {
  const toggleView = (map) => {
    $("regionMap").hidden = !map;
    $("munList").hidden = map;
    $("mapTab").setAttribute("aria-pressed", String(map));
    $("listTab").setAttribute("aria-pressed", String(!map));
  };
  $("mapTab").addEventListener("click", () => toggleView(true));
  $("listTab").addEventListener("click", () => toggleView(false));
  document
    .querySelectorAll("[data-city]")
    .forEach((button) =>
      button.addEventListener("click", () => selectCity(button.dataset.city)),
    );
  const links = [...document.querySelectorAll(".side-nav a")];
  links.forEach((link) =>
    link.addEventListener("click", () => {
      links.forEach((a) => a.classList.toggle("active", a === link));
      if (link.hash === "#municipios") toggleView(false);
    }),
  );
}

// Série temporal SVG inline à mão (D-10) — zero dependência. Desenha duas
// linhas (real sólido × projetado tracejado) sobre o mesmo eixo. Pontos null
// quebram a linha honestamente (mês sem dado nunca vira zero — regra sagrada).
function svgSerie(serie, campoReal, campoProj) {
  const W = 720,
    H = 240,
    P = 40;
  if (!serie.length) return "";
  const ys = serie.flatMap((d) =>
    [d[campoReal], d[campoProj]].filter((v) => v != null),
  );
  const yMax = Math.max(1, ...ys);
  const x = (i) => P + (i * (W - 2 * P)) / Math.max(1, serie.length - 1);
  const y = (v) => H - P - (v / yMax) * (H - 2 * P);
  const path = (campo) =>
    serie
      .map((d, i) =>
        d[campo] == null
          ? null
          : `${x(i).toFixed(1)},${y(d[campo]).toFixed(1)}`,
      )
      .filter(Boolean)
      .join(" ");
  const xlabs = serie
    .map(
      (d, i) =>
        `<text x="${x(i).toFixed(1)}" y="${H - P + 16}" class="xlab">${d.mes.slice(2)}</text>`,
    )
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="serie" role="img"
            aria-label="Série temporal: medição real (sólido) vs projeção do modelo (tracejado)">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" class="axis"/>
    <line x1="${P}" y1="${P}" x2="${P}" y2="${H - P}" class="axis"/>
    <text x="${P}" y="${P - 12}" class="ymax">máx ~${fmt(yMax, 2)} t/mês</text>
    <polyline points="${path(campoProj)}" class="s-proj" fill="none"/>
    <polyline points="${path(campoReal)}" class="s-real" fill="none"/>
    ${xlabs}
  </svg>`;
}

function renderOperacao() {
  const op = DATA.operacao;
  if (!op || !op.tem_dado) {
    // Estado vazio honesto (D-02): operação ainda não roda — nunca telemetria fabricada.
    $("opSlot").innerHTML = "";
    return;
  }
  // COM dado: série real×projetado + 4 cards de impacto acumulado (D-09/D-10/D-11).
  const a = op.acumulados || {};
  const cards = [
    [
      "c1",
      "DESVIO DE ATERRO ACUMULADO",
      fmt(a.desviado_t, 1),
      "t",
      "orgânico medido fora do aterro desde o início da operação.",
    ],
    [
      "c4",
      "RENDA A CATADORES ACUMULADA",
      "R$ " + fmt(a.partilha_rs / 1000, 1),
      "mil",
      "repassado ao fundo de partilha — conecta com a informalidade da região.",
    ],
    [
      "c2",
      "CO₂e EVITADO",
      fmt(a.co2e_evitado_t_derivado, 1),
      "t",
      `<b>derivado</b> do desvio real (~${fmt(a.carros_equivalente_derivado, 1)} carros/ano, ilustrativo).`,
    ],
    [
      "c3",
      "BIOCONVERSÃO ACUMULADA",
      fmt(a.larva_seca_t, 2),
      "t larva seca",
      `+ <b>${fmt(a.frass_t, 1)} t</b> de frass (biofertilizante) medidos.`,
    ],
  ];
  const cardsHtml = cards
    .map(
      ([cls, lab, val, u, sub]) =>
        `<div class="ocard ${cls}"><div class="o-lab">${lab}</div>
       <div class="o-val mono">${val} <small>${u}</small></div>
       <div class="o-sub">${sub}</div></div>`,
    )
    .join("");

  $("opSlot").innerHTML = `
    <div class="opwrap">
      <div class="op-head">
        <div class="op-title">Bioconversão medida × projetada — base mensal
          <span class="tag live">medição da operação</span></div>
        <div class="op-leg">
          <span><i class="ll-real"></i> medido (real)</span>
          <span><i class="ll-proj"></i> projetado pelo modelo</span>
        </div>
      </div>
      ${svgSerie(op.serie, "real_larva_seca_t", "projetado_larva_seca_t")}
      <div class="op-cap">Linha cheia = pesagem real de larva seca. Tracejado =
        o que o modelo (mesmos coeficientes do simulador) projetaria para o
        orgânico desviado de cada mês. Mês sem medição quebra a linha — nunca é zero.</div>
      <div class="out op-cards">${cardsHtml}</div>
    </div>`;
}

function renderFlow() {
  const c = CITY,
    comp = COEF.composicao;
  if (c.rsu_t_ano == null) {
    $("flowTags").innerHTML = `<span class="tag pend">pendente</span>`;
    $("flowSlot").innerHTML =
      `<div class="pendbox"><b>${c.nome} ainda não tem dado público carregado.</b>
       Extraia do SNIS / PMGIRS e rode <code>uv run obs build</code>.
       ${c.fonte ? "<br><span class='mono' style='font-size:12px'>" + c.fonte + "</span>" : ""}</div>`;
    return;
  }
  const tag =
    c.flag === "estimativa"
      ? `<span class="tag est">estimativa</span>`
      : `<span class="tag real">dado público</span>`;
  $("flowTags").innerHTML =
    tag + ` <span class="tag est">composição estimada</span>`;

  const gen = c.rsu_t_ano,
    org = gen * comp.organico,
    rec = gen * comp.reciclavel_seco,
    rej = gen * comp.rejeito;
  const recPct = c.reciclado_pct,
    recT = c.reciclado_t_ano;
  $("flowSlot").innerHTML = `
    <div class="flowwrap">
      <div class="flow-top">
        <div class="flow-total"><span class="n mono">${fmt(gen)}</span><span class="u">t / ano de RSU</span></div>
        <div class="flow-cap">~${fmt(gen / 365)} t/dia. A largura de cada faixa é a fração estimada do fluxo.</div>
      </div>
      <div class="bar">
        <div class="seg organic" style="flex-basis:${comp.organico * 100}%"><span class="sv">${fmt(org)} t</span><span class="sl">orgânico</span></div>
        <div class="seg recic" style="flex-basis:${comp.reciclavel_seco * 100}%"><span class="sv">${fmt(rec)} t</span><span class="sl">reciclável seco</span></div>
        <div class="seg rejeito" style="flex-basis:${comp.rejeito * 100}%"><span class="sv">${fmt(rej)} t</span><span class="sl">rejeito</span></div>
      </div>
      <div class="legend">
        <span><i style="background:var(--organic)"></i> orgânico — alimento do BSF</span>
        <span><i style="background:var(--recic)"></i> reciclável seco — cadeia dos catadores</span>
        <span><i style="background:var(--rejeito)"></i> rejeito</span>
      </div>
      <div class="fate">
        <div>recuperado hoje<b class="bad">${recPct != null ? "~" + fmt(recPct, 1) + "%" : "—"}</b>
          <span class="mono">${recT != null ? "~" + fmt(recT) + " t/ano" : "dado a levantar"}</span></div>
        <div>vai pro aterro<b class="bad">${recPct != null ? "~" + fmt(100 - recPct, 1) + "%" : "—"}</b>
          <span class="mono">${c.aterro_t_ano != null ? "~" + fmt(c.aterro_t_ano) + " t/ano" : "dado a levantar"}</span></div>
        <div>coleta seletiva<b>${c.coleta_seletiva_pop_pct != null ? fmt(c.coleta_seletiva_pop_pct, 1) + "%" : "—"}</b><span class="mono">da população</span></div>
        <div>custo municipal<b>${c.custo_mensal_rs != null ? "R$ " + fmt(c.custo_mensal_rs / 1e6, 1) + " mi" : "—"}</b><span class="mono">/mês · coleta+aterro</span></div>
      </div>
    </div>`;
}

function renderKpis() {
  const c = CITY;
  const tag = (f) =>
    f === "real"
      ? `<span class="tag real">real</span>`
      : f === "estimativa"
        ? `<span class="tag est">estim.</span>`
        : `<span class="tag pend">pendente</span>`;
  const cell = (lab, val, u, note, f) =>
    `<div class="kpi${f === "pendente" ? " pend" : ""}">
       <div class="k-lab">${lab} ${tag(f)}</div>
       <div class="k-val mono">${val}<small>${u}</small></div>
       <div class="k-note">${note}</div></div>`;
  const has = c.rsu_t_ano != null;
  const f = c.flag;
  $("kpis").innerHTML = [
    cell(
      "Geração de RSU",
      has ? fmt(c.rsu_t_ano) : "—",
      has ? " t/ano" : "",
      has ? `~${fmt(c.rsu_t_ano / 365)} t/dia` : "extrair do SNIS",
      f,
    ),
    cell(
      "Reciclado",
      c.reciclado_pct != null ? "~" + fmt(c.reciclado_pct, 1) : "—",
      c.reciclado_pct != null ? "%" : "",
      c.reciclado_t_ano != null
        ? `~${fmt(c.reciclado_t_ano)} t/ano`
        : "a levantar",
      c.reciclado_pct != null ? f : "pendente",
    ),
    cell(
      "Cooperados",
      c.cooperados != null ? "~" + fmt(c.cooperados) : "—",
      "",
      c.cooperados != null ? "em cooperativas" : "a levantar",
      c.cooperados != null ? f : "pendente",
    ),
    cell(
      "Coleta seletiva",
      c.coleta_seletiva_pop_pct != null
        ? fmt(c.coleta_seletiva_pop_pct, 1)
        : "—",
      c.coleta_seletiva_pop_pct != null ? "%" : "",
      "cobertura da população",
      c.coleta_seletiva_pop_pct != null ? f : "pendente",
    ),
    cell(
      "Custo coleta+aterro",
      c.custo_mensal_rs != null ? "R$" + fmt(c.custo_mensal_rs / 1e6, 1) : "—",
      c.custo_mensal_rs != null ? " mi/mês" : "",
      "convencional + disposição",
      c.custo_mensal_rs != null ? f : "pendente",
    ),
    cell(
      "Orgânico ao aterro",
      has ? "~" + fmt(c.organico_t_ano / 1000, 1) : "—",
      has ? " mil t/ano" : "",
      `fração orgânica (${COEF.composicao.organico * 100}%)`,
      has ? "estimativa" : "pendente",
    ),
  ].join("");
}

function renderInformalidade() {
  const c = CITY;
  const tag = (f) =>
    f === "real"
      ? `<span class="tag real">real</span>`
      : f === "estimativa"
        ? `<span class="tag est">estim.</span>`
        : `<span class="tag pend">pendente</span>`;
  const cell = (lab, val, u, note, f) =>
    `<div class="kpi${f === "pendente" ? " pend" : ""}">
       <div class="k-lab">${lab} ${tag(f)}</div>
       <div class="k-val mono">${val}<small>${u}</small></div>
       <div class="k-note">${note}</div></div>`;

  $("infTags").innerHTML =
    `<span class="tag real">Censo 2022</span> <span class="tag real">RAIS 2023</span>`;

  const flagInf = c.flag_informalidade || "pendente";
  const taxaVal =
    c.taxa_informalidade_pct != null
      ? fmt(c.taxa_informalidade_pct, 1) + " %"
      : "—";
  const taxaNota =
    c.taxa_informalidade_pct != null
      ? fmt(c.informais) +
        " de " +
        fmt(c.total_ocupados) +
        " ocupados (Censo 2022)"
      : "a levantar";

  const flagFormais = c.formais_residuos != null ? "real" : "pendente";
  const formaisVal = c.formais_residuos != null ? fmt(c.formais_residuos) : "—";

  const flagProxy = c.flag_proxy || "pendente";
  const proxyVal =
    c.proxy_formalizacao != null
      ? (c.proxy_formalizacao * 100).toFixed(1) + "%"
      : "—";
  const proxyNota =
    c.proxy_formalizacao != null
      ? fmt(c.formais_residuos) +
        " formais + " +
        fmt(c.cooperados || 0) +
        " cooperados"
      : "sem dado suficiente (D-07)";

  $("kpisInf").innerHTML = [
    cell("Taxa de informalidade", taxaVal, "", taxaNota, flagInf),
    cell(
      "Empregos formais — setor resíduos",
      formaisVal,
      "",
      "RAIS 2023 · CNAEs 3811–3900",
      flagFormais,
    ),
    cell("Grau de formalização", proxyVal, "", proxyNota, flagProxy),
  ].join("");

  $("infSubcount").innerHTML =
    `<b>Nota sobre subcontagem de catadores:</b> As bases oficiais (SNIS e Censo 2022)
     subcontam a população catadora informal — trate os números como piso, não total.
     O catador que não está em cooperativa nem em vínculo formal registrado não aparece
     nestas estatísticas.`;

  const pnad = DATA.meta.pnad_contexto_regional;
  if (pnad) {
    $("pnadRegional").innerHTML =
      `<div class="caveat" style="margin-top:8px">Contexto regional
       <span class="tag est" style="margin:0 4px">estimativa</span>
       Estado de SP (estimativa regional), ${pnad.periodo} —
       taxa de informalidade ${fmt(pnad.taxa_informalidade_pct, 1)}%
       (fonte: PNAD Contínua)</div>`;
  } else {
    $("pnadRegional").innerHTML = "";
  }
}

// ---- simulador: espelha pipeline/model.py ----
function project(clientes, kgDia, partilhaPct, gateFee, organicoMunicipal) {
  const b = COEF.bsf,
    cl = COEF.clima,
    op = COEF.operacao;
  const desviado = ((clientes * kgDia) / 1000) * 365;
  const co2e = desviado * cl.co2e_por_t_organico;
  const larvaSeca =
    desviado * b.conversao_larva_umida * b.larva_seca_sobre_umida;
  const frass = desviado * b.frass_sobre_organico;
  const receita = clientes * gateFee * 12;
  const fundo = (receita * partilhaPct) / 100;
  const catadores = fundo / (op.renda_alvo_catador_mes * 12);
  const pctOrg = organicoMunicipal
    ? (desviado / organicoMunicipal) * 100
    : null;
  return {
    desviado,
    co2e,
    carros: co2e / cl.co2e_por_carro_ano,
    larvaSeca,
    frass,
    receita,
    fundo,
    catadores,
    pctOrg,
  };
}

function recalc() {
  const cli = +$("sCli").value,
    kg = +$("sKg").value,
    sh = +$("sSh").value,
    fee = +$("sFee").value;
  $("vCli").textContent = cli;
  $("vKg").textContent = kg;
  $("vSh").textContent = sh;
  $("vFee").textContent = fmt(fee);
  const be = COEF.operacao.break_even_clientes;
  $("hCli").textContent =
    cli < be
      ? `abaixo do equilíbrio estimado (${be})`
      : cli === be
        ? `${be} = ponto de equilíbrio estimado da Fase 1`
        : `${cli - be} clientes acima do equilíbrio`;

  const orgMun = CITY ? CITY.organico_t_ano : DATA.totais.organico_t_ano;
  const r = project(cli, kg, sh, fee, orgMun);

  $("oDiv").textContent = fmt(r.desviado);
  $("oDivSub").innerHTML =
    r.pctOrg != null
      ? `equivale a <b>${fmt(r.pctOrg, 1)}%</b> do orgânico ${CITY ? "municipal" : "regional"} estimado.`
      : `selecione um município com dado de RSU para ver o % do orgânico local.`;
  $("oCO2").textContent = fmt(r.co2e);
  $("oCars").textContent = fmt(r.carros);
  $("oFrass").textContent = fmt(r.frass);
  $("oLarva").textContent = fmt(r.larvaSeca) + " t/ano";
  $("oCat").textContent = fmt(r.catadores, 1);
  $("oPool").textContent = "R$ " + fmt(r.fundo / 12) + "/mês";
  $("rev").textContent = "R$ " + fmt(r.receita / 12) + "/mês";
}

function wireSimulator() {
  ["sCli", "sKg", "sSh", "sFee"].forEach((id) =>
    $(id).addEventListener("input", recalc),
  );
}

boot();
