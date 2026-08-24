const state = { filter: "all", query: "", rates: [] };
const filterTitles = { all: "全部汇率", major: "主流货币", "low-price": "订阅低价区", "high-risk": "风险观察名单" };

const $ = (selector) => document.querySelector(selector);
const formatRate = (value) => {
  if (value === null || value === undefined) return "—";
  if (value >= 100) return value.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
  if (value >= 1) return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 6 });
  return value.toLocaleString("zh-CN", { minimumSignificantDigits: 3, maximumSignificantDigits: 6 });
};
const formatChange = (value) => {
  if (value === null) return '<span class="change muted">数据积累中</span>';
  const cls = value > 0 ? "up" : value < 0 ? "down" : "muted";
  const prefix = value > 0 ? "+" : "";
  return `<span class="change ${cls}">${prefix}${value.toFixed(2)}%</span>`;
};
const formatTime = (iso) => new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));
const riskLabel = (score) => score >= 70 ? ["高风险", "high"] : score >= 30 ? ["关注", "medium"] : ["正常", ""];
const toast = (message) => { const node = $("#toast"); node.textContent = message; node.classList.add("show"); setTimeout(() => node.classList.remove("show"), 2200); };

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
    renderTable();
    if (showToast) toast("看板已刷新");
  } catch (error) {
    $("#rates-body").innerHTML = `<tr><td colspan="6"><div class="loading">无法加载数据：${error.message}</div></td></tr>`;
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
  $("#updated-text").textContent = data.last_updated ? `数据日期 ${formatTime(data.last_updated)} · 自动监测中` : "首次数据同步正在进行，请稍候刷新";
  if (data.top_drops.length) {
    const item = data.top_drops[0];
    $("#risk-message").textContent = `${item.code} 当前为 24 小时跌幅首位（${item.change_1d.toFixed(2)}%）。`;
  }
}

function renderTable() {
  const query = state.query.trim().toLocaleLowerCase();
  const flag = { major: "is_major", "low-price": "is_low_price", "high-risk": "is_high_risk" }[state.filter];
  const rows = state.rates.filter((item) => (!flag || item[flag]) && (!query || `${item.code} ${item.name_zh} ${item.name_en}`.toLocaleLowerCase().includes(query)));
  $("#table-title").textContent = filterTitles[state.filter];
  $("#result-count").textContent = `显示 ${rows.length} 种货币`;
  if (!rows.length) {
    $("#rates-body").innerHTML = '<tr><td colspan="6"><div class="loading">没有匹配的货币</div></td></tr>';
    return;
  }
  $("#rates-body").innerHTML = rows.map((item) => {
    const [label, cls] = riskLabel(item.risk_score);
    return `<tr data-code="${item.code}">
      <td><div class="currency-cell"><span class="currency-icon">${item.code.slice(0, 2)}</span><span class="currency-name"><strong>${item.code} · ${item.name_zh || item.name_en}</strong><small>${item.name_en}</small></span></div></td>
      <td><span class="rate-value">¥ ${formatRate(item.value_cny)}</span></td>
      <td>${formatChange(item.change_1d)}</td><td>${formatChange(item.change_7d)}</td>
      <td><span class="risk-badge ${cls}">${label} ${item.risk_score}</span></td>
      <td class="time-cell">${formatTime(item.observed_at)}</td></tr>`;
  }).join("");
  document.querySelectorAll("tr[data-code]").forEach((row) => row.addEventListener("click", () => openCurrency(row.dataset.code)));
}

function openCurrency(code) {
  const item = state.rates.find((rate) => rate.code === code);
  if (!item) return;
  const [label] = riskLabel(item.risk_score);
  $("#dialog-content").innerHTML = `<span class="detail-kicker">${item.is_high_risk ? "RISK WATCH" : "CURRENCY DETAIL"}</span>
    <h2 class="detail-title">${item.code} · ${item.name_zh || item.name_en}</h2><p class="subtitle">${item.name_en}</p>
    <div class="detail-rate"><span>1 ${item.code} 当前参考价值</span><strong>¥ ${formatRate(item.value_cny)}</strong></div>
    <div class="detail-meta"><div><span>24 小时</span><strong>${item.change_1d === null ? "数据积累中" : `${item.change_1d.toFixed(2)}%`}</strong></div><div><span>风险等级</span><strong>${label} · ${item.risk_score}</strong></div><div><span>报价类型</span><strong>央行参考价</strong></div></div>
    <p class="subtitle">来源：${item.source} · 数据日期：${formatTime(item.observed_at)}。该数据不代表银行或支付平台实际成交价。</p>`;
  $("#currency-dialog").showModal();
}

document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach((node) => node.classList.remove("active"));
  button.classList.add("active"); state.filter = button.dataset.filter; renderTable();
}));
$("#search-input").addEventListener("input", (event) => { state.query = event.target.value; renderTable(); });
$("#refresh-button").addEventListener("click", () => loadData(true));
$("[data-jump-risk]").addEventListener("click", () => document.querySelector('[data-filter="high-risk"]').click());
$(".dialog-close").addEventListener("click", () => $("#currency-dialog").close());
$("#currency-dialog").addEventListener("click", (event) => { if (event.target === event.currentTarget) event.currentTarget.close(); });
loadData();
setInterval(() => loadData(false), 5 * 60 * 1000);
