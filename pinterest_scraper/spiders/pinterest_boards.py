import scrapy
import json
import re
from datetime import datetime
from urllib.parse import urljoin, quote_plus
from pinterest_scraper.items import PinterestBoardItem


class PinterestBoardsSpider(scrapy.Spider):
    name = "pinterest_boards"
    allowed_domains = ["pinterest.com", "proxy.scrapeops.io"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
    }

    def __init__(self, search_query=None, max_boards=20, category=None, *args, **kwargs):
        super(PinterestBoardsSpider, self).__init__(*args, **kwargs)
        self.search_query = search_query or "home decor"
        self.max_boards = int(max_boards)
        self.category = category
        self.base_url = "https://www.pinterest.com"
        self.boards_scraped = 0

    def start_requests(self):
        """Generate initial requests for Pinterest boards"""
        
        # Get ScrapeOps API key from settings
        api_key = self.settings.get('SCRAPEOPS_API_KEY')
        
        # If specific search query provided
        if self.search_query:
            search_url = f"{self.base_url}/search/boards/?q={quote_plus(self.search_query)}"
            self.logger.info(f"🔍 Searching Pinterest boards for: {self.search_query}")
            
            # Use ScrapeOps proxy with JavaScript rendering
            proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(search_url)}&render_js=true&wait=3000&residential=false&country=US"
            
            yield scrapy.Request(
                url=proxy_url,
                callback=self.parse_search_results,
                meta={'search_query': self.search_query}
            )
        
        # If category provided
        elif self.category:
            category_url = f"{self.base_url}/search/boards/?q={quote_plus(self.category)}"
            
            # Use ScrapeOps proxy with JavaScript rendering
            proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(category_url)}&render_js=true&wait=3000&residential=false&country=US"
            
            yield scrapy.Request(
                url=proxy_url,
                callback=self.parse_search_results,
                meta={'search_query': self.category}
            )
        
        # Default: popular board categories
        else:
            popular_categories = [
                "home decor", "fashion", "food recipes", "travel", "wedding",
                "interior design", "art", "photography", "diy projects"
            ]
            
            for category in popular_categories[:3]:  # Limit to first 3 categories
                search_url = f"{self.base_url}/search/boards/?q={quote_plus(category)}"
                
                # Use ScrapeOps proxy with JavaScript rendering
                proxy_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(search_url)}&render_js=true&wait=3000&residential=false&country=US"
                
                yield scrapy.Request(
                    url=proxy_url,
                    callback=self.parse_search_results,
                    meta={'search_query': category}
                )

    def parse_search_results(self, response):
        """Parse Pinterest board search results page to extract board links"""
        
        search_query = response.meta.get('search_query')
        self.logger.info(f"📍 Parsing board search results for: {search_query}")
        
        # Get ScrapeOps API key from settings
        api_key = self.settings.get('SCRAPEOPS_API_KEY')
        
        # Look for board links using Pinterest's actual format: /username/board-name/
        board_selectors = [
            '[data-test-id="board-card"] a::attr(href)',
            'a[href*="/"][href*="/"]:not([href*="/search/"]):not([href*="/pin/"]):not([href*="/user/"]):not([href*="/create/"])::attr(href)',
            '.board-card a::attr(href)',
            'a[href*="/"][href*="/"]::attr(href)'  # General pattern for username/board-name
        ]
        
        board_links = []
        for selector in board_selectors:
            found_links = response.css(selector).getall()
            if found_links:
                self.logger.info(f"Found {len(found_links)} board links using selector: {selector}")
                for link in found_links:
                    if link and len(link) > 5:
                        # Clean up the link
                        link = link.strip()
                        if not link.startswith('http'):
                            full_url = urljoin(self.base_url, link)
                        else:
                            full_url = link
                        
                        # Validate it's a proper board URL (Pinterest format: /username/board-name/)
                        if (full_url not in board_links and 
                            'pinterest.com' in full_url and 
                            not full_url.endswith('.mjs') and
                            not 'create' in full_url and
                            not 'edit' in full_url and
                            not '/search/' in full_url and
                            not '/pin/' in full_url and
                            not '/user/' in full_url and
                            full_url.count('/') >= 4):  # Should have at least username/boardname/
                            
                            # Convert to board URL format if needed
                            if '/board/' not in full_url:
                                # Extract username and board name from /username/board-name/
                                path_parts = full_url.split('/')
                                if len(path_parts) >= 4:
                                    username = path_parts[-3]  # Second to last part
                                    board_name = path_parts[-2]  # Last part
                                    board_url = f"https://www.pinterest.com/board/{username}/{board_name}/"
                                    board_links.append(board_url)
                            else:
                                board_links.append(full_url)
                break  # Use first successful selector
        
        # If no board links found, try alternative approach
        if not board_links:
            board_links = self.extract_boards_from_scripts(response)
        
        # Additional fallback: look for board URLs in page text
        if not board_links:
            board_links = self.extract_boards_from_text(response)
        
        self.logger.info(f"✅ Found {len(board_links)} unique board URLs")
        
        # Follow board links
        for board_url in board_links[:self.max_boards]:
            if self.boards_scraped >= self.max_boards:
                break
            
            # Use ScrapeOps proxy with JavaScript rendering for board pages
            proxy_board_url = f"https://proxy.scrapeops.io/v1/?api_key={api_key}&url={quote_plus(board_url)}&render_js=true&wait=3000&residential=false&country=US"
                
            yield scrapy.Request(
                url=proxy_board_url,
                callback=self.parse_board,
                meta={
                    'search_query': search_query,
                    'board_url': board_url
                }
            )
            self.boards_scraped += 1

    def extract_boards_from_scripts(self, response):
        """Extract board URLs from JavaScript/JSON data"""
        board_links = []
        
        # Look for JSON data in script tags
        scripts = response.css('script::text').getall()
        
        for script in scripts:
            if 'board' in script.lower():
                # Look for board URLs in JavaScript - Pinterest format: /username/board-name/
                board_matches = re.findall(r'["\'](/[^"\']+/[^"\']+/)["\']', script)
                
                for match in board_matches:
                    # Clean up the match and create proper URL
                    board_path = match.strip()
                    if (board_path and 
                        len(board_path) > 5 and 
                        not board_path.endswith('.mjs') and
                        not 'create' in board_path and
                        not 'edit' in board_path and
                        not '/search/' in board_path and
                        not '/pin/' in board_path and
                        not '/user/' in board_path and
                        board_path.count('/') >= 3):  # Should have at least /username/boardname/
                        
                        # Convert to board URL format
                        path_parts = board_path.split('/')
                        if len(path_parts) >= 3:
                            username = path_parts[1]  # First part after /
                            board_name = path_parts[2]  # Second part after /
                            if username and board_name:
                                board_url = f"https://www.pinterest.com/board/{username}/{board_name}/"
                                if board_url not in board_links:
                                    board_links.append(board_url)
                
                if board_links:
                    self.logger.info(f"Found {len(board_links)} boards in page scripts")
                    break
        
        return board_links[:20]  # Limit to 20 boards

    def extract_boards_from_text(self, response):
        """Extract board URLs from page text content"""
        board_links = []
        
        # Look for board URLs in the page content
        page_text = response.text.lower()
        
        # Common patterns for board URLs in text
        board_patterns = [
            r'href="https://www.pinterest.com/board/',
            r'href="/board/',
            r'href="https://pinterest.com/board/',
            r'href="/board/'
        ]
        
        for pattern in board_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                # Clean up the match and create proper URL
                full_url = urljoin(self.base_url, match)
                if full_url not in board_links and 'pinterest.com' in full_url:
                    board_links.append(full_url)
        
        return board_links[:10] # Limit to 10 boards

    def parse_board(self, response):
        """Parse individual Pinterest board page"""
        
        search_query = response.meta.get('search_query')
        board_url = response.meta.get('board_url', response.url)
        
        self.logger.info(f"📋 Parsing board: {board_url}")
        
        item = PinterestBoardItem()
        
        # Only extract the essential information
        item['board_url'] = board_url
        item['board_id'] = self.extract_board_id(board_url)
        
        yield item

    def extract_board_id(self, board_url):
        """Extract board ID from URL"""
        try:
            # Extract username from board URL
            if '/board/' in board_url:
                parts = board_url.split('/board/')
                if len(parts) > 1:
                    board_path = parts[1].rstrip('/')
                    username = board_path.split('/')[0]
                    return f"{username}/"
            return ""
        except:
            return ""

    def extract_board_name(self, response):
        """Extract board name with multiple selectors"""
        selectors = [
            'h1::text',
            '[data-test-id="board-name"]::text',
            '.boardName::text',
            'title::text',
            'meta[property="og:title"]::attr(content)',
            '[role="heading"]::text'
        ]
        
        for selector in selectors:
            name = response.css(selector).get()
            if name and name.strip() and not 'Pinterest' in name:
                return name.strip()
        
        return "No name available"

    def extract_board_description(self, response):
        """Extract board description"""
        selectors = [
            '[data-test-id="board-description"]::text',
            '.boardDescription::text',
            'meta[property="og:description"]::attr(content)',
            'meta[name="description"]::attr(content)',
            '.BoardDescription span::text'
        ]
        
        for selector in selectors:
            description = response.css(selector).get()
            if description and description.strip() and len(description.strip()) > 10:
                return description.strip()
        
        return ""

    def extract_board_owner_username(self, response):
        """Extract board owner username"""
        selectors = [
            '[data-test-id="board-owner"]::text',
            '.boardOwner::text',
            'a[href*="/user/"]::text',
            '.UserName::text'
        ]
        
        for selector in selectors:
            username = response.css(selector).get()
            if username and username.strip():
                return username.strip()
        
        return ""

    def extract_board_owner_name(self, response):
        """Extract board owner display name"""
        selectors = [
            '[data-test-id="board-owner-full-name"]::text',
            '.boardOwner-full-name::text',
            '.UserDisplayName::text'
        ]
        
        for selector in selectors:
            name = response.css(selector).get()
            if name and name.strip():
                return name.strip()
        
        return ""

    def extract_board_owner_url(self, response):
        """Extract board owner profile URL"""
        selectors = [
            'a[href*="/user/"]::attr(href)',
            '[data-test-id="board-owner-link"]::attr(href)'
        ]
        
        for selector in selectors:
            owner_url = response.css(selector).get()
            if owner_url:
                return urljoin(self.base_url, owner_url)
        
        return ""

    def extract_pin_count(self, response):
        """Extract number of pins in the board"""
        selectors = [
            '[data-test-id="pin-count"]::text',
            '.pin-count::text',
            'span:contains("pins")::text'
        ]
        
        for selector in selectors:
            count_text = response.css(selector).get()
            if count_text:
                return self.parse_number(count_text)
        
        return 0

    def extract_follower_count(self, response):
        """Extract number of board followers"""
        selectors = [
            '[data-test-id="follower-count"]::text',
            '.follower-count::text',
            'span:contains("followers")::text'
        ]
        
        for selector in selectors:
            count_text = response.css(selector).get()
            if count_text:
                return self.parse_number(count_text)
        
        return 0

    def extract_collaborator_count(self, response):
        """Extract number of board collaborators"""
        selectors = [
            '[data-test-id="collaborator-count"]::text',
            '.collaborator-count::text',
            'span:contains("collaborators")::text'
        ]
        
        for selector in selectors:
            count_text = response.css(selector).get()
            if count_text:
                return self.parse_number(count_text)
        
        return 0

    def extract_privacy_status(self, response):
        """Check if board is secret/private"""
        secret_indicators = [
            '.secret-board',
            '[data-test-id="secret"]',
            'span:contains("Secret")'
        ]
        
        for indicator in secret_indicators:
            if response.css(indicator).get():
                return "secret"
        
        return "public"

    def extract_collaborative_status(self, response):
        """Check if board is collaborative"""
        collaborative_indicators = [
            '.collaborative-board',
            '[data-test-id="collaborative"]',
            'span:contains("Collaborative")'
        ]
        
        for indicator in collaborative_indicators:
            if response.css(indicator).get():
                return True
        
        return False

    def extract_board_category(self, response):
        """Extract board category"""
        selectors = [
            '.boardCategory::text',
            '[data-test-id="category"]::text',
            '.category::text'
        ]
        
        for selector in selectors:
            category = response.css(selector).get()
            if category and category.strip():
                return category.strip()
        
        return ""

    def extract_board_tags(self, response):
        """Extract board tags/hashtags"""
        tags = []
        
        # Look for hashtags in description
        description = self.extract_board_description(response)
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

    def extract_board_topics(self, response):
        """Extract Pinterest topics/categories for the board"""
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

    def extract_sample_pins(self, response):
        """Extract sample pin URLs from the board"""
        sample_pins = []
        
        pin_selectors = [
            'a[href*="/pin/"]::attr(href)',
            '[data-test-id="pin"] a::attr(href)'
        ]
        
        for selector in pin_selectors:
            found_pins = response.css(selector).getall()
            for pin_url in found_pins[:5]:  # Limit to 5 sample pins
                if pin_url and '/pin/' in pin_url:
                    full_url = urljoin(self.base_url, pin_url)
                    sample_pins.append(full_url)
            break  # Use first successful selector
        
        return sample_pins

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