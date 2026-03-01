/**
 * Gold Price Tracker - Script
 * Reads CSV data, renders price table & Chart.js chart
 */

// ============================================
// Data Layer
// ============================================

let allData = [];
let chart = null;

const CSV_PATH = "data/gold_prices.csv";

const GOLD_TYPE_LABELS = {
    "Nhẫn 999.9": "Vàng Nhẫn 999.9",
    "Vàng Miếng SJC (Loại 10 chỉ)": "Vàng Miếng SJC (Loại 10 chỉ)",
};

async function loadCSV() {
    try {
        const res = await fetch(CSV_PATH);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        return parseCSV(text);
    } catch (err) {
        console.error("Failed to load CSV:", err);
        return [];
    }
}

function parseCSV(text) {
    const lines = text.trim().split("\n");
    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map((h) => h.trim());
    const data = [];

    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(",").map((v) => v.trim());
        if (values.length < 4) continue;

        const row = {};
        headers.forEach((h, idx) => {
            row[h] = values[idx];
        });

        row.buy_price = parseInt(row.buy_price, 10) || 0;
        row.sell_price = parseInt(row.sell_price, 10) || 0;

        data.push(row);
    }

    // Sort by date ascending
    data.sort((a, b) => a.date.localeCompare(b.date));
    return data;
}

// ============================================
// Filters
// ============================================

function getUniqueDates(data) {
    const dates = [...new Set(data.map((d) => d.date))];
    dates.sort((a, b) => b.localeCompare(a)); // newest first
    return dates;
}

function populateDateSelect(dates) {
    const select = document.getElementById("dateSelect");
    select.innerHTML = "";

    dates.forEach((date, i) => {
        const opt = document.createElement("option");
        opt.value = date;
        opt.textContent = formatDate(date);
        if (i === 0) opt.selected = true;
        select.appendChild(opt);
    });
}

function formatDate(dateStr) {
    const [y, m, d] = dateStr.split("-");
    return `${y}-${m}-${d}`;
}

function formatDateVN(dateStr) {
    const [y, m, d] = dateStr.split("-");
    return `${d}/${m}/${y}`;
}

// ============================================
// Price Table
// ============================================

