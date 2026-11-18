// script.js
// Shared helper functions used across pages.

// Fetches the current system state from the server and updates
// the Dashboard status cards + digital twin door.
async function refreshDashboard() {
    try {
        const res = await fetch("/api/status");
        const state = await res.json();
        updateDashboardUI(state);
    } catch (err) {
        console.error("Could not refresh dashboard:", err);
    }
}

function updateDashboardUI(state) {
    const rfidCard = document.getElementById("card-rfid");
    const tempCard = document.getElementById("card-temperature");
    const maskCard = document.getElementById("card-mask");
    const doorCard = document.getElementById("card-door");
    const decisionCard = document.getElementById("card-decision");
    const reasonBox = document.getElementById("dashboard-reason");
    const twinDoor = document.getElementById("twin-door");
    const doorText = document.getElementById("door-text");

    if (rfidCard) rfidCard.textContent = state.rfid_status;
    if (tempCard) tempCard.textContent = state.temperature ? state.temperature + "°C" : "--";
    if (maskCard) maskCard.textContent = state.mask_status;

    if (doorCard) {
        doorCard.textContent = state.door_status === "OPEN" ? "🟢 OPEN" : "🔴 CLOSED";
    }

    if (decisionCard) {
        decisionCard.textContent = state.decision === "GRANTED" ? "ACCESS GRANTED"
                                   : state.decision === "DENIED" ? "ACCESS DENIED"
                                   : state.decision;
    }

    if (reasonBox) {
        const bannerText = reasonBox.querySelector(".banner-text");
        if (bannerText) bannerText.textContent = state.reason || "No access decision yet.";
        else reasonBox.append(document.createTextNode(state.reason || "No access decision yet."));
    }
    if (state.statistics) {
        document.getElementById("stat-total").textContent = state.statistics.total;
        document.getElementById("stat-granted").textContent = state.statistics.granted;
        document.getElementById("stat-denied").textContent = state.statistics.denied;
        document.getElementById("stat-alerts").textContent = state.statistics.alerts;
    }

    if (twinDoor && doorText) {
        if (state.door_status === "OPEN") {
            twinDoor.classList.add("open");
            doorText.textContent = "OPEN";
        } else {
            twinDoor.classList.remove("open");
            doorText.textContent = "CLOSED";
        }
    }
}
