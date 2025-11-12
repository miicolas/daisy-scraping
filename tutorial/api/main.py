from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, SQLModel, create_engine, select, delete

from .models.atelier import Atelier, AtelierCreate

app = FastAPI()

postgres_url = "postgresql://postgres:postgres@localhost:5666/db"
engine = create_engine(postgres_url)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/ateliers", response_model=List[Atelier])
def get_ateliers(
    session: Session = Depends(get_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=100, ge=1),
    category: str = Query(default=None),
):
    """Récupère la liste des ateliers avec pagination et filtrage optionnel par catégorie."""
    statement = select(Atelier)
    
    if category:
        statement = statement.where(Atelier.category == category)
    
    statement = statement.offset(offset).limit(limit)
    ateliers = session.exec(statement).all()
    return ateliers


@app.get("/ateliers/urls", response_model=List[str])
def get_atelier_urls(session: Session = Depends(get_session)):
    """Récupère toutes les URLs des ateliers existants pour éviter les doublons."""
    urls = session.exec(select(Atelier.url)).all()
    return list(urls)


@app.get("/ateliers/{atelier_id}", response_model=Atelier)
def get_atelier(atelier_id: int, session: Session = Depends(get_session)):
    """Récupère un atelier par son ID."""
    atelier = session.get(Atelier, atelier_id)
    if not atelier:
        raise HTTPException(status_code=404, detail="Atelier not found")
    return atelier


@app.post("/ateliers/batch", response_model=List[Atelier])
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

@app.delete("/ateliers-all/", response_model=dict)
def delete_ateliers(session: Session = Depends(get_session)):
    """Supprime tous les ateliers."""
    session.exec(delete(Atelier))
    session.commit()
    return {"message": "Tous les ateliers ont été supprimés"}