function renderTable(data, selectedDate) {
    const tbody = document.getElementById("tableBody");
    const todayData = data.filter((d) => d.date === selectedDate);

    if (!todayData.length) {
        tbody.innerHTML = `<tr><td colspan="3" class="loading-cell">Không có dữ liệu cho ngày ${formatDateVN(selectedDate)}</td></tr>`;
        return;
    }

    // Find previous date for change calculation
    const dates = getUniqueDates(data);
    const currentIdx = dates.indexOf(selectedDate);
    const prevDate = currentIdx < dates.length - 1 ? dates[currentIdx + 1] : null;
    const prevData = prevDate ? data.filter((d) => d.date === prevDate) : [];

    let html = "";

    todayData.forEach((item) => {
        const prevItem = prevData.find((p) => p.gold_type === item.gold_type);
        const buyChange = prevItem ? item.buy_price - prevItem.buy_price : 0;
        const sellChange = prevItem ? item.sell_price - prevItem.sell_price : 0;

        html += `
            <tr>
                <td class="gold-name">${escapeHTML(item.gold_type)}</td>
                <td class="price-cell">
                    ${formatPrice(item.buy_price)}
                    ${renderChange(buyChange)}
                </td>
                <td class="price-cell">
                    ${formatPrice(item.sell_price)}
                    ${renderChange(sellChange)}
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function formatPrice(price) {
    return price.toLocaleString("vi-VN");
}

function renderChange(change) {
    if (change === 0) return "";

    const sign = change > 0 ? "+" : "";
    const arrow = change > 0 ? "▲" : "▼";
    const cls = change > 0 ? "up" : "down";

    return `<span class="price-change ${cls}">${arrow} ${sign}${formatPrice(change)}</span>`;
}

function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ============================================
// Chart
// ============================================

function renderChart(data, selectedGoldType) {
    const filtered = data.filter((d) => d.gold_type === selectedGoldType);

    const labels = filtered.map((d) => d.date);
    const buyPrices = filtered.map((d) => d.buy_price);
    const sellPrices = filtered.map((d) => d.sell_price);

    const chartTitle = document.getElementById("chartTitle");
    chartTitle.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
        </svg>
        ${GOLD_TYPE_LABELS[selectedGoldType] || selectedGoldType}
    `;

    const ctx = document.getElementById("priceChart").getContext("2d");

    if (chart) {
        chart.destroy();
    }

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Giá mua",
                    data: buyPrices,
                    borderColor: "#16a34a",
                    backgroundColor: "rgba(22, 163, 74, 0.08)",
                    borderWidth: 2.5,
                    pointRadius: labels.length > 60 ? 0 : labels.length > 30 ? 2 : 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#16a34a",
                    pointBorderColor: "#fff",
                    pointBorderWidth: 2,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: "Giá bán",
                    data: sellPrices,
                    borderColor: "#dc2626",
                    backgroundColor: "rgba(220, 38, 38, 0.08)",
                    borderWidth: 2.5,
                    pointRadius: labels.length > 60 ? 0 : labels.length > 30 ? 2 : 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#dc2626",
                    pointBorderColor: "#fff",
                    pointBorderWidth: 2,
                    tension: 0.3,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: {
                    position: "top",
                    align: "end",
                    labels: {
                        usePointStyle: true,
                        pointStyle: "circle",
                        padding: 16,
                        font: {
                            family: "'Inter', sans-serif",
                            size: 13,
                            weight: "600",
                        },
                    },
                },
                tooltip: {
                    backgroundColor: "rgba(28, 25, 23, 0.92)",
                    titleFont: { family: "'Inter', sans-serif", size: 13, weight: "600" },
                    bodyFont: { family: "'Inter', sans-serif", size: 13 },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function (items) {
                            if (!items.length) return "";
                            const dateStr = items[0].label;
                            const [y, m, d] = dateStr.split("-");
                            return `${d}/${m}/${y}`;
                        },
                        label: function (item) {
                            return ` ${item.dataset.label}: ${parseInt(item.raw).toLocaleString("vi-VN")} VND`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false,
                    },
                    ticks: {
                        font: { family: "'Inter', sans-serif", size: 11 },
                        color: "#78716c",
                        maxRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 12,
                        callback: function (value, index) {
                            const label = this.getLabelForValue(value);
                            const [y, m, d] = label.split("-");
                            return `${d}/${m}`;
                        },
                    },
                    title: {
                        display: true,
                        text: "Ngày",
                        font: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                        color: "#78716c",
                    },
                },
                y: {
                    display: true,
                    grid: {
                        color: "rgba(0,0,0,0.04)",
                    },
                    ticks: {
                        font: { family: "'Inter', sans-serif", size: 11 },
                        color: "#78716c",
                        callback: function (value) {
                            return (value / 1000000).toFixed(1) + "M";
                        },
                    },
                },
            },
        },
    });
}

// ============================================
// Update Timestamp
// ============================================

function updateTimestamp(data) {
    const dates = getUniqueDates(data);
    const latest = dates[0];
    if (latest) {
        document.getElementById("updateTime").textContent = `Cập nhật lần cuối: ${formatDateVN(latest)}`;
    }
}

// ============================================
// Init
// ============================================

async function init() {
    allData = await loadCSV();

    if (!allData.length) {
        document.getElementById("tableBody").innerHTML =
            '<tr><td colspan="3" class="loading-cell">Chưa có dữ liệu. Vui lòng chạy scraper trước.</td></tr>';
        return;
    }

    const dates = getUniqueDates(allData);
    populateDateSelect(dates);

    const selectedDate = dates[0];
    const goldTypeSelect = document.getElementById("goldTypeSelect");
    const selectedGoldType = goldTypeSelect.value;

    renderTable(allData, selectedDate);
    renderChart(allData, selectedGoldType);
    updateTimestamp(allData);

    // Event listeners
    document.getElementById("dateSelect").addEventListener("change", (e) => {
        renderTable(allData, e.target.value);
    });

    goldTypeSelect.addEventListener("change", (e) => {
        renderChart(allData, e.target.value);
    });
}

document.addEventListener("DOMContentLoaded", init);
