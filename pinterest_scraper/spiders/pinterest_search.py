import scrapy
import json
import re
from datetime import datetime
from urllib.parse import urljoin, quote_plus
from pinterest_scraper.items import PinterestSearchItem, PinterestTrendingItem


class PinterestSearchSpider(scrapy.Spider):
    name = "pinterest_search"
    allowed_domains = ["pinterest.com", "proxy.scrapeops.io"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
    }

    def __init__(self, search_query=None, search_type="pins", max_results=20, *args, **kwargs):
        super(PinterestSearchSpider, self).__init__(*args, **kwargs)
        self.search_query = search_query or "home decor ideas"
        self.search_type = search_type  # pins, boards, users
        self.max_results = int(max_results)
        self.base_url = "https://www.pinterest.com"
        self.results_scraped = 0

    def start_requests(self):
        """Generate initial requests for Pinterest search"""
        
        # Get ScrapeOps API key from settings
        api_key = self.settings.get('SCRAPEOPS_API_KEY')
        
        if self.search_query:
            # Search for specific query
            search_urls = []
            
            if self.search_type == "pins" or self.search_type == "all":
                search_urls.append(f"{self.base_url}/search/pins/?q={quote_plus(self.search_query)}")
            
            if self.search_type == "boards" or self.search_type == "all":
                search_urls.append(f"{self.base_url}/search/boards/?q={quote_plus(self.search_query)}")
            
            if self.search_type == "users" or self.search_type == "all":
                search_urls.append(f"{self.base_url}/search/people/?q={quote_plus(self.search_query)}")
            
            for search_url in search_urls:
                search_type = "pins" if "/pins/" in search_url else ("boards" if "/boards/" in search_url else "users")
                self.logger.info(f"🔍 Searching {search_type} for: {self.search_query}")
                
                # Use ScrapeOps proxy with JavaScript rendering
                proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(search_url)}&render_js=true&wait=3000&residential=false&country=US"
                
                yield scrapy.Request(
                    url=proxy_url,
                    callback=self.parse_search_results,
                    meta={
                        'search_query': self.search_query,
                        'search_type': search_type,
                        'search_url': search_url
                    }
                )
        
        # Also get trending content
        trending_url = f"{self.base_url}/today/"
        self.logger.info("📈 Getting trending Pinterest content")
        
        # Use ScrapeOps proxy for trending content
        proxy_trending_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(trending_url)}&render_js=true&wait=3000&residential=false&country=US"
        
        yield scrapy.Request(
            url=proxy_trending_url,
            callback=self.parse_trending,
            meta={'search_query': 'trending'}
        )

    def parse_search_results(self, response):
        """Parse Pinterest search results"""
        
        search_query = response.meta.get('search_query')
        search_type = response.meta.get('search_type')
        search_url = response.meta.get('search_url')
        
        self.logger.info(f"📊 Parsing {search_type} search results for: {search_query}")
        
        # Extract search metadata
        total_results = self.extract_total_results(response)
        search_suggestions = self.extract_search_suggestions(response)
        
        # Define selectors based on search type
        if search_type == "pins":
            result_selectors = [
                'a[href*="/pin/"]',
                '[data-test-id="pin"]',
                '.pinWrapper',
                '.Pin'
            ]
        elif search_type == "boards":
            result_selectors = [
                'a[href*="/board/"]',
                '[data-test-id="board"]',
                '.boardWrapper',
                '.Board'
            ]
        else:  # users
            result_selectors = [
                'a[href^="/"][href$="/"]',
                '[data-test-id="user"]',
                '.userWrapper',
                '.User'
            ]
        
        results_found = []
        position = 1
        
        for selector in result_selectors:
            results = response.css(selector)
            if results:
                self.logger.info(f"Found {len(results)} {search_type} results using selector: {selector}")
                
                for result in results[:self.max_results]:
                    if self.results_scraped >= self.max_results:
                        break
                    
                    search_item = self.extract_search_result(
                        result, search_query, search_type, search_url, 
                        position, total_results, search_suggestions
                    )
                    
                    if search_item:
                        results_found.append(search_item)
                        position += 1
                        self.results_scraped += 1
                
                break  # Use first successful selector
        
        # Yield all found results
        for item in results_found:
            yield item
        
        self.logger.info(f"✅ Extracted {len(results_found)} {search_type} search results")

    def extract_search_result(self, result_element, search_query, search_type, search_url, position, total_results, suggestions):
        """Extract individual search result"""
        
        item = PinterestSearchItem()
        
        # Search metadata
        item['search_query'] = search_query
        item['search_type'] = search_type
        item['search_url'] = search_url
        item['result_type'] = search_type.rstrip('s')  # pins -> pin, boards -> board, users -> user
        item['position_in_results'] = position
        item['total_results'] = total_results
        item['search_suggestions'] = suggestions
        
        # Extract result URL
        result_url = result_element.css('a::attr(href)').get()
        if result_url:
            item['result_url'] = urljoin(self.base_url, result_url)
            item['result_id'] = self.extract_result_id(result_url, search_type)
        
        # Extract result title/name
        title_selectors = [
            '::attr(alt)',
            '::attr(title)',
            '::text',
            'img::attr(alt)',
            'h3::text',
            'h4::text',
            '.title::text'
        ]
        
        for selector in title_selectors:
            title = result_element.css(selector).get()
            if title and title.strip() and len(title.strip()) > 2:
                item['result_title'] = title.strip()
                break
        
        if not item.get('result_title'):
            item['result_title'] = f"{search_type.rstrip('s').title()} Result"
        
        # Extract description
        desc_selectors = [
            '.description::text',
            '.desc::text',
            'p::text',
            'span::text'
        ]
        
        for selector in desc_selectors:
            description = result_element.css(selector).get()
            if description and description.strip() and len(description.strip()) > 5:
                item['result_description'] = description.strip()
                break
        
        if not item.get('result_description'):
            item['result_description'] = ""
        
        # Extract thumbnail/preview image
        img_selectors = [
            'img::attr(src)',
            '::attr(data-src)',
            '.image img::attr(src)'
        ]
        
        for selector in img_selectors:
            thumbnail = result_element.css(selector).get()
            if thumbnail and ('pinimg' in thumbnail or 'pinterest' in thumbnail):
                item['thumbnail_url'] = thumbnail
                break
        
        if not item.get('thumbnail_url'):
            item['thumbnail_url'] = ""
        
        # Extract creator information
        creator_selectors = [
            '.creator::text',
            '.author::text',
            '.user-name::text',
            '.pinner::text'
        ]
        
        for selector in creator_selectors:
            creator = result_element.css(selector).get()
            if creator and creator.strip():
                item['creator_name'] = creator.strip()
                break
        
        if not item.get('creator_name'):
            item['creator_name'] = ""
        
        # Metadata
        item['scraped_at'] = datetime.now().isoformat()
        item['search_timestamp'] = datetime.now().isoformat()
        
        return item

    def extract_result_id(self, result_url, search_type):
        """Extract ID from result URL"""
        if search_type == "pins":
            match = re.search(r'/pin/(\d+)/', result_url)
            return match.group(1) if match else ""
        elif search_type == "boards":
            # Board URLs are more complex, use the whole path segment
            match = re.search(r'/([^/]+/[^/]+)/?$', result_url.rstrip('/'))
            return match.group(1) if match else ""
        else:  # users
            match = re.search(r'/([^/]+)/?$', result_url.rstrip('/'))
            return match.group(1) if match else ""

    def extract_total_results(self, response):
        """Extract total number of search results"""
        count_selectors = [
            '.results-count::text',
            '[data-test-id="results-count"]::text',
            'span:contains("result")::text'
        ]
        
        for selector in count_selectors:
            count_text = response.css(selector).get()
            if count_text:
                return self.parse_number(count_text)
        
        # Fallback: count visible results
        visible_results = response.css('[data-test-id], .Pin, .Board, .User').getall()
        return len(visible_results) if visible_results else 0

    def extract_search_suggestions(self, response):
        """Extract search suggestions"""
        suggestions = []
        
        suggestion_selectors = [
            '.search-suggestion::text',
            '.related-search::text',
            '[data-test-id="suggestion"]::text'
        ]
        
        for selector in suggestion_selectors:
            found_suggestions = response.css(selector).getall()
            suggestions.extend([s.strip() for s in found_suggestions if s.strip()])
        
        return list(set(suggestions[:10]))  # Remove duplicates, limit to 10

    def parse_trending(self, response):
        """Parse trending content page"""
        
        self.logger.info("📈 Parsing trending Pinterest content")
        
        # Look for trending topics/searches
        trending_selectors = [
            '.trending-topic',
            '.trend',
            '[data-test-id="trending"]',
            '.popular-search'
        ]
        
        trending_items = []
        position = 1
        
        for selector in trending_selectors:
            trends = response.css(selector)
            if trends:
                self.logger.info(f"Found {len(trends)} trending items using selector: {selector}")
                
                for trend in trends[:10]:  # Limit to 10 trending items
                    trending_item = self.extract_trending_item(trend, position)
                    if trending_item:
                        trending_items.append(trending_item)
                        position += 1
                
                break  # Use first successful selector
        

        
        # Yield trending items
        for item in trending_items:
            yield item
        
        self.logger.info(f"✅ Extracted {len(trending_items)} trending items")

    def extract_trending_item(self, trend_element, position):
        """Extract individual trending item"""
        
        item = PinterestTrendingItem()
        
        # Basic trending info
        item['position'] = position
        item['trending_period'] = "today"
        
        # Extract trend name
        name_selectors = [
            '::text',
            'a::text',
            'h3::text',
            '.trend-name::text'
        ]
        
        for selector in name_selectors:
            trend_name = trend_element.css(selector).get()
            if trend_name and trend_name.strip():
                item['trend_name'] = trend_name.strip()
                break
        
        if not item.get('trend_name'):
            return None  # Skip if no trend name found
        
        # Generate trend ID
        item['trend_id'] = f"trend_{position}_{datetime.now().strftime('%Y%m%d')}"
        
        # Determine trend type
        if item['trend_name'].startswith('#'):
            item['trend_type'] = "hashtag"
        else:
            item['trend_type'] = "topic"
        
        # Extract associated links
        links = trend_element.css('a::attr(href)').getall()
        sample_pins = [urljoin(self.base_url, link) for link in links if '/pin/' in link]
        item['sample_pins'] = sample_pins[:5]  # Limit to 5
        
        # Metadata
        item['trending_region'] = "global"
        item['scraped_at'] = datetime.now().isoformat()
        
        return item



    def parse_number(self, text):
        """Parse number from text with K, M, B suffixes"""
        if not text:
            return 0
        
        text = str(text).strip().replace(',', '')
        
        # Handle K, M, B suffixes
        if text.lower().endswith('k'):
            try:
                return int(float(text[:-1]) * 1000)
            except ValueError:
                return 0
        elif text.lower().endswith('m'):
            try:
                return int(float(text[:-1]) * 1000000)
            except ValueError:
                return 0
        elif text.lower().endswith('b'):
            try:
                return int(float(text[:-1]) * 1000000000)
            except ValueError:
                return 0
        else:
            # Extract just numbers
            numbers = re.findall(r'\d+', text)
            if numbers:
                try:
                    return int(numbers[0])
                except ValueError:
                    return 0
        
        return 0 