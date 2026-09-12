"""
main.py
-------
Entry point for the ARYA backend. Defines the FastAPI app and wires
together memory, goals, tasks, desktop actions, conversation context,
profile building, and AI chat.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("arya.main")

# Load environment variables from backend/.env (TV_IP, TV_MAC, API keys, etc.)
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import (
    models,
    schemas,
    conversation_service,
    context_resolver,
    desktop_actions,
    action_planner,
    agent_planner,
    agent_executor,
    goal_commands,
    goal_service,
    memory_commands,
    memory_extractor,
    memory_service,
    memory_retriever,
    memory_validator,
    news_handlers,
    performance_service,
    profile_commands,
    profile_service,
    task_commands,
    task_service,
    ai_service,
    device_service,
)
from .database import engine, get_db
from .ws_manager import ws_hub
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Create database tables on startup if they don't already exist.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project ARYA - Autonomous Agentic OS", version="2.0.0")

# Enable CORS for modern Web & PWA frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------------------------------------------------------------------
# One-time startup migration (memory_cleanup_v1)
# ---------------------------------------------------------------------------

_MIGRATION_KEY = "memory_cleanup_v1_completed"


def _get_setting(db: Session, key: str) -> str | None:
    """Read a value from the key-value settings table."""
    try:
        row = db.execute(
            text("SELECT value FROM settings WHERE key = :k"), {"k": key}
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _set_setting(db: Session, key: str, value: str) -> None:
    """Upsert a value in the key-value settings table."""
    db.execute(
        text(
            "INSERT INTO settings (key, value) VALUES (:k, :v) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        ),
        {"k": key, "v": value},
    )
    db.commit()


def _run_startup_migration() -> None:
    """Run the memory cleanup migration exactly once."""
    from .database import SessionLocal  # avoid circular at module level
    db = SessionLocal()
    try:
        # Ensure the settings table exists
        db.execute(text(
            "CREATE TABLE IF NOT EXISTS settings "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        ))
        # Ensure category column exists in memories table
        try:
            db.execute(text("ALTER TABLE memories ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"))
            db.commit()
        except Exception:
            db.rollback()

        if _get_setting(db, _MIGRATION_KEY) == "true":
            print("[MEMORY CLEANUP] Already completed — skipping migration.")
            return

        print("[MEMORY CLEANUP] Running one-time cleanup migration...")
        memory_service.run_cleanup_migration(db)
        _set_setting(db, _MIGRATION_KEY, "true")
        device_service.seed_default_devices(db)
    finally:
        db.close()


_run_startup_migration()


def _seed_devices_if_needed():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        device_service.seed_default_devices(db)
    finally:
        db.close()


_seed_devices_if_needed()

def create_memory(memory: schemas.MemoryCreate, db: Session = Depends(get_db)):
    """Store a new memory."""
    return memory_service.save_memory(db, memory)


@app.get("/memory", response_model=list[schemas.MemoryResponse])
def list_memories(db: Session = Depends(get_db)):
    """Get all stored memories, newest first."""
    return memory_service.get_all_memories(db)


@app.get("/memory/search", response_model=list[schemas.MemoryResponse])
def search_memory(q: str, db: Session = Depends(get_db)):
    """Search memories containing the keyword 'q'."""
    return memory_service.search_memories(db, q)


@app.get("/memories", response_model=list[schemas.MemoryResponse])
def dashboard_memories(db: Session = Depends(get_db)):
    """Dashboard endpoint for stored memories."""
    return memory_service.get_all_memories(db)


@app.get("/goals", response_model=list[schemas.GoalResponse])
def dashboard_goals(db: Session = Depends(get_db)):
    """Dashboard endpoint for goals."""
    return goal_service.get_goals(db)


@app.get("/tasks", response_model=list[schemas.TaskResponse])
def dashboard_tasks(db: Session = Depends(get_db)):
    """Dashboard endpoint for tasks."""
    return task_service.get_tasks(db)


@app.post("/tasks", response_model=schemas.TaskResponse)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    """Create a task."""
    return task_service.add_task(db, task.title)


@app.post("/tasks/{task_id}/complete", response_model=schemas.TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Complete a task by id."""
    task = task_service.complete_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/api/memories/{memory_id}")
