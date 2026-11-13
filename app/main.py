"""DyslexiaScreen backend: login, child profiles, three screening modules,
combined Reading Difficulty Index report, and the Model Lab results."""
import os, json
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from .db import init_db, get_db, User, Child, Assessment
from .auth import hash_password, check_password, make_token, current_user
from .ml import fusion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, 'artifacts')
app = FastAPI(title="DyslexiaScreen API", version="1.0")
init_db()


# ---------------------------------------------------------------- schemas
class RegisterIn(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "teacher"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChildIn(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=5, le=17)
    gender: str = "female"
    native_speaker: bool = True
    other_language: bool = False
    school: str = ""


class GameItem(BaseModel):
    q: int
    clicks: float
    hits: float
    misses: float


class GameIn(BaseModel):
    child_id: int
    items: List[GameItem]
    duration_s: Optional[float] = None


class EyeIn(BaseModel):
    child_id: int
    tasks: dict
    camera: Optional[str] = None
    calibration_error_px: Optional[float] = None


def child_of(user, child_id, db) -> Child:
    c = db.get(Child, child_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(404, "Child not found.")
    return c


def save(db, child, module, risk, label, payload):
    a = Assessment(child_id=child.id, module=module, risk=risk, label=label, payload=json.dumps(payload))
    db.add(a); db.commit(); db.refresh(a)
    return a


def user_out(u):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


def child_out(c: Child):
    last = {}
    for a in c.assessments:
        last[a.module] = {"id": a.id, "risk": a.risk, "label": a.label, "date": a.created_at.isoformat()}
    r = fusion.rdi({k: v["risk"] for k, v in last.items()})
    return {"id": c.id, "name": c.name, "age": c.age, "gender": c.gender, "native_speaker": c.native_speaker,
            "other_language": c.other_language, "school": c.school, "created_at": c.created_at.isoformat(),
            "latest": last, "rdi": r}


# ---------------------------------------------------------------- auth
@app.post("/api/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(func.lower(User.email) == body.email.lower()).first():
        raise HTTPException(400, "An account with this email already exists. Try logging in.")
    u = User(name=body.name.strip(), email=body.email.lower(), password_hash=hash_password(body.password), role=body.role)
    db.add(u); db.commit(); db.refresh(u)
    return {"token": make_token(u), "user": user_out(u)}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(func.lower(User.email) == body.email.lower()).first()
    if not u or not check_password(body.password, u.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    return {"token": make_token(u), "user": user_out(u)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


# ---------------------------------------------------------------- children
@app.get("/api/children")
def list_children(user: User = Depends(current_user), db: Session = Depends(get_db)):
    kids = db.query(Child).filter(Child.user_id == user.id).order_by(Child.created_at.desc()).all()
    return [child_out(c) for c in kids]


@app.post("/api/children")
def add_child(body: ChildIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = Child(user_id=user.id, **body.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return child_out(c)


@app.get("/api/children/{cid}")
def get_child(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return child_out(child_of(user, cid, db))


@app.delete("/api/children/{cid}")
def delete_child(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = child_of(user, cid, db); db.delete(c); db.commit()
    return {"ok": True}


@app.get("/api/children/{cid}/report")
def report(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = child_of(user, cid, db)
    latest = {}
    for a in c.assessments:
        latest[a.module] = a
    modules = {k: {"id": a.id, "risk": a.risk, "label": a.label, "date": a.created_at.isoformat(),
                   "result": json.loads(a.payload).get("result")} for k, a in latest.items()}
    history = [{"id": a.id, "module": a.module, "risk": a.risk, "label": a.label, "date": a.created_at.isoformat()}
               for a in c.assessments]
    return {"child": child_out(c), "modules": modules, "rdi": fusion.rdi({k: v["risk"] for k, v in modules.items()}),
            "history": history, "generated_at": datetime.utcnow().isoformat(), "screener": user.name}


@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    kids = db.query(Child).filter(Child.user_id == user.id).all()
    outs = [child_out(c) for c in kids]
    n_assess = sum(len(c.assessments) for c in kids)
    referred = sum(1 for o in outs if o["rdi"] and o["rdi"]["refer"])
    by_module = {}
    for c in kids:
        for a in c.assessments:
            by_module[a.module] = by_module.get(a.module, 0) + 1
    return {"children": len(kids), "assessments": n_assess, "referred": referred, "by_module": by_module,
            "recent": sorted(outs, key=lambda o: o["created_at"], reverse=True)[:6]}


# ---------------------------------------------------------------- module 1: gamified test
@app.post("/api/game/predict")
def game_predict(body: GameIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .ml import game
    c = child_of(user, body.child_id, db)
    res = game.predict_from_items(c, [i.model_dump() for i in body.items])
    a = save(db, c, "game", res["risk"], res["label"], {"input": body.model_dump(), "result": res})
    return {"assessment_id": a.id, **res}


@app.get("/api/game/sample")
def game_sample(dyslexia: Optional[int] = None, user: User = Depends(current_user)):
    from .ml import game
    return game.dataset_sample(dyslexia)


# ---------------------------------------------------------------- module 2: handwriting
@app.post("/api/handwriting/predict")
async def hw_predict(child_id: int = Form(...), images: List[UploadFile] = File(...),
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .ml import handwriting
    c = child_of(user, child_id, db)
    blobs = [await f.read() for f in images]
    res = handwriting.predict_images(blobs)
    slim = {k: v for k, v in res.items()}
    a = save(db, c, "handwriting", res["risk"], res["label"], {"result": slim})
    return {"assessment_id": a.id, **res}


@app.post("/api/handwriting/sheet")
async def hw_sheet(child_id: int = Form(...), image: UploadFile = File(...),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .ml import handwriting
    c = child_of(user, child_id, db)
    res = handwriting.predict_sheet(await image.read())
    a = save(db, c, "handwriting", res["risk"], res["label"], {"result": res})
    return {"assessment_id": a.id, **res}


# ---------------------------------------------------------------- module 3: eye tracking
@app.post("/api/eye/analyze")
def eye_analyze(body: EyeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .ml import eye
    c = child_of(user, body.child_id, db)
    res = eye.analyse(body.tasks)
    res["label"] = "Atypical reading pattern" if res["risk"] >= 0.5 else "Typical reading pattern"
    res["camera"] = body.camera; res["calibration_error_px"] = body.calibration_error_px
    a = save(db, c, "eye", res["risk"], res["label"], {"result": res})
    return {"assessment_id": a.id, **res}


_etdd = None


@app.get("/api/eye/sample")
def eye_sample(dyslexia: Optional[int] = None, user: User = Depends(current_user)):
    global _etdd
    import random
    if _etdd is None:
        _etdd = json.load(open(os.path.join(ART, "etdd_samples.json")))
    kids = [k for k in _etdd["children"] if dyslexia is None or k["y"] == int(dyslexia)]
    k = random.choice(kids)
    return {**k, "label": "Atypical reading pattern" if k["risk"] >= 0.5 else "Typical reading pattern",
            "model": "Heterogeneous ensemble (LR, SVM, KNN, MLP, Extra Trees)"}


# ---------------------------------------------------------------- model lab
@app.get("/api/lab")
def lab():
    out = {}
    for k in ["game", "handwriting", "eye"]:
        p = os.path.join(ART, f"lab_{k}.json")
        if os.path.exists(p):
            out[k] = json.load(open(p))
    return out


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------- frontend
STATIC = os.path.join(ROOT, "static")
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    f = os.path.join(STATIC, path)
    if path and os.path.isfile(f):
        return FileResponse(f)
    return FileResponse(os.path.join(STATIC, "index.html"))
