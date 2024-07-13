from collections import namedtuple

import asyncpg.pool

SnippetHeader = namedtuple(
    "SnippetHeader",
    ["id", "name", "content", "uses", "owner_id", "location_id", "created_at"],
)


async def get_snippet(
    pool: asyncpg.pool.Pool, guild_id: int, owner_id: int, snippet_name: str
):
    fields_str = ",".join(SnippetHeader._fields)
    query = f"""
    SELECT {fields_str} from snippets
    WHERE location_id = $1 AND owner_id = $2 AND name = $3
    """
    row = await pool.fetchrow(query, guild_id, owner_id, snippet_name)
    if not row:
        return None
    return SnippetHeader(*row)


async def create_snippet(
    pool: asyncpg.pool.Pool,
    guild_id: int,
    owner_id: int,
    snippet_name: str,
    snippet_text: str,
):
    query = """
        INSERT INTO snippets (owner_id, location_id, name, content)
        VALUES ($1, $2, $3, $4)
        """
    await pool.execute(query, guild_id, owner_id, snippet_name, snippet_text)
