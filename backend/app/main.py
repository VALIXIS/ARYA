"""
main.py
-------
Entry point for the ARYA backend. Defines the FastAPI app and wires
together memory, goals, tasks, desktop actions, conversation context,
profile building, and AI chat.
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

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
    news_handlers,
    performance_service,
    profile_commands,
    profile_service,
    task_commands,
    task_service,
    ai_service,
)
from .database import engine, get_db

# Create database tables on startup if they don't already exist.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARYA Sprint 1")


@app.post("/memory", response_model=schemas.MemoryResponse)
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
            performance_service.log_perf("Memory", memory_ms)
        if context_ms is not None:
            performance_service.log_timing("context_resolution", context_ms)
            performance_service.log_perf("Context", context_ms)
        if ai_ms is not None:
            performance_service.log_timing("ai_response", ai_ms)
            performance_service.log_perf("AI", ai_ms)

        total_ms = performance_service.elapsed_ms(request_start)
        performance_service.log_timing("total_response", total_ms)
        performance_service.log_perf("Total", total_ms)
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
            memory = schemas.MemoryCreate(content=memory_to_save)
            memory_service.save_memory(db, memory)
            return finish(f"I'll remember that: {memory_to_save}")

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
        recent_messages = conversation_service.get_cached_recent_messages(limit=4)
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
            limit=3,
            memories=cached_memories,
        )
        memory_ms = performance_service.elapsed_ms(memory_start)

        performance_service.log_perf("AI start")
        ai_start = performance_service.start_timer()
        reply = ai_service.ask_ai(resolved_message, memories, recent_messages)
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
