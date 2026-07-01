"""Agent endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.core.exceptions import NotFoundError
from app.models.agent import Agent
from app.repositories.agent import AgentRepository
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, session: SessionDep, user: CurrentUser) -> Agent:
    repo = AgentRepository(session)
    agent = Agent(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        agent_type=payload.agent_type,
        config=payload.config.model_dump(exclude_none=True),
    )
    return await repo.add(agent)


@router.get("", response_model=Page[AgentRead])
async def list_agents(
    session: SessionDep, page: PaginationDep, user: CurrentUser
) -> Page[AgentRead]:
    repo = AgentRepository(session)
    items = await repo.list_owned(user.id, limit=page.limit, offset=page.offset)
    total = await repo.count_owned(user.id)
    return Page[AgentRead](
        items=[AgentRead.model_validate(a) for a in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> Agent:
    agent = await AgentRepository(session).get(agent_id)
    if agent is None or (agent.owner_id is not None and agent.owner_id != user.id):
        raise NotFoundError("Agent not found")
    return agent


async def _get_owned_agent(session: SessionDep, agent_id: uuid.UUID, user: CurrentUser) -> Agent:
    agent = await AgentRepository(session).get(agent_id)
    # Only the owner may mutate an agent; shared/demo agents (owner_id is None) are
    # read-only so one user can't edit another user's (or the seeded) agent.
    if agent is None or agent.owner_id != user.id:
        raise NotFoundError("Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: uuid.UUID, payload: AgentUpdate, session: SessionDep, user: CurrentUser
) -> Agent:
    """Edit an agent. Sending `config` replaces it wholesale — so a stored secret
    (e.g. an api_key that shouldn't be there) is removed by PATCHing a config
    that omits it."""
    agent = await _get_owned_agent(session, agent_id, user)
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.config is not None:
        agent.config = payload.config.model_dump(exclude_none=True)
    await session.flush()
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> Response:
    repo = AgentRepository(session)
    agent = await _get_owned_agent(session, agent_id, user)
    await repo.delete(agent)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
