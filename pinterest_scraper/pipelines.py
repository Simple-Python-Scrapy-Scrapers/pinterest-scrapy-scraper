# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import csv
import json
import re
from datetime import datetime
from itemadapter import ItemAdapter


class PinterestScrapyPipeline:
    """Main pipeline for processing Pinterest scraped data"""

    def __init__(self):
        self.files = {}
        self.exporters = {}

    def open_spider(self, spider):
        """Initialize CSV files for different item types based on spider type"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        
        # Define which item types each spider generates
        spider_item_types = {
            'pinterest_search': ['PinterestSearchItem', 'PinterestTrendingItem'],
            'pinterest_pins': ['PinterestPinItem'],
            'pinterest_boards': ['PinterestBoardItem']
        }
        
        # Get the item types for this specific spider
        spider_name = spider.name
        item_types_to_create = spider_item_types.get(spider_name, [])
        
        # Define item types and their corresponding CSV files
        item_types = {
            'PinterestPinItem': f'data/pinterest_pins_{timestamp}.csv',
            'PinterestBoardItem': f'data/pinterest_boards_{timestamp}.csv',
            'PinterestUserItem': f'data/pinterest_users_{timestamp}.csv',
            'PinterestSearchItem': f'data/pinterest_search_{timestamp}.csv',
            'PinterestTrendingItem': f'data/pinterest_trending_{timestamp}.csv'
        }
        
        # Only create files for item types this spider will generate
        for item_type in item_types_to_create:
            if item_type in item_types:
                filename = item_types[item_type]
                file = open(filename, 'w', newline='', encoding='utf-8')
                self.files[item_type] = file
                self.exporters[item_type] = csv.writer(file)
                spider.logger.info(f"📁 Created CSV file for {item_type}: {filename}")

    def close_spider(self, spider):
        """Close all CSV files"""
        for file in self.files.values():
            file.close()

    def process_item(self, item, spider):
        """Process items based on their type"""
        adapter = ItemAdapter(item)
        item_type = item.__class__.__name__
        
        # Clean and validate item data
        cleaned_item = self.clean_item_data(adapter)
        
        # Filter out empty fields for cleaner CSV output
        non_empty_item = {k: v for k, v in cleaned_item.items() if v and v != '' and v != '0' and v != 'false' and v != '[]'}
        
        # Write headers if this is the first item of this type
        if item_type in self.exporters and not hasattr(self, f'{item_type}_headers_written'):
            self.exporters[item_type].writerow(non_empty_item.keys())
            setattr(self, f'{item_type}_headers_written', True)
            
        # Write item data to CSV
        if item_type in self.exporters:
            self.exporters[item_type].writerow(non_empty_item.values())
            
        return item

    def clean_item_data(self, adapter):
        """Clean and format item data for CSV export"""
        cleaned = {}
        
        for field_name, field_value in adapter.items():
            cleaned_value = self.clean_field_value(field_value)
            cleaned[field_name] = cleaned_value
            
        return cleaned

    def clean_field_value(self, value):
        """Clean individual field values"""
        if value is None:
            return ''
        elif isinstance(value, (list, tuple)):
            # Convert lists to comma-separated strings
            return ', '.join(str(item) for item in value if item)
        elif isinstance(value, dict):
            # Convert dicts to JSON strings
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            # Clean string values
            return str(value).strip()


class DataValidationPipeline:
    """Validate Pinterest data quality and completeness"""

    def process_item(self, item, spider):
        """Validate item data"""
        adapter = ItemAdapter(item)
        item_type = item.__class__.__name__
        
        if item_type == 'PinterestPinItem':
            self.validate_pin_item(adapter)
        elif item_type == 'PinterestBoardItem':
            self.validate_board_item(adapter)
        elif item_type == 'PinterestUserItem':
            self.validate_user_item(adapter)
        elif item_type == 'PinterestSearchItem':
            self.validate_search_item(adapter)
            
        return item

    def validate_pin_item(self, adapter):
        """Validate Pinterest pin data"""
        required_fields = ['pin_id', 'title', 'image_url']
        
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field for pin: {field}")
                
        # Validate URL format
        if adapter.get('pin_url') and not self.is_valid_url(adapter['pin_url']):
            adapter['pin_url'] = ''
            
        # Validate numeric fields
        numeric_fields = ['pin_likes', 'pin_comments', 'pin_repins', 'pinner_follower_count']
        for field in numeric_fields:
            if adapter.get(field):
                adapter[field] = self.parse_number(adapter[field])

    def validate_board_item(self, adapter):
        """Validate Pinterest board data"""
        required_fields = ['board_id', 'board_name']
        
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field for board: {field}")
                
        # Validate numeric fields
        numeric_fields = ['pin_count', 'follower_count', 'collaborator_count']
        for field in numeric_fields:
            if adapter.get(field):
                adapter[field] = self.parse_number(adapter[field])

    def validate_user_item(self, adapter):
        """Validate Pinterest user data"""
        required_fields = ['user_id', 'username']
        
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field for user: {field}")
                
        # Clean username
        if adapter.get('username'):
            adapter['username'] = adapter['username'].replace('@', '').strip()
            
        # Validate numeric fields
        numeric_fields = ['follower_count', 'following_count', 'pin_count', 'board_count']
        for field in numeric_fields:
            if adapter.get(field):
                adapter[field] = self.parse_number(adapter[field])

    def validate_search_item(self, adapter):
        """Validate Pinterest search data"""
        required_fields = ['search_query', 'result_type']
        
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field for search result: {field}")

    def is_valid_url(self, url):
        """Check if URL is valid"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    def parse_number(self, value):
        """Parse number from string with K, M suffixes"""
        if isinstance(value, (int, float)):
            return value
            
        if not value or value == 'N/A':
            return 0
            
        value_str = str(value).strip().replace(',', '')
        
        # Handle K, M, B suffixes
        if value_str.endswith('K') or value_str.endswith('k'):
            try:
                return int(float(value_str[:-1]) * 1000)
            except ValueError:
                return 0
        elif value_str.endswith('M') or value_str.endswith('m'):
            try:
                return int(float(value_str[:-1]) * 1000000)
            except ValueError:
                return 0
        elif value_str.endswith('B') or value_str.endswith('b'):
            try:
                return int(float(value_str[:-1]) * 1000000000)
            except ValueError:
                return 0
        else:
            try:
                return int(float(value_str))
            except ValueError:
                return 0


