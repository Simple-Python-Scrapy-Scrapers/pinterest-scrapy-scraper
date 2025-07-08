import scrapy
import json
import re
from datetime import datetime
from urllib.parse import urljoin, quote_plus
from pinterest_scraper.items import PinterestPinItem


class PinterestPinsSpider(scrapy.Spider):
    name = "pinterest_pins"
    allowed_domains = ["pinterest.com", "proxy.scrapeops.io"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
    }

    def __init__(self, search_query=None, max_pins=20, category=None, *args, **kwargs):
        super(PinterestPinsSpider, self).__init__(*args, **kwargs)
        self.search_query = search_query or "home decor"
        self.max_pins = int(max_pins)
        self.category = category
        self.base_url = "https://www.pinterest.com"
        self.pins_scraped = 0

    def start_requests(self):
        """Generate initial requests for Pinterest pins"""
        
        # Get ScrapeOps API key from settings
        api_key = self.settings.get('SCRAPEOPS_API_KEY')
        
        # If specific search query provided
        if self.search_query:
            search_url = f"{self.base_url}/search/pins/?q={quote_plus(self.search_query)}"
            self.logger.info(f"🔍 Searching Pinterest for: {self.search_query}")
            
            # Use ScrapeOps proxy with JavaScript rendering
            proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(search_url)}&render_js=true&wait=3000&residential=false&country=US"
            
            yield scrapy.Request(
                url=proxy_url,
                callback=self.parse_search_results,
                meta={'search_query': self.search_query}
            )
        
        # If category provided
        elif self.category:
            category_url = f"{self.base_url}/search/pins/?q={quote_plus(self.category)}"
            
            # Use ScrapeOps proxy with JavaScript rendering
            proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(category_url)}&render_js=true&wait=3000&residential=false&country=US"
            
            yield scrapy.Request(
                url=proxy_url,
                callback=self.parse_search_results,
                meta={'search_query': self.category}
            )
        
        # Default: popular pins
        else:
            popular_queries = [
                "home decor", "fashion", "food recipes", "travel", "wedding",
                "interior design", "art", "photography", "diy projects"
            ]
            
            for query in popular_queries[:3]:  # Limit to first 3 queries
                search_url = f"{self.base_url}/search/pins/?q={quote_plus(query)}"
                
                # Use ScrapeOps proxy with JavaScript rendering
                proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(search_url)}&render_js=true&wait=3000&residential=false&country=US"
                
                yield scrapy.Request(
                    url=proxy_url,
                    callback=self.parse_search_results,
                    meta={'search_query': query}
                )

    def parse_search_results(self, response):
        """Parse Pinterest search results page to extract pin links"""
        
        search_query = response.meta.get('search_query')
        self.logger.info(f"📍 Parsing search results for: {search_query}")
        
        # Get ScrapeOps API key from settings
        api_key = self.settings.get('SCRAPEOPS_API_KEY')
        
        # Look for pin links using multiple selectors
        pin_selectors = [
            'a[href*="/pin/"]::attr(href)',
            '[data-test-id="pin"] a::attr(href)',
            '.pinWrapper a::attr(href)',
            '.Pin a::attr(href)',
            'a[href*="/pin/"]:not([href*="/search/"])::attr(href)'
        ]
        
        pin_links = []
        for selector in pin_selectors:
            found_links = response.css(selector).getall()
            if found_links:
                self.logger.info(f"Found {len(found_links)} pin links using selector: {selector}")
                for link in found_links:
                    if link and '/pin/' in link and len(link) > 10:
                        full_url = urljoin(self.base_url, link)
                        if full_url not in pin_links:
                            pin_links.append(full_url)
                break  # Use first successful selector
        
        # If no pin links found, try alternative approach
        if not pin_links:
            pin_links = self.extract_pins_from_scripts(response)
        
        self.logger.info(f"✅ Found {len(pin_links)} unique pin URLs")
        
        # Follow pin links
        for pin_url in pin_links[:self.max_pins]:
            if self.pins_scraped >= self.max_pins:
                break
            
            # Use ScrapeOps proxy with JavaScript rendering for pin pages
            proxy_pin_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(pin_url)}&render_js=true&wait=3000&residential=false&country=US"
                
            yield scrapy.Request(
                url=proxy_pin_url,
                callback=self.parse_pin,
                meta={
                    'search_query': search_query,
                    'pin_url': pin_url
                }
            )
            self.pins_scraped += 1

    def extract_pins_from_scripts(self, response):
        """Extract pin URLs from JavaScript/JSON data"""
        pin_links = []
        
        # Look for JSON data in script tags
        scripts = response.css('script::text').getall()
        
        for script in scripts:
            if 'pin' in script.lower() and '/pin/' in script:
                # Use regex to find pin URLs in JavaScript
                pin_matches = re.findall(r'/pin/\d+/', script)
                
                for match in pin_matches:
                    full_url = urljoin(self.base_url, match)
                    if full_url not in pin_links:
                        pin_links.append(full_url)
                
                if pin_links:
                    self.logger.info(f"Found {len(pin_links)} pins in page scripts")
                    break
        
        return pin_links[:20]  # Limit to 20 pins

    def parse_pin(self, response):
        """Parse individual Pinterest pin page"""
        
        search_query = response.meta.get('search_query')
        pin_url = response.meta.get('pin_url', response.url)
        
        self.logger.info(f"📌 Parsing pin: {pin_url}")
        
        item = PinterestPinItem()
        
        # Basic pin information
        item['pin_url'] = pin_url
        item['pin_id'] = self.extract_pin_id(pin_url)
        item['title'] = self.extract_pin_title(response)
        item['description'] = self.extract_pin_description(response)
        
        # Media information
        item['image_url'] = self.extract_image_url(response)
        item['media_type'] = self.extract_media_type(response)
        
        # Board information
        item['board_name'] = self.extract_board_name(response)
        item['board_url'] = self.extract_board_url(response)
        
        # Pinner information
        item['pinner_username'] = self.extract_pinner_username(response)
        item['pinner_name'] = self.extract_pinner_name(response)
        item['pinner_url'] = self.extract_pinner_url(response)
        
        # Engagement metrics
        item['pin_likes'] = self.extract_pin_likes(response)
        item['pin_comments'] = self.extract_pin_comments(response)
        item['pin_repins'] = self.extract_pin_repins(response)
        
        # Source information
        item['source_url'] = self.extract_source_url(response)
        item['source_domain'] = self.extract_source_domain(response)
        
        # Categories and topics
        item['tags'] = self.extract_pin_tags(response)
        item['topics'] = self.extract_pin_topics(response)
        
        # Technical metadata
        item['scraped_at'] = datetime.now().isoformat()
        item['scraper_version'] = "1.0"
        
        # Shopping information
        item['is_shoppable'] = self.extract_shoppable_status(response)
        item['product_price'] = self.extract_product_price(response)
        
        yield item

    def extract_pin_id(self, pin_url):
        """Extract pin ID from URL"""
        # Pinterest pin URLs format: /pin/PIN_ID/
        match = re.search(r'/pin/(\d+)/', pin_url)
        return match.group(1) if match else ""

    def extract_pin_title(self, response):
        """Extract pin title with multiple selectors"""
        selectors = [
            'h1::text',
            '[data-test-id="pin-title"]::text',
            '.Pin-title::text',
            'title::text',
            'meta[property="og:title"]::attr(content)',
            '[role="heading"]::text'
        ]
        
        for selector in selectors:
            title = response.css(selector).get()
            if title and title.strip() and not 'Pinterest' in title:
                return title.strip()
        
        return "No title available"

    def extract_pin_description(self, response):
        """Extract pin description"""
        selectors = [
            '[data-test-id="pin-description"]::text',
            '.Pin-description::text',
            'meta[property="og:description"]::attr(content)',
            'meta[name="description"]::attr(content)',
            '.UserDescription span::text'
        ]
        
        for selector in selectors:
            description = response.css(selector).get()
            if description and description.strip() and len(description.strip()) > 10:
                return description.strip()
        
        return ""

    def extract_image_url(self, response):
        """Extract main pin image URL"""
        selectors = [
            'img[alt*="Pin"]::attr(src)',
            '.Pin-image img::attr(src)',
            'meta[property="og:image"]::attr(content)',
            '.MainContainer img::attr(src)',
            'img[src*="pinimg"]::attr(src)'
        ]
        
        for selector in selectors:
            image_url = response.css(selector).get()
            if image_url and ('pinimg' in image_url or 'pinterest' in image_url):
                return image_url
        
        return ""

    def extract_media_type(self, response):
        """Determine if pin is image, video, or other"""
        # Check for video indicators
        if response.css('video, .video, [data-test-id="video"]').get():
            return "video"
        elif response.css('img, .image, [data-test-id="image"]').get():
            return "image"
        else:
            return "unknown"

    def extract_board_name(self, response):
        """Extract board name"""
        selectors = [
            '[data-test-id="board-name"]::text',
            '.boardName::text',
            'a[href*="/board/"]::text',
            '.Board-name::text'
        ]
        
        for selector in selectors:
            board_name = response.css(selector).get()
            if board_name and board_name.strip():
                return board_name.strip()
        
        return ""

    def extract_board_url(self, response):
        """Extract board URL"""
        selectors = [
            'a[href*="/board/"]::attr(href)',
            '[data-test-id="board-link"]::attr(href)'
        ]
        
        for selector in selectors:
            board_url = response.css(selector).get()
            if board_url:
                return urljoin(self.base_url, board_url)
        
        return ""

    def extract_pinner_username(self, response):
        """Extract pinner username"""
        selectors = [
            '[data-test-id="pinner-name"]::text',
            '.pinner-name::text',
            'a[href*="/user/"]::text',
            '.UserName::text'
        ]
        
        for selector in selectors:
            username = response.css(selector).get()
            if username and username.strip():
                return username.strip()
        
        return ""

    def extract_pinner_name(self, response):
        """Extract pinner display name"""
        selectors = [
            '[data-test-id="pinner-full-name"]::text',
            '.pinner-full-name::text',
            '.UserDisplayName::text'
        ]
        
        for selector in selectors:
            name = response.css(selector).get()
            if name and name.strip():
                return name.strip()
        
        return ""

    def extract_pinner_url(self, response):
        """Extract pinner profile URL"""
        selectors = [
            'a[href*="/user/"]::attr(href)',
            '[data-test-id="pinner-link"]::attr(href)'
        ]
        
        for selector in selectors:
            pinner_url = response.css(selector).get()
            if pinner_url:
                return urljoin(self.base_url, pinner_url)
        
        return ""

    def extract_pin_likes(self, response):
        """Extract number of likes/hearts"""
        # Pinterest might not always show exact numbers
        selectors = [
            '[data-test-id="like-count"]::text',
            '.like-count::text',
            'span:contains("reactions")::text'
        ]
        
        for selector in selectors:
            likes_text = response.css(selector).get()
            if likes_text:
                return self.parse_number(likes_text)
        
        return 0

    def extract_pin_comments(self, response):
        """Extract number of comments"""
        selectors = [
            '[data-test-id="comment-count"]::text',
            '.comment-count::text',
            'span:contains("comment")::text'
        ]
        
        for selector in selectors:
            comments_text = response.css(selector).get()
            if comments_text:
                return self.parse_number(comments_text)
        
        return 0

    def extract_pin_repins(self, response):
        """Extract number of repins/saves"""
        selectors = [
            '[data-test-id="save-count"]::text',
            '.save-count::text',
            'span:contains("save")::text'
        ]
        
        for selector in selectors:
            saves_text = response.css(selector).get()
            if saves_text:
                return self.parse_number(saves_text)
        
        return 0

    def extract_source_url(self, response):
        """Extract original source URL if available"""
        selectors = [
            'a[data-test-id="source-url"]::attr(href)',
            '.source-link::attr(href)',
            'meta[property="article:author"]::attr(content)'
        ]
        
        for selector in selectors:
            source_url = response.css(selector).get()
            if source_url and source_url.startswith('http'):
                return source_url
        
        return ""

    def extract_source_domain(self, response):
        """Extract domain from source URL"""
        source_url = self.extract_source_url(response)
        if source_url:
            match = re.search(r'https?://([^/]+)', source_url)
            return match.group(1) if match else ""
        return ""

    def extract_pin_tags(self, response):
        """Extract hashtags and tags"""
        tags = []
        
        # Look for hashtags in description or dedicated tag areas
        description = self.extract_pin_description(response)
        if description:
            hashtags = re.findall(r'#(\w+)', description)
            tags.extend(hashtags)
        
        # Look for dedicated tag elements
        tag_selectors = [
            '.tag::text',
            '.hashtag::text',
            '[data-test-id="tag"]::text'
        ]
        
        for selector in tag_selectors:
            found_tags = response.css(selector).getall()
            tags.extend([tag.strip('#') for tag in found_tags if tag])
        
        return list(set(tags[:10]))  # Remove duplicates, limit to 10

    def extract_pin_topics(self, response):
        """Extract Pinterest topics/categories"""
        topics = []
        
        topic_selectors = [
            '.topic::text',
            '.category::text',
            '[data-test-id="topic"]::text'
        ]
        
        for selector in topic_selectors:
            found_topics = response.css(selector).getall()
            topics.extend([topic.strip() for topic in found_topics if topic])
        
        return list(set(topics[:5]))  # Remove duplicates, limit to 5

    def extract_shoppable_status(self, response):
        """Check if pin is shoppable"""
        shopping_indicators = [
            '.shopping-icon',
            '[data-test-id="shopping"]',
            '.price-tag',
            'span:contains("Shop")'
        ]
        
        for indicator in shopping_indicators:
            if response.css(indicator).get():
                return True
        
        return False

    def extract_product_price(self, response):
        """Extract product price if available"""
        price_selectors = [
            '.price::text',
            '[data-test-id="price"]::text',
            'span:contains("$")::text'
        ]
        
        for selector in price_selectors:
            price_text = response.css(selector).get()
            if price_text and '$' in price_text:
                # Extract price using regex
                price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                return price_match.group(0) if price_match else ""
        
        return ""

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