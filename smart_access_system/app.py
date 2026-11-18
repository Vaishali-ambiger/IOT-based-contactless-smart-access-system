"""
Smart Access & Safety Digital Twin
-----------------------------------
This is a SOFTWARE-ONLY SIMULATION.
It does NOT connect to any real hardware (no NodeMCU, no Arduino,
no real RFID reader, no real sensors, no real servo motor).

Everything here is simulated using buttons and input fields on a
web dashboard, and the results are stored in a local SQLite database.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import database
from datetime import datetime
from threading import Timer
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SMART_ACCESS_SECRET", "development-only-secret")

# ------------------------------------------------------------------
# Default safety setting (this will become editable in Phase 2 - Admin page)
# ------------------------------------------------------------------
database.init_db()
door_timer = None

# ------------------------------------------------------------------
# This dictionary holds the CURRENT state of the simulated system.
# Think of it as "what the dashboard should show right now".
# It lives in memory (not the database) because it only represents
# the live/current simulation - the database stores the HISTORY.
# ------------------------------------------------------------------
current_state = {
    "rfid_id": None,
    "rfid_status": "Waiting for Scan",
    "temperature": None,
    "temperature_status": "Not Checked",
    "mask_status": "Not Checked",
    "decision": "Waiting",
    "door_status": "CLOSED",
    "reason": ""
}


# ------------------------------------------------------------------
# PAGE ROUTES (these return full HTML pages)
# ------------------------------------------------------------------

@app.route("/")
def dashboard():
    """Main dashboard page - shows the digital twin and live status."""
    return render_template("index.html", state=current_state)


@app.route("/simulation")
def simulation():
    """Access Simulation page - where the user simulates a visitor entering."""
    return render_template("simulation.html", state=current_state,
                           threshold=get_temperature_threshold())


@app.route("/logs")
def logs():
    return render_template("logs.html", logs=database.get_access_logs())


@app.route("/alerts")
def alerts():
    return render_template("alerts.html", alerts=database.get_alerts())


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        action = request.form.get("action")
        rfid_id = request.form.get("rfid_id", "").strip().upper()
        if action in ("add", "remove") and not rfid_id:
            flash("Please enter an RFID ID.", "error")
        elif action == "add":
            flash("RFID added successfully." if database.add_authorized_rfid(rfid_id)
                  else "RFID already exists.", "success" if rfid_id else "error")
        elif action == "remove":
            flash("RFID removed successfully." if database.remove_authorized_rfid(rfid_id)
                  else "RFID not found.", "success" if rfid_id else "error")
        elif action == "threshold":
            try:
                threshold = float(request.form.get("threshold", ""))
                if threshold <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                flash("Please enter a valid temperature threshold.", "error")
            else:
                database.set_setting("temp_threshold", threshold)
                flash("Temperature threshold updated.", "success")
        return redirect(url_for("admin"))
    return render_template("admin.html", rfids=database.get_authorized_rfids(),
                           threshold=get_temperature_threshold())


# ------------------------------------------------------------------
# API ROUTES (these return JSON - used by JavaScript via fetch())
# ------------------------------------------------------------------

@app.route("/api/status")
def get_status():
    """Returns the current live state. Used by the dashboard to refresh itself."""
    state = dict(current_state)
    state["statistics"] = database.get_statistics()
    state["temperature_threshold"] = get_temperature_threshold()
    return jsonify(state)


def get_temperature_threshold():
    return float(database.get_setting("temp_threshold", "37.5"))


def create_alert(alert_type, message):
    now = datetime.now()
    database.add_safety_alert(now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                              alert_type, message)


@app.route("/api/scan_rfid", methods=["POST"])
def scan_rfid():
    """Simulates scanning an RFID card."""
    data = request.get_json(silent=True) or {}
    rfid_id = data.get("rfid_id", "").strip().upper()
    if not rfid_id:
        return jsonify({"error": "Please enter an RFID ID."}), 400

    authorized_ids = database.get_authorized_rfids()

    current_state["rfid_id"] = rfid_id
    if rfid_id in authorized_ids:
        current_state["rfid_status"] = "Authorized"
    else:
        current_state["rfid_status"] = "Unauthorized"
        create_alert("Security", "Unauthorized Access Attempt")

    return jsonify({
        "rfid_id": rfid_id,
        "rfid_status": current_state["rfid_status"]
    })


@app.route("/api/check_temperature", methods=["POST"])
def check_temperature():
    """Simulates reading a temperature sensor."""
    data = request.get_json(silent=True) or {}

    try:
        temp = float(data.get("temperature"))
    except (TypeError, ValueError):
        return jsonify({"error": "Please enter a valid temperature."}), 400

    current_state["temperature"] = temp
    threshold = get_temperature_threshold()
    if temp <= threshold:
        current_state["temperature_status"] = "Safe"
    else:
        current_state["temperature_status"] = "High"
        create_alert("Safety", "High Temperature Detected")

    return jsonify({
        "temperature": temp,
        "temperature_status": current_state["temperature_status"],
        "threshold": threshold
    })


@app.route("/api/check_mask", methods=["POST"])
def check_mask():
    """Simulates a mask-detection camera result."""
    data = request.get_json(silent=True) or {}
    mask_detected = data.get("mask_detected", False)

    current_state["mask_status"] = "Detected" if mask_detected else "Not Detected"
    if not mask_detected:
        create_alert("Safety", "Mask Required")

    return jsonify({"mask_status": current_state["mask_status"]})


@app.route("/api/final_decision", methods=["POST"])
def final_decision():
    """
    Combines all three checks (RFID + Temperature + Mask) and decides
    whether the digital door should open or stay closed.
    Also saves the attempt into the Access Logs table in the database.
    """
    rfid_ok = current_state["rfid_status"] == "Authorized"
    temp_ok = current_state["temperature_status"] == "Safe"
    mask_ok = current_state["mask_status"] == "Detected"

    if rfid_ok and temp_ok and mask_ok:
        decision = "GRANTED"
        door_status = "OPEN"
        reason = "All safety checks passed"
    else:
        decision = "DENIED"
        door_status = "CLOSED"
        failed = []
        if not rfid_ok:
            failed.append("Unauthorized RFID")
        if not temp_ok:
            failed.append("High Temperature")
        if not mask_ok:
            failed.append("Mask Required")
        reason = ", ".join(failed)

    current_state["decision"] = decision
    current_state["door_status"] = door_status
    current_state["reason"] = reason

    # Save this attempt to the database (this is what will power
    # the Access Logs page and Dashboard statistics in Phase 2)
    now = datetime.now()
    database.add_access_log(
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        rfid_id=current_state["rfid_id"] or "N/A",
        rfid_status=current_state["rfid_status"],
        temperature=current_state["temperature"],
        mask_status=current_state["mask_status"],
        decision=decision,
        door_status=door_status,
        reason=reason
    )

    if decision == "GRANTED":
        schedule_door_close()

    return jsonify(current_state)


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Resets the simulation back to its starting state (for a new visitor)."""
    global door_timer
    if door_timer:
        door_timer.cancel()
        door_timer = None
    current_state.update({
        "rfid_id": None,
        "rfid_status": "Waiting for Scan",
        "temperature": None,
        "temperature_status": "Not Checked",
        "mask_status": "Not Checked",
        "decision": "Waiting",
        "door_status": "CLOSED",
        "reason": ""
    })
    return jsonify(current_state)


def close_door():
    if current_state["door_status"] == "OPEN":
        current_state["door_status"] = "CLOSED"


def schedule_door_close():
    global door_timer
    if door_timer:
        door_timer.cancel()
    door_timer = Timer(3.0, close_door)
    door_timer.daemon = True
    door_timer.start()


if __name__ == "__main__":
    # Create the database and tables (only happens once, safe to run every time)
    database.init_db()
    app.run(debug=True)
