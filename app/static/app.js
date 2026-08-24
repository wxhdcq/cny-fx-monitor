const PIN_STORAGE_KEY = "cny-fx-monitor:pinned-v1";
const state = {
  filter: "all",
  query: "",
  rates: [],
  pinned: loadPinned(),
  historyCache: new Map(),
};
const filterTitles = {
  all: "全部汇率",
  major: "主流货币",
  "low-price": "订阅低价区",
  "high-risk": "风险观察名单",
};

const $ = (selector) => document.querySelector(selector);

function loadPinned() {
  try {
    const value = JSON.parse(localStorage.getItem(PIN_STORAGE_KEY) || "[]");
    return new Set(Array.isArray(value) ? value.filter((item) => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

function savePinned() {
  try {
    localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify([...state.pinned]));
  } catch {
    // 隐私模式或禁用存储时仍允许当前页面临时置顶。
  }
}

function formatRate(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value >= 1000) return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  if (value >= 100) return value.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
  if (value >= 1) {
    return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 6 });
  }
  return value.toLocaleString("zh-CN", { minimumSignificantDigits: 3, maximumSignificantDigits: 6 });
}

function formatChange(value, compact = false) {
  if (value === null || value === undefined) {
    return `<span class="change muted">${compact ? "—" : "数据积累中"}</span>`;
  }
  const cls = value > 0 ? "up" : value < 0 ? "down" : "muted";
  const prefix = value > 0 ? "+" : "";
  return `<span class="change ${cls}">${prefix}${value.toFixed(2)}%</span>`;
}

function formatTime(iso) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}

function formatShortDate(value) {
  return new Intl.DateTimeFormat("zh-CN", { year: "2-digit", month: "2-digit", day: "2-digit" }).format(value);
}

const riskLabel = (score) =>
  score >= 70 ? ["高风险", "high"] : score >= 30 ? ["关注", "medium"] : ["正常", ""];

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2200);
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

async function loadData(showToast = false) {
  const refresh = $("#refresh-button");
  refresh.classList.add("spinning");
  try {
    const [summary, rates] = await Promise.all([getJson("api/summary"), getJson("api/rates")]);
    state.rates = rates.items;
    renderSummary(summary);
    populateCurrencyOptions();
    renderConverter();
    renderTable();
    if (showToast) toast("看板已刷新");
  } catch (error) {
    $("#rates-body").innerHTML = `<tr><td colspan="8"><div class="loading">无法加载数据：${error.message}</div></td></tr>`;
    $("#health-label").textContent = "连接异常";
    $("#source-dot").className = "status-dot error";
    if (showToast) toast("刷新失败，请检查服务状态");
  } finally {
    refresh.classList.remove("spinning");
  }
}

function renderSummary(data) {
  $("#currency-count").textContent = data.currency_count || "—";
  $("#risk-count").textContent = data.high_risk_count || "0";
  $("#alert-count").textContent = data.open_alerts || "0";
  $("#health-label").textContent = data.source.status === "healthy" ? "运行正常" : "初始化中";
  $("#source-status").textContent = data.source.status === "healthy" ? "数据源正常" : "等待首次同步";
  $("#source-dot").className = `status-dot ${data.source.status === "healthy" ? "healthy" : "pending"}`;
  $("#updated-text").textContent = data.last_updated
    ? `数据日期 ${formatTime(data.last_updated)} · 自动监测中`
    : "首次数据同步正在进行，请稍候刷新";
  if (data.top_drops.length) {
    const item = data.top_drops[0];
    $("#risk-message").textContent = `${item.code} 当前为 24 小时变动最低（${item.change_1d.toFixed(2)}%）。`;
  }
}

function converterCurrencies() {
  return [
    { code: "CNY", name_zh: "人民币", name_en: "Chinese Yuan", flag: "🇨🇳", flag_code: "cn", value_cny: 1 },
    ...state.rates,
  ];
}

function flagAssetUrl(flagCode) {
  return flagCode ? `static/flags/${flagCode}.svg` : null;
}

function flagMarkup(item, className) {
  const assetUrl = flagAssetUrl(item.flag_code);
  return assetUrl
    ? `<img class="${className}" src="${assetUrl}" alt="" loading="lazy">`
    : `<span class="${className} flag-fallback" aria-hidden="true">${item.flag || "🌐"}</span>`;
}

