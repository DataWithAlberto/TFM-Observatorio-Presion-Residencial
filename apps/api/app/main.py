import json,logging,time,uuid
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import get_settings
from app.core.database import get_engine
from app.routers.observatory import router
logging.basicConfig(level=logging.INFO,format="%(message)s"); log=logging.getLogger("observatorio")
settings=get_settings(); app=FastAPI(title=settings.app_name,version="1.0.0",docs_url="/api/docs",openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api/v1",tags=["observatorio"])
@app.middleware("http")
async def timing(req:Request,call_next):
    start=time.perf_counter(); rid=req.headers.get("x-request-id",str(uuid.uuid4())); res=await call_next(req)
    res.headers["x-request-id"]=rid; log.info(json.dumps({"request_id":rid,"path":req.url.path,"status":res.status_code,"duration_ms":round((time.perf_counter()-start)*1000,2)})); return res
@app.get("/health")
def health(): return {"status":"ok","version":app.version}
@app.get("/ready")
def ready():
    try:
        with get_engine().connect() as c: c.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status":"unavailable"},status_code=503)
    return {"status":"ready"}