def delete_memory_endpoint(memory_id: int, db: Session = Depends(get_db)):
    """Delete a memory entry by ID."""
    success = memory_service.delete_memory_by_id(db, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "message": f"Memory {memory_id} deleted successfully."}


@app.post("/api/goals/{goal_id}/complete")
def complete_goal_endpoint(goal_id: int, db: Session = Depends(get_db)):
    """Toggle completion status for a goal."""
    goal = goal_service.complete_goal_by_id(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True, "goal": {"id": goal.id, "title": goal.title, "status": goal.status}}



@app.get("/profile")
def dashboard_profile(db: Session = Depends(get_db)):
    """Dashboard endpoint for the user profile."""
    memories = memory_service.get_all_memories(db)
    return {"profile": profile_service.build_profile(memories)}


@app.get("/performance/report")
def performance_report():
    """Return recent chat performance timings."""
    return performance_service.get_report()


@app.get("/news", response_model=schemas.NewsResponse)
def get_news():
    """Return cached or freshly fetched AI and technology news."""
    return news_handlers.get_news_endpoint_response()


# ---------------------------------------------------------------------------
# Memory Knowledge Graph Endpoint
# ---------------------------------------------------------------------------

def _clean_node_label(content: str, max_len: int = 34) -> str:
    """Extract a clean, concise title label from memory content."""
    if "]: " in content:
        title = content.split("]: ", 1)[0] + "]"
        if len(title) <= 42:
            return title
    if ": " in content:
        head = content.split(": ", 1)[0].strip()
        if 3 <= len(head) <= 36:
            return head
    clean = content.strip().replace("\n", " ")
    if len(clean) > max_len:
        cut = clean[:max_len].rsplit(" ", 1)[0]
        return cut + "..."
    return clean