function updateConverterSelectFlags() {
  const currencies = converterCurrencies();
  [$("#from-currency"), $("#to-currency")].forEach((select) => {
    const item = currencies.find((currency) => currency.code === select.value);
    const assetUrl = flagAssetUrl(item?.flag_code);
    select.style.setProperty("--flag-image", item?.flag_code ? `url(\"flags/${item.flag_code}.svg\")` : "none");
    select.classList.toggle("has-flag", Boolean(assetUrl));
  });
}

function populateCurrencyOptions() {
  const fromSelect = $("#from-currency");
  const toSelect = $("#to-currency");
  const previousFrom = fromSelect.value || "CNY";
  const previousTo = toSelect.value || "USD";
  const currencies = converterCurrencies().sort((a, b) => a.code.localeCompare(b.code));
  const options = currencies
    .map((item) => `<option value="${item.code}">${item.flag_code ? item.code : `${item.flag || "🌐"} ${item.code}`}</option>`)
    .join("");
  fromSelect.innerHTML = options;
  toSelect.innerHTML = options;
  fromSelect.value = currencies.some((item) => item.code === previousFrom) ? previousFrom : "CNY";
  toSelect.value = currencies.some((item) => item.code === previousTo) ? previousTo : "USD";
  updateConverterSelectFlags();
}

function renderConverter() {
  updateConverterSelectFlags();
  const amount = Number.parseFloat($("#convert-amount").value);
  const currencies = converterCurrencies();
  const from = currencies.find((item) => item.code === $("#from-currency").value);
  const to = currencies.find((item) => item.code === $("#to-currency").value);
  if (!from || !to || !Number.isFinite(amount) || amount < 0) {
    $("#converted-value").textContent = "—";
    $("#conversion-rate").textContent = "请输入有效的非负金额";
    return;
  }
  const result = (amount * from.value_cny) / to.value_cny;
  const unitRate = from.value_cny / to.value_cny;
  $("#converted-value").textContent = formatRate(result);
  $("#conversion-rate").textContent = `1 ${from.code} = ${formatRate(unitRate)} ${to.code} · 参考价自动换算`;
}

function filteredRows() {
  const query = state.query.trim().toLocaleLowerCase();
  const flag = {
    major: "is_major",
    "low-price": "is_low_price",
    "high-risk": "is_high_risk",
  }[state.filter];
  return state.rates
    .filter(
      (item) =>
        (!flag || item[flag]) &&
        (!query || `${item.code} ${item.name_zh} ${item.name_en}`.toLocaleLowerCase().includes(query)),
    )
    .sort((a, b) => {
      if (state.filter === "all") {
        const pinDifference = Number(state.pinned.has(b.code)) - Number(state.pinned.has(a.code));
        if (pinDifference) return pinDifference;
      }
      return Number(b.is_major) - Number(a.is_major) || a.code.localeCompare(b.code);
    });
}

function renderTable() {
  const rows = filteredRows();
  $("#table-title").textContent = filterTitles[state.filter];
  $("#result-count").textContent = `显示 ${rows.length} 种货币`;
  $("#pin-summary").textContent = state.pinned.size
    ? `已置顶 ${state.pinned.size} 种货币 · 置顶仅保存在当前浏览器`
    : "点击星标可将常用货币置顶";
  if (!rows.length) {
    $("#rates-body").innerHTML = '<tr><td colspan="8"><div class="loading">没有匹配的货币</div></td></tr>';
    return;
  }
  $("#rates-body").innerHTML = rows
    .map((item) => {
      const [label, cls] = riskLabel(item.risk_score);
      const pinned = state.pinned.has(item.code);
      return `<tr data-code="${item.code}" class="${pinned ? "pinned-row" : ""}">
        <td><div class="currency-cell">${flagMarkup(item, "currency-icon")}<span class="currency-name"><strong>${item.code} · ${item.name_zh || item.name_en}</strong><small>${item.name_en}</small></span></div></td>
        <td><span class="rate-value">¥ ${formatRate(item.value_cny)}</span></td>
        <td>${formatChange(item.change_1d, true)}</td>
        <td>${formatChange(item.change_90d, true)}</td>
        <td>${formatChange(item.change_180d, true)}</td>
        <td>${formatChange(item.change_365d, true)}</td>
        <td><span class="risk-badge ${cls}">${label} ${item.risk_score}</span></td>
        <td><button class="pin-button ${pinned ? "active" : ""}" data-pin="${item.code}" aria-label="${pinned ? "取消置顶" : "置顶"} ${item.code}" title="${pinned ? "取消置顶" : "置顶"}">${pinned ? "★" : "☆"}</button></td>
      </tr>`;
    })
    .join("");
  document.querySelectorAll("tr[data-code]").forEach((row) =>
    row.addEventListener("click", () => openCurrency(row.dataset.code)),
  );
  document.querySelectorAll("[data-pin]").forEach((button) =>
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePinned(button.dataset.pin);
    }),
  );
}

