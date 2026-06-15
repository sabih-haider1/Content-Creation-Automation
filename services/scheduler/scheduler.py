from fastapi import FastAPI

app = FastAPI(title="Scheduler Service")

@app.post("/schedule")
async def schedule():
    return {"status": "scheduled"}\n