@app.get("/api/memories/graph", response_model=schemas.MemoryGraphResponse)
def get_memory_graph(db: Session = Depends(get_db)):
    """Generate structured graph nodes and edges representing ARYA's memory universe."""
    memories = memory_service.get_all_memories(db)
    goals = goal_service.get_goals(db)
    tasks = task_service.get_tasks(db)
    devices = device_service.get_all_devices(db)

    nodes: list[schemas.GraphNode] = []
    edges: list[schemas.GraphEdge] = []
    existing_node_ids = set()

    def add_node(n: schemas.GraphNode):
        if n.id not in existing_node_ids:
            nodes.append(n)
            existing_node_ids.add(n.id)

    # 1. Central Core Node
    add_node(schemas.GraphNode(
        id="root_arya",
        label="ARYA Brain",
        category="Core",
        type="core",
        detail="Project ARYA Neural Core v2.0 - Central Intelligence & Context Nexus",
        status="active"
    ))

    # 2. Collect category counts
    cat_counts: dict[str, int] = {}
    for m in memories:
        cat_counts[m.category] = cat_counts.get(m.category, 0) + 1
    if goals:
        cat_counts["Goals"] = cat_counts.get("Goals", 0) + len(goals)
    if tasks:
        cat_counts["Tasks"] = cat_counts.get("Tasks", 0) + len(tasks)
    if devices:
        cat_counts["Devices"] = cat_counts.get("Devices", 0) + len(devices)

    # 3. Create Category Hub Nodes (Only categories with active children)
    for cat, count in sorted(cat_counts.items()):
        cat_id = f"cat_{cat.lower().replace(' ', '_')}"
        add_node(schemas.GraphNode(
            id=cat_id,
            label=cat,
            category=cat,
            type="category",
            detail=f"{cat} Cluster ({count} items indexed)",
            count=count
        ))
        edges.append(schemas.GraphEdge(
            id=f"edge_root_{cat_id}",
            source="root_arya",
            target=cat_id,
            relationship="contains"
        ))

    # 4. Memory Leaf Nodes
    for m in memories:
        m_id = f"mem_{m.id}"
        cat_id = f"cat_{m.category.lower().replace(' ', '_')}"
        add_node(schemas.GraphNode(
            id=m_id,
            label=_clean_node_label(m.content),
            category=m.category,
            type="memory",
            created_at=str(m.created_at) if m.created_at else None,
            detail=m.content,
            status="active",
            raw_id=str(m.id)
        ))
        edges.append(schemas.GraphEdge(
            id=f"edge_{cat_id}_{m_id}",
            source=cat_id,
            target=m_id,
            relationship="stores"
        ))

    # 5. Goal Leaf Nodes
    for g in goals:
        g_id = f"goal_{g.id}"
        add_node(schemas.GraphNode(
            id=g_id,
            label=g.title,
            category="Goals",
            type="goal",
            created_at=str(g.created_at) if g.created_at else None,
            detail=f"Ambition / Target: {g.title} (Status: {g.status.upper()})",
            status=g.status,
            raw_id=str(g.id)
        ))
        edges.append(schemas.GraphEdge(
            id=f"edge_cat_goals_{g_id}",
            source="cat_goals",
            target=g_id,
            relationship=f"{g.status}_goal"
        ))

    # 6. Task Leaf Nodes
    for t in tasks:
        t_id = f"task_{t.id}"
        add_node(schemas.GraphNode(
            id=t_id,
            label=t.title,
            category="Tasks",
            type="task",
            created_at=str(t.created_at) if t.created_at else None,
            detail=f"System Task: {t.title} (Status: {t.status.upper()})",
            status=t.status,
            raw_id=str(t.id)
        ))
        edges.append(schemas.GraphEdge(
            id=f"edge_cat_tasks_{t_id}",
            source="cat_tasks",
            target=t_id,
            relationship=f"{t.status}_task"
        ))

    # 7. Device Leaf Nodes
    for d in devices:
        d_id = f"dev_{d.id}"
        add_node(schemas.GraphNode(
            id=d_id,
            label=f"{d.name} ({d.device_type.upper()})",
            category="Devices",
            type="device",
            detail=f"Hardware Node: {d.name} | Type: {d.device_type} | IP: {d.ip_address or 'Local'} | Status: {d.status.upper()}",
            status=d.status,
            raw_id=d.node_id
        ))
        edges.append(schemas.GraphEdge(
            id=f"edge_cat_devices_{d_id}",
            source="cat_devices",
            target=d_id,
            relationship="connected_hardware"
        ))

    # 8. Meaningful Cross-Links (Interconnected Knowledge Web)
    for n in nodes:
        if "arya" in n.label.lower() and n.type == "memory":
            edges.append(schemas.GraphEdge(
                id=f"edge_{n.id}_core",
                source=n.id,
                target="root_arya",
                relationship="manifests_as"
            ))
        if "valixis" in n.label.lower() and "ecosystem" in n.category.lower():
            for other in nodes:
                if any(k in other.label.lower() for k in ("resume brain", "valexis", "pdf maker")):
                    edges.append(schemas.GraphEdge(
                        id=f"edge_{n.id}_{other.id}",
                        source=n.id,
                        target=other.id,
                        relationship="umbrella_company"
                    ))

    return schemas.MemoryGraphResponse(
        nodes=nodes,
        edges=edges,
        total_memories=len(memories),
        total_goals=len(goals),
        total_tasks=len(tasks),
        total_devices=len(devices)
    )


# ---------------------------------------------------------------------------
# Cross-Device & Smart Home Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/devices", response_model=list[schemas.DeviceNodeResponse])
def list_devices(db: Session = Depends(get_db)):
    """Return all registered device nodes, live refreshing host, mobile, and TV states."""
    # 1. Refresh live host laptop telemetry
    info = device_service.get_real_host_telemetry()
    device_service.update_device_state(db, "laptop-primary", {
        "volume": info.get("volume", 60),
        "cpu": info.get("cpu_percent", 0),
        "ram": info.get("ram_percent", 0),
        **({"battery": info["battery"], "charging": info.get("charging", True)} if "battery" in info else {}),
    })
    laptop = device_service.get_device_by_node_id(db, "laptop-primary")
    if laptop and info.get("ip"):
        laptop.ip_address = info["ip"]
        db.commit()

    # 2. Refresh mobile devices (real ADB probe)
    device_service.check_and_register_mobile_devices(db)

    # 3. Refresh TV state (real socket probe)
    device_service.check_and_register_lg_tv(db)

    return device_service.get_all_devices(db)