function togglePinned(code) {
  if (state.pinned.has(code)) {
    state.pinned.delete(code);
    toast(`${code} 已取消置顶`);
  } else {
    state.pinned.add(code);
    toast(`${code} 已置顶到市场总览`);
  }
  savePinned();
  renderTable();
  const modalPin = $("[data-dialog-pin]");
  if (modalPin?.dataset.dialogPin === code) {
    modalPin.textContent = state.pinned.has(code) ? "★ 已置顶" : "☆ 置顶";
    modalPin.classList.toggle("active", state.pinned.has(code));
  }
}

async function openCurrency(code) {
  const item = state.rates.find((rate) => rate.code === code);
  if (!item) return;
  renderCurrencyDetail(item);
  $("#currency-dialog").showModal();
  try {
    if (!state.historyCache.has(code)) {
      const history = await getJson(`api/rates/${code}/history?days=370`);
      state.historyCache.set(code, history.points);
    }
    renderHistoryChart(item, state.historyCache.get(code), 365);
  } catch (error) {
    $("#history-chart").innerHTML = `<div class="chart-empty">历史数据加载失败：${error.message}</div>`;
  }
}

function renderCurrencyDetail(item) {
  const [label] = riskLabel(item.risk_score);
  const pinned = state.pinned.has(item.code);
  $("#dialog-content").innerHTML = `
    <div class="detail-header">
      <div class="detail-identity">${flagMarkup(item, "detail-flag")}<div><span class="detail-kicker">${item.is_high_risk ? "RISK WATCH" : "CURRENCY DETAIL"}</span><h2 class="detail-title">${item.code} · ${item.name_zh || item.name_en}</h2><p class="subtitle">${item.name_en}</p></div></div>
      <button class="dialog-pin ${pinned ? "active" : ""}" data-dialog-pin="${item.code}">${pinned ? "★ 已置顶" : "☆ 置顶"}</button>
    </div>
    <div class="detail-rate"><span>1 ${item.code} 当前参考价值</span><strong>¥ ${formatRate(item.value_cny)}</strong><small>${formatTime(item.observed_at)}</small></div>
    <div class="detail-meta long-term-meta">
      <div><span>3 个月</span><strong>${formatChange(item.change_90d, true)}</strong></div>
      <div><span>6 个月</span><strong>${formatChange(item.change_180d, true)}</strong></div>
      <div><span>1 年</span><strong>${formatChange(item.change_365d, true)}</strong></div>
      <div><span>风险等级</span><strong>${label} · ${item.risk_score}</strong></div>
    </div>
    <section class="history-section">
      <div class="history-head"><div><span>历史参考汇率</span><strong>${item.code} / CNY</strong></div><div class="range-tabs"><button data-range="90">3个月</button><button data-range="180">6个月</button><button data-range="365" class="active">1年</button></div></div>
      <div id="history-chart"><div class="chart-empty">正在加载历史曲线…</div></div>
    </section>
    <p class="detail-note">来源：${item.source}。央行日度参考数据不代表银行、银行卡或订阅平台实际成交价。</p>`;
  $("[data-dialog-pin]").addEventListener("click", () => togglePinned(item.code));
}

