from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, APIRouter, Path
from sqlmodel import Session, SQLModel, create_engine, select, delete

from .models.atelier import Atelier, AtelierCreate
from .models.crawl_log import CrawlLog, CrawlStatus

from .tasks import run_scrapy_spider
from .celery_config import celery_app

import enum
from datetime import datetime

# Enum pour les spiders
class Spiders(str, enum.Enum):
    wecandoo = "wecandoo"


app = FastAPI()
router = APIRouter(prefix="/api/v1")

postgres_url = "postgresql://postgres:postgres@localhost:5666/db"
engine = create_engine(postgres_url)

# Création des tables dans la base de données
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Fonction pour obtenir une session de la base de données
def get_session():
    with Session(engine) as session:
        yield session


# Événement de démarrage de l'application
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# Route pour la racine de l'API
@router.get("/")
async def root():
    return {"message": "Hello World"}


# Route pour récupérer tous les ateliers
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
        return HTTPException(status_code=500, detail=f"Erreur lors de la récupération des ateliers: {str(e)}")


# Route pour récupérer toutes les URLs des ateliers
@router.get("/ateliers/urls", response_model=List[str])
def get_atelier_urls(session: Session = Depends(get_session)):
    try:
        urls = session.exec(select(Atelier.url)).all()
        return {"status": "success", "message": "URLs des ateliers récupérées avec succès", "urls": list(urls)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des URLs des ateliers: {str(e)}")


# Route pour récupérer un atelier par son ID
@router.get("/ateliers/{atelier_id}", response_model=Atelier)
def get_atelier(atelier_id: int, session: Session = Depends(get_session)):
    try:
        atelier = session.get(Atelier, atelier_id)
        if not atelier:
            raise HTTPException(status_code=404, detail="Atelier not found")
        return atelier
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de l'atelier: {str(e)}")


# Route pour créer plusieurs ateliers en batch
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
        
        return {"status": "success", "message": "Tous les ateliers ont été créés avec succès", "ateliers": created_ateliers}
    
    except Exception as e:
        session.rollback()
        return HTTPException(status_code=500, detail=f"Erreur lors de la création des ateliers: {str(e)}")

# Route pour supprimer tous les ateliers
@router.delete("/ateliers-all/")
def delete_ateliers(session: Session = Depends(get_session)):

    try:
        session.exec(delete(Atelier))
        session.commit()
        return {"status": "success", "message": "Tous les ateliers ont été supprimés avec succès"}
    except Exception as e:
        session.rollback()
        return HTTPException(status_code=500, detail=f"Erreur lors de la suppression des ateliers: {str(e)}")

# Route pour démarrer un crawl
@router.post("/start-crawl/{spider_name}")
def start_crawl(spider_name: Spiders = Path(...), session: Session = Depends(get_session)):
    try:
        result = run_scrapy_spider.delay(spider_name.value)
        
        crawl_log = CrawlLog(
            task_id=result.id,
            spider_name=spider_name.value,
            status=CrawlStatus.PENDING.value
        )
        session.add(crawl_log)
        session.commit()
        
        return {"task_id": result.id, "status": "started", "message": f"crawl {spider_name.value} démarré avec succès"}
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement du crawl: {error_msg}")


# Route pour récupérer le statut d'un crawl par son ID
@router.get("/start-crawl/status/{task_id}")
def get_crawl_status(task_id: str, session: Session = Depends(get_session)):
    try:
        task = celery_app.AsyncResult(task_id)
        
        crawl_log = session.exec(select(CrawlLog).where(CrawlLog.task_id == task_id)).first()
        if not crawl_log:
            crawl_log = CrawlLog(
                task_id=task_id,
                spider_name="unknown",
                status=task.state or "UNKNOWN"
            )
            session.add(crawl_log)
        
        celery_state = task.state or "UNKNOWN"
        
        if celery_state == "SUCCESS":
            crawl_log.status = CrawlStatus.SUCCESS.value
        elif celery_state == "FAILURE" or celery_state == "FAILED":
            crawl_log.status = CrawlStatus.FAILED.value
        elif celery_state == "PROGRESS":
            crawl_log.status = CrawlStatus.PROGRESS.value
        elif celery_state == "PENDING":
            crawl_log.status = CrawlStatus.PENDING.value
        elif celery_state == "STARTED":
            crawl_log.status = CrawlStatus.STARTED.value
        else:
            crawl_log.status = celery_state
        
        crawl_log.updated_at = datetime.utcnow()
        session.add(crawl_log)
        session.commit()
        session.refresh(crawl_log)
        
        return {
            "task_id": task_id,
            "celery_state": task.state,
            "celery_info": task.info if task.info else None,
            "status": crawl_log.status,
            "error_message": crawl_log.error_message,
            "items_scraped": crawl_log.items_scraped,
            "created_at": crawl_log.created_at.isoformat() if crawl_log.created_at else None,
            "completed_at": crawl_log.completed_at.isoformat() if crawl_log.completed_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {str(e)}")




app.include_router(router)