from app.scheduler_service import scheduler_service

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing ARYA System Resources...")
    
    # Initialize background auto-healer and discovery
    check_and_register_mobile_devices()
    
    # Initialize Autonomous Scheduler
    scheduler_service.start()
    
    logger.info("ARYA System Initialized and Ready.")


@app.post("/api/devices", response_model=schemas.DeviceNodeResponse)
def register_device(device: schemas.DeviceNodeCreate, db: Session = Depends(get_db)):
    """Register or update a hardware or IoT device."""
    return device_service.register_or_update_device(db, device, status="online")

from pydantic import BaseModel
class LocationWebhook(BaseModel):
    event: str  # e.g., "enter_home", "leave_home"
    lat: float = 0.0
    lng: float = 0.0

@app.post("/api/webhook/location")
async def location_webhook(payload: LocationWebhook, db: Session = Depends(get_db)):
    """Webhook triggered by mobile geofencing apps (Tasker/MacroDroid)."""
    logger.info(f"[GEOFENCE] Received location event: {payload.event}")
    from app.agent_planner import plan
    from app.agent_executor import execute_plan
    
    if payload.event == "enter_home":
        execute_plan(plan("I have arrived home. Turn on the lights and say welcome back sir."))
    elif payload.event == "leave_home":
        execute_plan(plan("I have left home. Turn off the lights and lock the PC."))
        
    return {"status": "processed", "event": payload.event}

@app.post("/api/devices/{node_id}/command", response_model=schemas.DeviceCommandResponse)
async def send_device_command(node_id: str, command: schemas.DeviceCommandRequest, db: Session = Depends(get_db)):
    """Dispatch a remote command to a specific device node."""
    res = await ws_hub.dispatch_device_command(node_id, command.action, command.params)
    if "volume" in command.params:
        device_service.update_device_state(db, node_id, {"volume": command.params["volume"]})
    if command.action in {"turn_on", "turn_off"}:
        device_service.update_device_state(db, node_id, {"power": "on" if command.action == "turn_on" else "off"})

    return schemas.DeviceCommandResponse(
        node_id=node_id,
        action=command.action,
        status=res.get("status", "success"),
        result=res.get("result", str(res))
    )


# ---------------------------------------------------------------------------
# Android & iOS Mobile Integration Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/android/devices")
def get_android_devices():
    """List all connected Android devices over USB and Wireless ADB."""
    from .android_service import android_bridge
    return {
        "adb_available": android_bridge.is_available(),
        "devices": android_bridge.get_connected_devices()
    }


@app.post("/api/android/connect")
def connect_wireless_android(data: dict):
    """Pair or connect to Android over local Wi-Fi (e.g. 192.168.1.15:5555)."""
    from .android_service import android_bridge
    ip = data.get("ip", "").strip()
    port = int(data.get("port", 5555))
    return android_bridge.connect_wireless(ip, port)


@app.post("/api/android/command")
def execute_android_command(data: dict):
    """Directly execute hardware actions on connected Android device."""
    from .android_service import android_bridge
    action = data.get("action", "")
    params = data.get("params", {})
    serial = data.get("serial")
    if action == "lock":
        return android_bridge.lock_screen(serial)
    elif action == "wake":
        return android_bridge.wake_screen(serial)
    elif action == "volume":
        pct = int(params.get("percent", 50))
        return android_bridge.set_volume(pct, serial)
    elif action == "open_app":
        app = params.get("app_name", "youtube")
        return android_bridge.open_app(app, serial)
    elif action == "media":
        return android_bridge.media_play_pause(serial)
    return {"error": f"Unknown action: {action}"}


@app.post("/api/ios/report")
def ios_report_telemetry(data: dict, db: Session = Depends(get_db)):
    """Webhook for Apple Shortcuts to report iPhone/iPad status to ARYA."""
    from .ios_service import ios_bridge
    res = ios_bridge.record_telemetry(data)
    device_service.check_and_register_mobile_devices(db)
    return res


