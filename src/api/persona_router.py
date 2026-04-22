# src/api/persona_router.py
import json

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/persona")
async def get_persona(request: Request):
    return request.app.state.persona.model_dump()


@router.post("/persona/update")
async def update_persona(request: Request):
    body = await request.json()
    field = body.get("field", "")
    value = body.get("value")

    persona_engine = request.app.state.persona_engine
    persona_engine.update_persona_field(field, value)

    request.app.state.persona = persona_engine.load_persona()

    request.app.state.git_manager.commit(f"persona update: {field}")

    return {"status": "ok", "field": field}


@router.post("/persona/apply-template")
async def apply_template(request: Request):
    body = await request.json()
    template_id = body.get("template_id", "default")

    persona_engine = request.app.state.persona_engine
    persona = persona_engine.apply_template(template_id)
    request.app.state.persona = persona

    request.app.state.git_manager.commit(f"apply template: {template_id}")

    return {"status": "ok", "template": template_id, "persona": persona.model_dump()}
