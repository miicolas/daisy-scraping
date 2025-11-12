from playwright.async_api import async_playwright
import scrapy
from scrapy.http import HtmlResponse
from tutorial.items import TutorialItem


class AteliersSpider(scrapy.Spider):
    name = "ateliers"
    start_urls = ["https://wecandoo.fr/ateliers"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(kwargs.get('max_pages', 10))
        self.scroll_attempts = int(kwargs.get('scroll_attempts', 5))
        self.seen_urls = set()  # Pour éviter les doublons dans la même session
    
    async def parse(self, response):
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto(response.url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            previous_count = 0
            for scroll_count in range(self.scroll_attempts):
                current_count = await page.locator("a[href*='/atelier/']").count()
                if current_count == previous_count:
                    break
                previous_count = current_count
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
            
            html = await page.content()
            await browser.close()

        rendered_response = HtmlResponse(
            url=response.url,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )
        
        page_num = response.meta.get('page_num', 1)
        atelier_links = rendered_response.css("a[href*='/atelier/']")
        
        for atelier in atelier_links:
            url = atelier.css("::attr(href)").get()
            if not url:
                continue
            
            url = response.urljoin(url) if not url.startswith('http') else url
            
            if url in self.seen_urls:
                continue
            
            self.seen_urls.add(url)
            
            spans = atelier.css("p.w-typo--caption span::text").getall()
            
            yield TutorialItem(
                title=atelier.css("h3::text").get(),
                url=url,
                category=atelier.css("p.w-typo--footnote-serif::text").get(),
                price=atelier.css("span.w-typo--h6 span::text").get(),
                duration=spans[0] if spans else None,
                location=spans[1] if len(spans) > 1 else None,
            )
        
        if page_num < self.max_pages:
            for link in rendered_response.css("a[href*='page='], a[href*='/ateliers?']"):
                next_url = link.css("::attr(href)").get()
                if next_url:
                    yield scrapy.Request(
                        response.urljoin(next_url),
                        callback=self.parse,
                        meta={'page_num': page_num + 1}
                    )
            
