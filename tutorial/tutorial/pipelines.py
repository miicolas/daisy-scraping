# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import re
from urllib.parse import urljoin
import requests


class TutorialPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        if adapter.get('title'):
            adapter['title'] = adapter['title'].strip()
        
        if adapter.get('category'):
            adapter['category'] = adapter['category'].strip()
        
        if adapter.get('price'):
            price_str = adapter['price'].strip()
            price_match = re.search(r'(\d+)', price_str)
            if price_match:
                adapter['price'] = int(price_match.group(1))
            else:
                adapter['price'] = None
        
        if adapter.get('duration'):
            adapter['duration'] = adapter['duration'].strip()
        
        if adapter.get('location'):
            location = adapter['location'].strip()
            adapter['location'] = location if location else None
        else:
            adapter['location'] = None
        
        if adapter.get('url'):
            url = adapter['url'].strip()
            if url and not url.startswith('http'):
                base_url = 'https://wecandoo.fr'
                adapter['url'] = urljoin(base_url, url)
        
        return item


class DatabasePipeline:
    """Pipeline pour collecter les nouveaux ateliers et les envoyer à l'API à la fin du scraping."""
    
    def __init__(self):
        self.api_url = "http://localhost:8000"
        self.batch_url = f"{self.api_url}/ateliers/batch"
        self.urls_url = f"{self.api_url}/ateliers/urls"
        self.new_ateliers = []
        self.existing_urls = set()
    
    def open_spider(self, spider):
        self.new_ateliers = []
        self.existing_urls = set()
        
        try:
            spider.logger.info("Chargement des URLs existantes depuis l'API...")
            response = requests.get(self.urls_url, timeout=10)
            if response.status_code == 200:
                self.existing_urls = set(response.json())
                spider.logger.info(f"{len(self.existing_urls)} URLs existantes chargées - les doublons seront ignorés")
            else:
                spider.logger.warning(f"Impossible de charger les URLs existantes: {response.status_code}")
        except requests.exceptions.ConnectionError:
            spider.logger.warning("Impossible de se connecter à l'API pour charger les URLs existantes. Les doublons seront filtrés lors de l'envoi.")
        except Exception as e:
            spider.logger.warning(f"Erreur lors du chargement des URLs existantes: {str(e)}")
        
        spider.logger.info("DatabasePipeline initialisé - les ateliers seront envoyés à l'API à la fin du scraping")
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        if not adapter.get('url') or not adapter.get('title'):
            spider.logger.warning(f"Item incomplet ignoré: {item}")
            return item
        
        price = adapter.get('price')
        if price is not None:
            price = float(price)
        
        url = adapter.get('url')
        
        if url in self.existing_urls:
            spider.logger.debug(f"Atelier déjà en DB, ignoré: {url}")
            return item
        
        if any(a['url'] == url for a in self.new_ateliers):
            spider.logger.debug(f"Atelier déjà dans la liste, ignoré: {url}")
            return item
        
        atelier_data = {
            "title": adapter.get('title'),
            "url": url,
            "category": adapter.get('category'),
            "price": price,
            "duration": adapter.get('duration'),
            "location": adapter.get('location'),
        }
        
        self.new_ateliers.append(atelier_data)
        spider.logger.debug(f"Atelier ajouté à la liste: {atelier_data['title']}")
        
        return item
    
    def close_spider(self, spider):
        """Envoie tous les nouveaux ateliers à l'API via POST."""
        if not self.new_ateliers:
            spider.logger.info("Aucun nouvel atelier à envoyer")
            return
        
        spider.logger.info(f"Envoi de {len(self.new_ateliers)} nouveaux ateliers à l'API...")
        
        total_created = 0
        batch_size = 50
        
        for i in range(0, len(self.new_ateliers), batch_size):
            batch = self.new_ateliers[i:i+batch_size]
            batch_num = i//batch_size + 1
            
            try:
                response = requests.post(
                    self.batch_url,
                    json=batch,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    created = response.json()
                    total_created += len(created)
                else:
                    spider.logger.error(f"Erreur lors de l'envoi du lot {batch_num}: {response.status_code} - {response.text[:200]}")
            
            except requests.exceptions.ConnectionError:
                spider.logger.error(f"Impossible de se connecter à l'API pour le lot {batch_num}. L'API est-elle démarrée?")
            except requests.exceptions.Timeout:
                spider.logger.error(f"Timeout lors de l'envoi du lot {batch_num}")
            except Exception as e:
                spider.logger.error(f"Erreur inattendue lors de l'envoi du lot {batch_num}: {str(e)}")
        
        spider.logger.info(f"Total: {total_created} ateliers créés avec succès sur {len(self.new_ateliers)} envoyés")