class DuplicateFilterPipeline:
    """Filter out duplicate items based on unique identifiers"""

    def __init__(self):
        self.seen_ids = {
            'PinterestPinItem': set(),
            'PinterestBoardItem': set(),
            'PinterestUserItem': set(),
            'PinterestSearchItem': set(),
            'PinterestTrendingItem': set()
        }

    def process_item(self, item, spider):
        """Filter out duplicate items"""
        adapter = ItemAdapter(item)
        item_type = item.__class__.__name__
        
        # Determine unique identifier based on item type
        unique_id = self.get_unique_identifier(adapter, item_type)
        
        if unique_id in self.seen_ids.get(item_type, set()):
            spider.logger.warning(f"Duplicate {item_type} found: {unique_id}")
            return None
        else:
            self.seen_ids[item_type].add(unique_id)
            return item

    def get_unique_identifier(self, adapter, item_type):
        """Get unique identifier for different item types"""
        if item_type == 'PinterestPinItem':
            return adapter.get('pin_id') or adapter.get('pin_url', '')
        elif item_type == 'PinterestBoardItem':
            return adapter.get('board_id') or adapter.get('board_url', '')
        elif item_type == 'PinterestUserItem':
            return adapter.get('user_id') or adapter.get('username', '')
        elif item_type == 'PinterestSearchItem':
            return f"{adapter.get('search_query', '')}_{adapter.get('result_id', '')}"
        elif item_type == 'PinterestTrendingItem':
            return adapter.get('trend_id') or adapter.get('trend_name', '')
        else:
            return str(adapter.get('scraped_at', ''))


class DataEnrichmentPipeline:
    """Enrich Pinterest data with additional computed fields"""

    def process_item(self, item, spider):
        """Enrich item with computed fields"""
        adapter = ItemAdapter(item)
        item_type = item.__class__.__name__
        
        # Add timestamp if not present
        if not adapter.get('scraped_at'):
            adapter['scraped_at'] = datetime.now().isoformat()
            
        if item_type == 'PinterestPinItem':
            self.enrich_pin_item(adapter)
        elif item_type == 'PinterestUserItem':
            self.enrich_user_item(adapter)
            
        return item

    def enrich_pin_item(self, adapter):
        """Add computed fields for pin items"""
        # Calculate engagement rate
        likes = self.safe_int(adapter.get('pin_likes', 0))
        comments = self.safe_int(adapter.get('pin_comments', 0))
        repins = self.safe_int(adapter.get('pin_repins', 0))
        
        total_engagement = likes + comments + repins
        follower_count = self.safe_int(adapter.get('pinner_follower_count', 0))
        
        if follower_count > 0:
            engagement_rate = (total_engagement / follower_count) * 100
            adapter['engagement_rate'] = round(engagement_rate, 2)
        else:
            adapter['engagement_rate'] = 0

    def enrich_user_item(self, adapter):
        """Add computed fields for user items"""
        # Calculate average pins per board
        pin_count = self.safe_int(adapter.get('pin_count', 0))
        board_count = self.safe_int(adapter.get('board_count', 0))
        
        if board_count > 0:
            avg_pins_per_board = pin_count / board_count
            adapter['avg_pins_per_board'] = round(avg_pins_per_board, 1)

    def safe_int(self, value):
        """Safely convert value to integer"""
        try:
            return int(float(str(value).replace(',', '')))
        except (ValueError, TypeError):
            return 0 