from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Web Search Service")

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search(req: SearchRequest):
    # TODO: Implement Tavily/Serper search
    return {"facts": [f"Fact about {req.query}"], "sources": ["https://example.com"]}\n