function renderHistoryChart(item, allPoints, days) {
  const points = allPoints
    .map((point) => ({ ...point, date: new Date(point.time) }))
    .sort((a, b) => a.date - b.date);
  const latestDate = points.at(-1)?.date;
  const cutoff = latestDate ? new Date(latestDate.getTime() - days * 86400000) : null;
  const visible = cutoff ? points.filter((point) => point.date >= cutoff) : [];
  if (visible.length < 2) {
    $("#history-chart").innerHTML = '<div class="chart-empty">该周期历史数据不足</div>';
    return;
  }

  const width = 720;
  const height = 250;
  const padding = { left: 48, right: 18, top: 20, bottom: 34 };
  const values = visible.map((point) => point.value);
  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  if (minimum === maximum) {
    minimum *= 0.995;
    maximum *= 1.005;
  }
  const margin = (maximum - minimum) * 0.08;
  minimum -= margin;
  maximum += margin;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const x = (index) => padding.left + (index / (visible.length - 1)) * plotWidth;
  const y = (value) => padding.top + ((maximum - value) / (maximum - minimum)) * plotHeight;
  const linePath = visible
    .map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(2)},${y(point.value).toFixed(2)}`)
    .join(" ");
  const baseline = height - padding.bottom;
  const areaPath = `${linePath} L${x(visible.length - 1).toFixed(2)},${baseline} L${x(0).toFixed(2)},${baseline} Z`;
  const first = visible[0];
  const last = visible.at(-1);
  const periodChange = ((last.value - first.value) / first.value) * 100;

  $("#history-chart").innerHTML = `
    <div class="chart-summary"><span>${days === 90 ? "3个月" : days === 180 ? "6个月" : "1年"}变动 ${formatChange(periodChange, true)}</span><span>区间低点 ¥${formatRate(Math.min(...values))}</span><span>区间高点 ¥${formatRate(Math.max(...values))}</span></div>
    <div class="chart-canvas">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${item.code} 最近${days}天兑人民币历史曲线">
        <defs><linearGradient id="chart-area-${item.code}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b6b4f" stop-opacity=".24"/><stop offset="1" stop-color="#0b6b4f" stop-opacity="0"/></linearGradient></defs>
        <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${baseline}" class="chart-axis"/>
        <line x1="${padding.left}" y1="${baseline}" x2="${width - padding.right}" y2="${baseline}" class="chart-axis"/>
        <line x1="${padding.left}" y1="${padding.top + plotHeight / 2}" x2="${width - padding.right}" y2="${padding.top + plotHeight / 2}" class="chart-grid"/>
        <path d="${areaPath}" fill="url(#chart-area-${item.code})"/>
        <path d="${linePath}" class="chart-line"/>
        <circle cx="${x(visible.length - 1)}" cy="${y(last.value)}" r="4" class="chart-dot"/>
        <text x="${padding.left - 8}" y="${padding.top + 4}" text-anchor="end" class="chart-label">${formatRate(maximum)}</text>
        <text x="${padding.left - 8}" y="${baseline}" text-anchor="end" class="chart-label">${formatRate(minimum)}</text>
        <text x="${padding.left}" y="${height - 8}" class="chart-label">${formatShortDate(first.date)}</text>
        <text x="${width - padding.right}" y="${height - 8}" text-anchor="end" class="chart-label">${formatShortDate(last.date)}</text>
      </svg>
    </div>`;

  document.querySelectorAll("[data-range]").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.range) === days);
    button.onclick = () => renderHistoryChart(item, allPoints, Number(button.dataset.range));
  });
}

document.querySelectorAll(".nav-item").forEach((button) =>
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    state.filter = button.dataset.filter;
    renderTable();
  }),
);
$("#search-input").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderTable();
});
$("#convert-amount").addEventListener("input", renderConverter);
$("#from-currency").addEventListener("change", renderConverter);
$("#to-currency").addEventListener("change", renderConverter);
$("#swap-currencies").addEventListener("click", () => {
  const from = $("#from-currency").value;
  $("#from-currency").value = $("#to-currency").value;
  $("#to-currency").value = from;
  renderConverter();
});
$("#refresh-button").addEventListener("click", () => loadData(true));
$("[data-jump-risk]").addEventListener("click", () =>
  document.querySelector('[data-filter="high-risk"]').click(),
);
$(".dialog-close").addEventListener("click", () => $("#currency-dialog").close());
$("#currency-dialog").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});
loadData();
setInterval(() => loadData(false), 5 * 60 * 1000);
