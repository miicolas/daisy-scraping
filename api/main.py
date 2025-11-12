import subprocess
import os

from typing import List

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, APIRouter
from sqlmodel import Session, SQLModel, create_engine, select, delete

from .models.atelier import Atelier, AtelierCreate


app = FastAPI()
router = APIRouter(prefix="/api/v1")

postgres_url = "postgresql://postgres:postgres@localhost:5666/db"
engine = create_engine(postgres_url)


def run_spider(spider_name: str):
    try:


        spiders_list = [
            "wecandoo",
        ]

        if spider_name not in spiders_list:
            raise HTTPException(status_code=400, detail=f"Spider {spider_name} non trouvé")


        result = subprocess.run(
            ["scrapy", "crawl", spider_name],
            cwd="./scrapping",
            timeout=1800,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Erreur lors du lancement du crawl: {result.stderr}")
        else:
            return {"status": "Crawl {spider_name} terminé avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement du crawl {spider_name}: {str(e)}")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/ateliers", response_model=List[Atelier])
def get_ateliers(
    session: Session = Depends(get_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=100, ge=1),
    category: str = Query(default=None),
):
    statement = select(Atelier)
    try:
    if category:
        statement = statement.where(Atelier.category == category)
        statement = statement.offset(offset).limit(limit)
        ateliers = session.exec(statement).all()
        return ateliers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des ateliers: {str(e)}")


@router.get("/ateliers/urls", response_model=List[str])
def get_atelier_urls(session: Session = Depends(get_session)):
    try:
        urls = session.exec(select(Atelier.url)).all()
        return list(urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des URLs des ateliers: {str(e)}")
    return list(urls)


@router.get("/ateliers/{atelier_id}", response_model=Atelier)
def get_atelier(atelier_id: int, session: Session = Depends(get_session)):
    try:
        atelier = session.get(Atelier, atelier_id)
        if not atelier:
            raise HTTPException(status_code=404, detail="Atelier not found")
        return atelier
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de l'atelier: {str(e)}")


@router.post("/ateliers/batch", response_model=List[Atelier])
def create_ateliers_batch(ateliers: List[AtelierCreate], session: Session = Depends(get_session)):
    if not ateliers:
        return []
    
    try:
        created_ateliers = []
        
        batch_urls = [a.url for a in ateliers]
        
        existing = session.exec(
            select(Atelier.url).where(Atelier.url.in_(batch_urls))
        ).all()
        existing_urls = set(existing)
        
        for atelier_data in ateliers:
            if atelier_data.url in existing_urls:
                continue
            
            try:
                db_atelier = Atelier.model_validate(atelier_data)
                session.add(db_atelier)
                existing_urls.add(atelier_data.url)
                created_ateliers.append(db_atelier)
            except Exception as e:
                continue
        
        if created_ateliers:
            session.commit()
            for atelier in created_ateliers:
                try:
                    session.refresh(atelier)
                except:
                    pass
        
        return created_ateliers
    
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création des ateliers: {str(e)}")

@router.delete("/ateliers-all/", response_model=dict)
def delete_ateliers(session: Session = Depends(get_session)):

    try:
        session.exec(delete(Atelier))
        session.commit()
        return {"message": "Tous les ateliers ont été supprimés"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression des ateliers: {str(e)}")

@router.post("/start-crawl/{spider_name}")
def start_crawl(background_tasks: BackgroundTasks, spider_name: str):
    try:
        background_tasks.add_task(run_spider, spider_name)
        return {"status": "Crawl started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la démarrage du crawl: {str(e)}")

app.include_router(router)