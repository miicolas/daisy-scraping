import subprocess
import re

from .celery_config import celery_app

@celery_app.task(bind=True)
def run_scrapy_spider(self, spider_name: str):
    
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Démarrage du spider...'})
    
    try:
        result = subprocess.run(
            ["scrapy", "crawl", spider_name],
            cwd="./scrapping",
            timeout=1800,
            capture_output=True,
            text=True
        )
        
        items_scraped = 0
        if result.stdout:
            match = re.search(r"'item_scraped_count':\s*(\d+)", result.stdout)
            if match:
                items_scraped = int(match.group(1))
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or 'Erreur inconnue'
            self.update_state(
                state='FAILURE',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': 'Échec du crawl',
                    'error_msg': error_msg,
                    'items_scraped': items_scraped
                }
            )
            raise Exception(f"Erreur lors du crawl: {error_msg}")
        
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Crawl terminé avec succès',
                'items_scraped': items_scraped
            }
        )
                
        return {
            "status": "success",
            "message": f"Crawl {spider_name} terminé avec succès",
            "items_scraped": items_scraped
        }
    except subprocess.TimeoutExpired:
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Timeout',
                'error_msg': f"Timeout: le crawl {spider_name} a pris plus de 30 minutes"
            }
        )
        raise Exception(f"Timeout: le crawl {spider_name} a pris plus de 30 minutes")
    except Exception as e:
        error_msg = str(e)
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Erreur',
                'error_msg': error_msg
            }
        )
        raise
