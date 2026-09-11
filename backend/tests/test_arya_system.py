"""
test_arya_system.py
-------------------
Comprehensive test suite for Project ARYA:
- Core API routes (Memories, Goals, Tasks, Devices, System Status)
- Memory Knowledge Graph generation
- Cross-device command dispatch
- Agent action planner tool recognition for smart home & hardware control
- WebSocket streaming endpoints
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import agent_planner

client = TestClient(app)


def test_system_status():
    """Verify system telemetry endpoint returns active status and counts."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Project ARYA" in data["name"]
    assert "ai_gateway" in data
    assert data["total_devices"] >= 1


def test_device_node_endpoints():
    """Verify device listing, registration, and remote command routing."""
    # 1. List devices
    res = client.get("/api/devices")
    assert res.status_code == 200
    devices = res.json()
    assert isinstance(devices, list)
    assert len(devices) > 0

    # 2. Register a new test mobile node
    test_node = {
        "node_id": "test-mobile-node-1",
        "name": "Test iPhone 16 Pro",
        "device_type": "mobile",
        "ip_address": "192.168.1.199",
        "capabilities": ["voice_input", "notifications", "haptic"],
        "state_data": {"battery": 95, "charging": True},
    }
    reg_res = client.post("/api/devices", json=test_node)
    assert reg_res.status_code == 200
    created = reg_res.json()
    assert created["node_id"] == "test-mobile-node-1"
    assert created["status"] == "online"

    # 3. Dispatch command to device
    cmd_payload = {
        "action": "notify",
        "params": {"title": "ARYA System Alert", "message": "Test notification"},
    }
    cmd_res = client.post("/api/devices/test-mobile-node-1/command", json=cmd_payload)
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    assert cmd_data["node_id"] == "test-mobile-node-1"
    assert cmd_data["action"] == "notify"


def test_memory_knowledge_graph():
    """Verify memory graph structure returns valid core, category, and leaf nodes."""
    res = client.get("/api/memories/graph")
    assert res.status_code == 200
    graph = res.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0

    # Verify root center node exists
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "root_arya" in node_ids


def test_agent_planner_cross_device_tools():
    """Verify agent_planner recognizes device control and smart home tools."""
    # 1. Lock screen command
    plan_lock = agent_planner.plan("lock my laptop")
    assert len(plan_lock) > 0
    assert any("lock" in step["tool"] or step["tool"] == "device_command" for step in plan_lock)

    # 2. Smart lighting command
    plan_light = agent_planner.plan("turn off the living room lights")
    assert len(plan_light) > 0
    assert any("light" in step["tool"] or "smarthome" in step["tool"] for step in plan_light)

    # 3. TV command
    plan_tv = agent_planner.plan("turn on the TV and set volume to 20")
    assert len(plan_tv) > 0
    assert any("tv" in step["tool"] or "volume" in step["tool"] for step in plan_tv)


def test_websocket_agent_handshake():
    """Verify WebSocket /ws/agent connection and status ping."""
    with client.websocket_connect("/ws/agent") as websocket:
        # Initial status frame sent on connection
        welcome = websocket.receive_json()
        assert welcome["type"] == "system_status"
        assert welcome["status"] == "connected"

        # Ping-pong test
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"


def test_websocket_device_daemon_handshake():
    """Verify WebSocket /ws/devices/{node_id} registration and heartbeat."""
    with client.websocket_connect("/ws/devices/test-daemon-node") as websocket:
        # Send heartbeat
        websocket.send_json({
            "type": "heartbeat",
            "node_id": "test-daemon-node",
            "state": {"cpu": 15, "battery": 100},
        })
        ack = websocket.receive_json()
        assert ack["type"] == "heartbeat_ack"