@app.get("/api/ios/action")
def ios_poll_action():
    """Endpoint for Apple Shortcuts automation to fetch queued commands."""
    from .ios_service import ios_bridge
    actions = ios_bridge.pop_pending_actions()
    return {"actions": actions}


@app.post("/api/ios/command")
def ios_queue_command(data: dict):
    """Queue an action to be performed by Apple Shortcuts on iPhone."""
    from .ios_service import ios_bridge
    action = data.get("action", "")
    params = data.get("params", {})
    return ios_bridge.queue_action(action, params)



@app.get("/api/system/status")
def system_status(db: Session = Depends(get_db)):
    """Return system telemetry, AI provider, device counts, and stats."""
    import os
    provider = "Google Gemini 2.0 Flash (Cloud-Native)" if os.getenv("GEMINI_API_KEY") else f"Ollama Local ({os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')})"
    devices = device_service.get_all_devices(db)
    memories_count = len(memory_service.get_all_memories(db))
    tasks_count = len(task_service.get_tasks(db))
    goals_count = len(goal_service.get_goals(db))
    return {
        "status": "online",
        "name": "Project ARYA",
        "version": "2.0.0",
        "ai_gateway": provider,
        "active_devices": len([d for d in devices if d.status == "online"]),
        "total_devices": len(devices),
        "total_memories": memories_count,
        "total_tasks": tasks_count,
        "total_goals": goals_count,
        "connected_websockets": len(ws_hub.active_clients),
        "connected_daemons": len(ws_hub.device_nodes),
    }


# ---------------------------------------------------------------------------
# Real-Time WebSockets
# ---------------------------------------------------------------------------

