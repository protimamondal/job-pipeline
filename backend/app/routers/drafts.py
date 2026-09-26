import json
import uuid

from fastapi import APIRouter, Depends,HTTPException,Request
from fastapi.responses import StreamingResponse
from langfuse.openai import AsyncOpenAI
from langfuse import get_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import DraftRequest
from app.db import get_session
from app.db_models import Job, User
from app.dependencies import get_current_user
from app.profile import PROFILE
from app.settings import get_settings

router = APIRouter(prefix="/jobs", tags=["drafts"])

def build_prompt(job: Job, instruction: str|None)->str:
    extra = f"\n\nExtra user instruction: {instruction}" if instruction else ""
    return  f"""consider yourself as the job applicant and create a cover letter
using the job title {job.title} whose description is
{job.description} and this is my profile {PROFILE}

Return the cover letter itself.
- If you use something from the job description, add [[job]].
- If you use something from the profile, add [[profile]].
- Use only [[job]] and [[profile]].
You may use markdown formatting like **bold**.
Do not wrap the answer in triple backticks.
Do not use a markdown code block.
Do not start with ```markdown.
Use 2-3 short paragraphs and bold one important skill match.{extra}"""

async def event_stream(request: Request, prompt: str):
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    text_id = str(uuid.uuid4())
    try:
        #yield event({"type": "text-start", "id": text_id})
        yield f'data:{json.dumps({"type":"text-start","id": text_id})}\n\n'
        async with await client.chat.completions.create(
            model=settings.draft_model,
            messages=[{"role":"user","content":prompt}],
            stream= True,
            ) as stream:
            async for chunk in stream:
                if await request.is_disconnected():
                    break
                text = chunk.choices[0].delta.content
                if text:
                    yield f'data:{json.dumps({"type":"text-delta","id":text_id,"delta":text})}\n\n'
            else:
                yield f'data:{json.dumps({"type":"text-end","id": text_id})}\n\n'
                #yield f'data:{json.dumps({"type":"done"})}\n\n'

    except Exception as exc:
        yield f'data:{json.dumps({"type":"error","errorText":str(exc)})}\n\n'
    await get_client().flush()
    yield "data: [DONE]\n\n"


@router.post("/{job_id}/draft")
async def create_draft(
    job_id: int,
    payload: DraftRequest,
    request: Request,
    cur_user: User = Depends(get_current_user),
    session : AsyncSession = Depends(get_session),
)-> StreamingResponse:
    job = await session.get(Job,job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    prompt = build_prompt(job,payload.instruction)
    return StreamingResponse(
        event_stream(request, prompt),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1"},
    )