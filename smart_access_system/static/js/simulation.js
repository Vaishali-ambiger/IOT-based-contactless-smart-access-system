// simulation.js
// Handles all the interactive logic on the Access Simulation page.

let stepStatus = {
    rfid: false,
    temp: false,
    mask: false
};

// ---------------- STEP 1: RFID ----------------
async function scanRfid() {
    const rfidId = document.getElementById("rfid-input").value;

    const res = await fetch("/api/scan_rfid", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rfid_id: rfidId })
    });
    const data = await res.json();

    const box = document.getElementById("rfid-result");
    if (!res.ok) {
        box.textContent = data.error;
        box.className = "result-box result-box result-warn";
        stepStatus.rfid = false;
        return;
    }
    if (data.rfid_status === "Authorized") {
        box.textContent = "🟢 RFID AUTHORIZED";
        box.className = "result-box result-ok";
        setFlowStep("flow-rfid", true);
        setFlowStep("flow-auth", true);
    } else {
        box.textContent = "🔴 RFID NOT AUTHORIZED";
        box.className = "result-box result-fail";
        setFlowStep("flow-rfid", false);
        setFlowStep("flow-auth", false);
    }

    stepStatus.rfid = true;
}

// ---------------- STEP 2: TEMPERATURE ----------------
async function checkTemperature() {
    const temp = document.getElementById("temp-input").value;

    const res = await fetch("/api/check_temperature", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ temperature: temp })
    });
    const data = await res.json();

    const box = document.getElementById("temp-result");
    if (data.error) {
        box.textContent = "⚠️ " + data.error;
        box.className = "result-box result-warn";
        stepStatus.temp = false;
        return;
    }

    if (data.temperature_status === "Safe") {
        box.textContent = `🟢 TEMPERATURE SAFE (${data.temperature}°C)`;
        box.className = "result-box result-ok";
        setFlowStep("flow-temp", true);
    } else {
        box.textContent = `⚠️ HIGH TEMPERATURE WARNING (${data.temperature}°C)`;
        box.className = "result-box result-warn";
        setFlowStep("flow-temp", false);
    }

    stepStatus.temp = true;
}

// ---------------- STEP 3: MASK ----------------
async function checkMask(maskDetected) {
    const res = await fetch("/api/check_mask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mask_detected: maskDetected })
    });
    const data = await res.json();

    const box = document.getElementById("mask-result");
    if (data.mask_status === "Detected") {
        box.textContent = "🟢 MASK DETECTED";
        box.className = "result-box result-ok";
        setFlowStep("flow-mask-step", true);
    } else {
        box.textContent = "⚠️ MASK REQUIRED";
        box.className = "result-box result-warn";
        setFlowStep("flow-mask-step", false);
    }

    stepStatus.mask = true;
}

// ---------------- FINAL DECISION ----------------
async function submitFinalDecision() {
    const finalBox = document.getElementById("final-result");

    if (!stepStatus.rfid || !stepStatus.temp || !stepStatus.mask) {
        finalBox.textContent = "⚠️ Please complete all 3 steps first (RFID, Temperature, Mask).";
        finalBox.className = "result-box result-box-large result-warn";
        return;
    }

    const res = await fetch("/api/final_decision", { method: "POST" });
    const data = await res.json();

    const twinDoor = document.getElementById("twin-door");
    const doorText = document.getElementById("door-text");

    if (data.decision === "GRANTED") {
        finalBox.textContent = "🟢 ACCESS GRANTED";
        finalBox.className = "result-box result-box-large result-ok";
        setFlowStep("flow-door", true);
        twinDoor.classList.add("open");
        doorText.textContent = "OPEN";

        // Automatically close the door again after 3 seconds, like a real access system
        setTimeout(() => {
            twinDoor.classList.remove("open");
            doorText.textContent = "CLOSED";
        }, 3000);

    } else {
        finalBox.textContent = `🔴 ACCESS DENIED — ${data.reason}`;
        finalBox.className = "result-box result-box-large result-fail";
        setFlowStep("flow-door", false);
        twinDoor.classList.remove("open");
        doorText.textContent = "CLOSED";
    }
}

// ---------------- RESET ----------------
async function resetSimulation() {
    await fetch("/api/reset", { method: "POST" });

    stepStatus = { rfid: false, temp: false, mask: false };

    document.getElementById("rfid-result").textContent = "Waiting for Scan";
    document.getElementById("rfid-result").className = "result-box";

    document.getElementById("temp-result").textContent = "Not Checked";
    document.getElementById("temp-result").className = "result-box";

    document.getElementById("mask-result").textContent = "Not Checked";
    document.getElementById("mask-result").className = "result-box";

    document.getElementById("final-result").textContent = "Complete steps 1-3 first";
    document.getElementById("final-result").className = "result-box result-box-large";

    ["flow-rfid", "flow-auth", "flow-temp", "flow-mask-step", "flow-door"].forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove("active-ok", "active-fail");
    });

    const twinDoor = document.getElementById("twin-door");
    twinDoor.classList.remove("open");
    document.getElementById("door-text").textContent = "CLOSED";
}

// ---------------- Helper ----------------
function setFlowStep(elementId, isOk) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.remove("active-ok", "active-fail");
    el.classList.add(isOk ? "active-ok" : "active-fail");
}
