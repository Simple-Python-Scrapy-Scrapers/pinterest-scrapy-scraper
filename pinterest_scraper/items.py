# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class PinterestPinItem(scrapy.Item):
    """Pinterest Pin data model with comprehensive fields"""
    
    # Pin identification
    pin_id = scrapy.Field()
    pin_url = scrapy.Field()
    pin_shortcode = scrapy.Field()
    
    # Pin content
    title = scrapy.Field()
    description = scrapy.Field()
    alt_text = scrapy.Field()
    
    # Media information
    image_url = scrapy.Field()
    image_width = scrapy.Field()
    image_height = scrapy.Field()
    image_signature = scrapy.Field()
    media_type = scrapy.Field()  # image, video, story_pin
    
    # Board information
    board_id = scrapy.Field()
    board_name = scrapy.Field()
    board_url = scrapy.Field()
    board_section = scrapy.Field()
    
    # Pinner (creator) information
    pinner_id = scrapy.Field()
    pinner_username = scrapy.Field()
    pinner_name = scrapy.Field()
    pinner_url = scrapy.Field()
    pinner_follower_count = scrapy.Field()
    pinner_verified = scrapy.Field()
    
    # Engagement metrics
    pin_likes = scrapy.Field()
    pin_comments = scrapy.Field()
    pin_repins = scrapy.Field()
    pin_saves = scrapy.Field()
    engagement_rate = scrapy.Field()
    
    # Content metadata
    created_at = scrapy.Field()
    last_pinned_at = scrapy.Field()
    is_promoted = scrapy.Field()
    is_video = scrapy.Field()
    dominant_color = scrapy.Field()
    
    # Source information
    source_url = scrapy.Field()
    source_domain = scrapy.Field()
    attribution = scrapy.Field()
    
    # Categories and tags
    primary_category = scrapy.Field()
    categories = scrapy.Field()
    tags = scrapy.Field()
    topics = scrapy.Field()
    
    # Shopping information (if applicable)
    product_price = scrapy.Field()
    product_currency = scrapy.Field()
    product_availability = scrapy.Field()
    is_shoppable = scrapy.Field()
    
    # Technical metadata
    pin_score = scrapy.Field()
    rich_metadata = scrapy.Field()
    aggregated_pin_data = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field()
    scraper_version = scrapy.Field()


class PinterestBoardItem(scrapy.Item):
    """Pinterest Board data model"""
    
    # Board identification
    board_id = scrapy.Field()
    board_url = scrapy.Field()
    board_name = scrapy.Field()
    board_slug = scrapy.Field()
    
    # Board information
    description = scrapy.Field()
    category = scrapy.Field()
    is_collaborative = scrapy.Field()
    privacy = scrapy.Field()  # public, secret
    
    # Owner information
    owner_id = scrapy.Field()
    owner_username = scrapy.Field()
    owner_name = scrapy.Field()
    owner_url = scrapy.Field()
    
    # Board metrics
    pin_count = scrapy.Field()
    follower_count = scrapy.Field()
    collaborator_count = scrapy.Field()
    section_count = scrapy.Field()
    
    # Board metadata
    created_at = scrapy.Field()
    updated_at = scrapy.Field()
    cover_pin = scrapy.Field()
    cover_images = scrapy.Field()
    
    # Board sections
    sections = scrapy.Field()
    section_names = scrapy.Field()
    
    # Sample pins from board
    sample_pins = scrapy.Field()
    recent_pins = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field()


class PinterestUserItem(scrapy.Item):
    """Pinterest User/Profile data model"""
    
    # User identification
    user_id = scrapy.Field()
    username = scrapy.Field()
    profile_url = scrapy.Field()
    
    # Profile information
    full_name = scrapy.Field()
    first_name = scrapy.Field()
    last_name = scrapy.Field()
    bio = scrapy.Field()
    location = scrapy.Field()
    
    # Profile images
    profile_image = scrapy.Field()
    profile_image_large = scrapy.Field()
    cover_image = scrapy.Field()
    
    # Account metadata
    account_type = scrapy.Field()  # personal, business
    verified = scrapy.Field()
    is_partner = scrapy.Field()
    website_url = scrapy.Field()
    
    # Social metrics
    follower_count = scrapy.Field()
    following_count = scrapy.Field()
    pin_count = scrapy.Field()
    board_count = scrapy.Field()
    likes_count = scrapy.Field()
    
    # Activity metrics
    monthly_views = scrapy.Field()
    engagement_rate = scrapy.Field()
    avg_monthly_impressions = scrapy.Field()
    
    # Business information (if applicable)
    business_name = scrapy.Field()
    business_type = scrapy.Field()
    business_location = scrapy.Field()
    
    # Content categories
    top_categories = scrapy.Field()
    interest_categories = scrapy.Field()
    
    # Recent activity
    recent_pins = scrapy.Field()
    recent_boards = scrapy.Field()
    
    # Account dates
    created_at = scrapy.Field()
    last_pin_save_time = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field()


class PinterestSearchItem(scrapy.Item):
    """Pinterest Search Results data model"""
    
    # Search metadata
    search_query = scrapy.Field()
    search_type = scrapy.Field()  # pins, boards, users
    search_url = scrapy.Field()
    
    # Result information
    result_type = scrapy.Field()  # pin, board, user
    result_id = scrapy.Field()
    result_url = scrapy.Field()
    result_title = scrapy.Field()
    result_description = scrapy.Field()
    
    # Result metrics
    result_score = scrapy.Field()
    relevance_score = scrapy.Field()
    position_in_results = scrapy.Field()
    
    # Result preview
    thumbnail_url = scrapy.Field()
    preview_images = scrapy.Field()
    
    # Creator information
    creator_name = scrapy.Field()
    creator_username = scrapy.Field()
    creator_verified = scrapy.Field()
    
    # Search context
    total_results = scrapy.Field()
    result_page = scrapy.Field()
    search_filters = scrapy.Field()
    search_suggestions = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field()
    search_timestamp = scrapy.Field()


class PinterestTrendingItem(scrapy.Item):
    """Pinterest Trending content data model"""
    
    # Trending identification
    trend_id = scrapy.Field()
    trend_type = scrapy.Field()  # hashtag, topic, search_term
    trend_name = scrapy.Field()
    
    # Trend metrics
    trend_score = scrapy.Field()
    search_volume = scrapy.Field()
    growth_rate = scrapy.Field()
    position = scrapy.Field()
    
    # Associated content
    sample_pins = scrapy.Field()
    related_trends = scrapy.Field()
    trend_category = scrapy.Field()
    
    # Time context
    trending_period = scrapy.Field()  # today, week, month
    trend_start_date = scrapy.Field()
    
    # Geographic context
    trending_region = scrapy.Field()
    country_code = scrapy.Field()
    
    # Scraping metadata
    scraped_at = scrapy.Field() 