@app.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket, db: Session = Depends(get_db)):
    """Real-time bi-directional streaming endpoint for 3D Core & Web/PWA frontends."""
    await ws_hub.connect_client(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type", "message")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type in {"user_message", "voice_transcript"}:
                user_msg = data.get("text") or data.get("message", "")
                if not user_msg:
                    continue

                # Notify 3D Core: Thinking
                await ws_hub.broadcast_to_clients({
                    "type": "state_change",
                    "state": "thinking",
                    "message": user_msg
                })

                # Check if agent plan applies
                agent_plan = agent_planner.plan(user_msg)
                if agent_plan:
                    await ws_hub.broadcast_to_clients({
                        "type": "state_change",
                        "state": "executing",
                        "plan": agent_plan
                    })
                    reply = agent_executor.execute(agent_plan)
                else:
                    recent_msgs = conversation_service.get_cached_recent_messages(limit=2)
                    resolved = context_resolver.resolve_message(user_msg, recent_msgs)
                    cached_mems = memory_service.get_cached_memories(db)
                    retrieved = memory_retriever.retrieve_relevant_memories(db, resolved, limit=5, memories=cached_mems)
                    reply = ai_service.ask_ai(resolved, retrieved, recent_msgs, response_length=data.get("response_length", "Normal"))
                    conversation_service.add_messages([("user", user_msg), ("assistant", reply)])

                # Stream reply and change to speaking
                await ws_hub.broadcast_to_clients({
                    "type": "chat_response",
                    "reply": reply,
                    "state": "speaking"
                })

                # Return to idle
                await ws_hub.broadcast_to_clients({
                    "type": "state_change",
                    "state": "idle"
                })

            elif event_type == "device_command":
                target_node = data.get("node_id", "laptop-primary")
                action = data.get("action", "")
                params = data.get("params", {})
                res = await ws_hub.dispatch_device_command(target_node, action, params)
                await websocket.send_json({"type": "device_command_result", "result": res})

    except WebSocketDisconnect:
        ws_hub.disconnect_client(websocket)
    except Exception:
        ws_hub.disconnect_client(websocket)


@app.websocket("/ws/devices/{node_id}")
async def websocket_device_daemon(websocket: WebSocket, node_id: str, db: Session = Depends(get_db)):
    """Direct bi-directional command pipe for remote device daemons (Laptop, IoT, Mobile)."""
    await ws_hub.connect_device(node_id, websocket)
    device_service.update_device_status(db, node_id, "online")
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                device_service.update_device_status(db, node_id, "online")
                if "state" in data:
                    device_service.update_device_state(db, node_id, data["state"])
                await websocket.send_json({"type": "heartbeat_ack"})

            elif msg_type == "command_result":
                cmd_id = data.get("command_id")
                if cmd_id:
                    ws_hub.handle_device_response(cmd_id, data.get("result", {}))

            elif msg_type == "state_update":
                if "state" in data:
                    device_service.update_device_state(db, node_id, data["state"])
                    await ws_hub.broadcast_to_clients({
                        "type": "device_state_update",
                        "node_id": node_id,
                        "state": data["state"]
                    })
    except WebSocketDisconnect:
        ws_hub.disconnect_device(node_id)
        device_service.update_device_status(db, node_id, "offline")
    except Exception:
        ws_hub.disconnect_device(node_id)
        device_service.update_device_status(db, node_id, "offline")


@app.post("/chat", response_model=schemas.ChatResponse)

def chat(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Handle memory commands or send a memory-aware message to qwen3:8b."""
    request_start = performance_service.start_timer()
    performance_service.log_perf("Request received")

    def finish(
        reply: str,
        *,
        memory_ms: float | None = None,
        context_ms: float | None = None,
        ai_ms: float | None = None,
    ) -> schemas.ChatResponse:
        if memory_ms is not None:
            performance_service.log_timing("memory_retrieval", memory_ms)
            print(f"[MEMORY] {memory_ms:.0f} ms")
        if context_ms is not None:
            performance_service.log_timing("context_resolution", context_ms)
            print(f"[CONTEXT] {context_ms:.0f} ms")
        if ai_ms is not None:
            performance_service.log_timing("ai_response", ai_ms)
            print(f"[AI] {ai_ms:.0f} ms")

        total_ms = performance_service.elapsed_ms(request_start)
        performance_service.log_timing("total_response", total_ms)
        print(f"[TOTAL] {total_ms:.0f} ms")
        return schemas.ChatResponse(reply=reply)

    try:
        print(f"[CHAT] Received: {request.message!r}")

        # ---- Agent Core (v1.1) ----------------------------------------
        print("[AGENT] Planning...")
        agent_plan = agent_planner.plan(request.message)
        if agent_plan:
            reply = agent_executor.execute(agent_plan)
            return finish(reply)
        print("[AGENT] No plan — continuing to legacy handlers")

        # ---- Legacy action planner (kept as fallback) ------------------
        print("[CHAT] Action planner attempted")
        planned_actions = action_planner.plan_actions(request.message)
        if planned_actions:
            print(f"[CHAT] Action planner returned {len(planned_actions)} step(s) — executing")
            reply = desktop_actions.execute_action_chain(planned_actions)
            return finish(reply)
        print("[CHAT] Action planner returned nothing — continuing")

        memory_to_save = memory_commands.detect_remember_command(request.message)
        if memory_to_save:
            extracted = memory_extractor.extract_memories(memory_to_save)
            if extracted:
                mem_dict = extracted[0]
                memory = schemas.MemoryCreate(
                    content=mem_dict["content"],
                    category=mem_dict.get("category", "Other")
                )
            else:
                # Treat as a plain Preferences fact if extractor finds nothing
                memory = schemas.MemoryCreate(content=memory_to_save, category="Preferences")
            saved = memory_service.save_memory(db, memory)
            if saved:
                return finish(f"I'll remember that: {saved.content}")
            return finish(f"I couldn't save that — it looks like a command or temporary fact.")

        memory_to_forget = memory_commands.detect_forget_command(request.message)
        if memory_to_forget:
            deleted_count = memory_service.delete_memory(db, memory_to_forget)
            if deleted_count == 0:
                return finish(f"I could not find a memory matching: {memory_to_forget}")
            return finish(f"I forgot {deleted_count} matching memory.")

        goal_to_complete = goal_commands.detect_goal_complete(request.message)
        if goal_to_complete:
            completed_goal = goal_service.complete_goal(db, goal_to_complete)
            if not completed_goal:
                return finish(
                    f"I could not find an active goal matching: {goal_to_complete}"
                )
            return finish(f"Completed goal: {completed_goal.title}")

        goal_to_create = goal_commands.detect_goal_create(request.message)
        if goal_to_create:
            goal = goal_service.create_goal(db, goal_to_create)
            return finish(f"Goal saved: {goal.title}")

        if goal_commands.detect_goal_query(request.message):
            goals = goal_service.get_goals(db)
            if not goals:
                return finish("You do not have any goals yet.")

            goal_lines = "\n".join(
                f"- [{goal.status}] {goal.title}" for goal in goals
            )
            return finish(f"Your goals:\n{goal_lines}")

        task_to_complete = task_commands.detect_task_complete(request.message)
        if task_to_complete:
            completed_task = task_service.complete_task(db, task_to_complete)
            if not completed_task:
                return finish(
                    f"I could not find an active task matching: {task_to_complete}"
                )
            return finish(f"Completed task: {completed_task.title}")

        task_to_create = task_commands.detect_task_create(request.message)
        if task_to_create:
            task = task_service.add_task(db, task_to_create)
            return finish(f"Task added: {task.title}")

        if task_commands.detect_task_query(request.message):
            tasks = task_service.get_tasks(db)
            if not tasks:
                return finish("You do not have any tasks yet.")

            task_lines = "\n".join(
                f"- [{task.status}] {task.title}" for task in tasks
            )
            return finish(f"Your tasks:\n{task_lines}")

        if profile_commands.detect_profile_query(request.message):
            memories = memory_service.get_all_memories(db)
            profile = profile_service.build_profile(memories)
            return finish(profile)

        if memory_commands.detect_memory_query(request.message):
            memories = memory_service.get_all_memories(db)
            if not memories:
                return finish("I do not have any memories yet.")

            memory_lines = "\n".join(f"- {memory.content}" for memory in memories)
            return finish(f"Here is what I remember:\n{memory_lines}")

        news_reply = news_handlers.handle_chat_command(request.message)
        if news_reply is not None:
            return finish(news_reply)

        print("[CHAT] Memory extraction attempted")
        extracted_memories = memory_extractor.extract_memories(request.message)
        if extracted_memories:
            for mem_dict in extracted_memories:
                memory = schemas.MemoryCreate(
                    content=mem_dict["content"],
                    category=mem_dict.get("category", "Other")
                )
                memory_service.save_memory(db, memory)
                print(f"[MEMORY] Saved: {mem_dict['content']!r} [{mem_dict.get('category', 'Other')}]")
        else:
            print("[CHAT] Memory extraction returned [] — no personal facts detected")

        print("[CHAT] Falling back to AI")

        conversation_start = performance_service.start_timer()
        recent_messages = conversation_service.get_cached_recent_messages(limit=2)
        performance_service.log_timing(
            "conversation_history_load",
            performance_service.elapsed_ms(conversation_start),
        )

        context_start = performance_service.start_timer()
        resolved_message = context_resolver.resolve_message(
            request.message, recent_messages
        )
        context_ms = performance_service.elapsed_ms(context_start)

        memory_start = performance_service.start_timer()
        cached_memories = memory_service.get_cached_memories(db)
        memories = memory_retriever.retrieve_relevant_memories(
            db,
            resolved_message,
            limit=5,
            memories=cached_memories,
        )
        memory_ms = performance_service.elapsed_ms(memory_start)

        performance_service.log_perf("AI start")
        ai_start = performance_service.start_timer()
        reply = ai_service.ask_ai(
            resolved_message, 
            memories, 
            recent_messages,
            response_length=request.response_length
        )
        ai_ms = performance_service.elapsed_ms(ai_start)
        performance_service.log_perf("AI finish")

        conversation_service.add_messages(
            [("user", request.message), ("assistant", reply)]
        )

        return finish(
            reply,
            memory_ms=memory_ms,
            context_ms=context_ms,
            ai_ms=ai_ms,
        )
    except Exception as e:
        total_ms = performance_service.elapsed_ms(request_start)
        performance_service.log_timing("total_response", total_ms)
        performance_service.log_perf("Total", total_ms)
        raise HTTPException(status_code=500, detail=f"AI service error: {e}")
