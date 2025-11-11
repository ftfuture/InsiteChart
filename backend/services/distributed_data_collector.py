"""
Distributed Data Collection Service for InsiteChart platform.

This service provides a distributed architecture for collecting data from multiple
sources including Yahoo Finance API, social media, and news feeds.
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import aiohttp
import aioredis
from asyncio import Queue
import hashlib

from ..cache.unified_cache import UnifiedCacheManager




@dataclass
class DataCollectionTask:
    """Data collection task."""
    task_id: str
    source_type: DataSourceType
    priority: DataPriority
    source_config: Dict[str, Any]
    created_at: datetime
    scheduled_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    status: DataStatus = DataStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityRule:
    """Data quality validation rule."""
    rule_id: str
    name: str
    description: str
    source_types: List[DataSourceType]
    validation_function: Callable[[Dict[str, Any]], bool]
    enabled: bool
    created_at: datetime


@dataclass
class DataPipeline:
    """Data processing pipeline."""
    pipeline_id: str
    name: str
    description: str
    source_type: DataSourceType
    processors: List[str]  # Processor function names
    enabled: bool
    created_at: datetime
    updated_at: datetime


class DistributedDataCollector:
    """Distributed data collection service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # Data storage
        self.collection_tasks: Dict[str, DataCollectionTask] = {}
        self.data_pipelines: Dict[str, DataPipeline] = {}
        self.quality_rules: Dict[str, DataQualityRule] = {}
        
        # Processing queues
        self.task_queues = {
            DataPriority.CRITICAL: Queue(maxsize=100),
            DataPriority.HIGH: Queue(maxsize=500),
            DataPriority.NORMAL: Queue(maxsize=1000),
            DataPriority.LOW: Queue(maxsize=2000)
        }
        
        # Worker management
        self.workers = {}
        self.max_workers = self.config.get("max_workers", 10)
        self.worker_active = True
        
        # Message queue
        self.redis_client = None
        self.message_queue = "data_collection_tasks"
        
        # Performance metrics
        self.metrics = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "avg_processing_time_ms": 0,
            "queue_sizes": {},
            "worker_utilization": {}
        }
        
        # Cache TTL settings
        self.task_cache_ttl = 3600  # 1 hour
        self.pipeline_cache_ttl = 1800  # 30 minutes
        self.metrics_cache_ttl = 300  # 5 minutes
        
        # Initialize data quality rules
        self._initialize_quality_rules()
        
        # Initialize data pipelines
        self._initialize_data_pipelines()
        
        # Start message queue listener
        asyncio.create_task(self._start_message_queue_listener())
        
        # Start worker processes
        self._start_workers()
        
        self.logger.info("DistributedDataCollector initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load data collection configuration."""
        try:
            return {
                "max_workers": int(os.getenv('MAX_DATA_COLLECTION_WORKERS', '10')),
                "redis_host": os.getenv('REDIS_HOST', 'localhost'),
                "redis_port": int(os.getenv('REDIS_PORT', '6379')),
                "redis_db": int(os.getenv('REDIS_DB', '0')),
                "task_timeout": int(os.getenv('TASK_TIMEOUT', '300')),  # 5 minutes
                "retry_delay": int(os.getenv('RETRY_DELAY', '60')),  # 1 minute
                "batch_size": int(os.getenv('DATA_COLLECTION_BATCH_SIZE', '100')),
                "quality_check_enabled": os.getenv('DATA_QUALITY_CHECK_ENABLED', 'true').lower() == 'true',
                "deduplication_enabled": os.getenv('DATA_DEDUPLICATION_ENABLED', 'true').lower() == 'true',
                "metrics_collection_interval": int(os.getenv('METRICS_COLLECTION_INTERVAL', '60'))  # 1 minute
            }
        except Exception as e:
            self.logger.error(f"Error loading data collection configuration: {str(e)}")
            return {}
    
    def _initialize_quality_rules(self):
        """Initialize data quality validation rules."""
        try:
            default_rules = [
                DataQualityRule(
                    rule_id="yahoo_finance_data_validation",
                    name="Yahoo Finance Data Validation",
                    description="Validates Yahoo Finance API data structure and values",
                    source_types=[DataSourceType.YAHOO_FINANCE],
                    validation_function=self._validate_yahoo_finance_data,
                    enabled=True,
                    created_at=datetime.utcnow()
                ),
                DataQualityRule(
                    rule_id="social_media_data_validation",
                    name="Social Media Data Validation",
                    description="Validates social media sentiment data",
                    source_types=[DataSourceType.SOCIAL_MEDIA],
                    validation_function=self._validate_social_media_data,
                    enabled=True,
                    created_at=datetime.utcnow()
                ),
                DataQualityRule(
                    rule_id="news_feed_data_validation",
                    name="News Feed Data Validation",
                    description="Validates news feed data structure",
                    source_types=[DataSourceType.NEWS_FEEDS],
                    validation_function=self._validate_news_feed_data,
                    enabled=True,
                    created_at=datetime.utcnow()
                )
            ]
            
            for rule in default_rules:
                self.quality_rules[rule.rule_id] = rule
            
            self.logger.info(f"Initialized {len(default_rules)} data quality rules")
            
        except Exception as e:
            self.logger.error(f"Error initializing quality rules: {str(e)}")
    
    def _initialize_data_pipelines(self):
        """Initialize data processing pipelines."""
        try:
            default_pipelines = [
                DataPipeline(
                    pipeline_id="yahoo_finance_pipeline",
                    name="Yahoo Finance Data Pipeline",
                    description="Processes Yahoo Finance API data",
                    source_type=DataSourceType.YAHOO_FINANCE,
                    processors=["fetch_data", "validate_data", "transform_data", "store_data"],
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                DataPipeline(
                    pipeline_id="social_media_pipeline",
                    name="Social Media Data Pipeline",
                    description="Processes social media sentiment data",
                    source_type=DataSourceType.SOCIAL_MEDIA,
                    processors=["fetch_data", "validate_data", "analyze_sentiment", "store_data"],
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                DataPipeline(
                    pipeline_id="news_feed_pipeline",
                    name="News Feed Data Pipeline",
                    description="Processes news feed data",
                    source_type=DataSourceType.NEWS_FEEDS,
                    processors=["fetch_data", "validate_data", "extract_entities", "store_data"],
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for pipeline in default_pipelines:
                self.data_pipelines[pipeline.pipeline_id] = pipeline
            
            self.logger.info(f"Initialized {len(default_pipelines)} data pipelines")
            
        except Exception as e:
            self.logger.error(f"Error initializing data pipelines: {str(e)}")
    
    async def _start_message_queue_listener(self):
        """Start listening to message queue for tasks."""
        try:
            # Connect to Redis
            self.redis_client = await aioredis.create_redis_pool(
                f"redis://{self.config.get('redis_host')}:{self.config.get('redis_port')}/{self.config.get('redis_db')}"
            )
            
            # Listen for messages
            while True:
                try:
                    # Get task from queue
                    message = await self.redis_client.blpop(self.message_queue, timeout=1)
                    if message:
                        task_data = json.loads(message[1])
                        await self._create_task_from_message(task_data)
                except Exception as e:
                    self.logger.error(f"Error processing message from queue: {str(e)}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Error starting message queue listener: {str(e)}")
    
    async def _create_task_from_message(self, task_data: Dict[str, Any]):
        """Create task from message queue data."""
        try:
            task = DataCollectionTask(
                task_id=task_data.get("task_id", str(uuid.uuid4())),
                source_type=DataSourceType(task_data.get("source_type")),
                priority=DataPriority(task_data.get("priority", "normal")),
                source_config=task_data.get("source_config", {}),
                created_at=datetime.utcnow(),
                scheduled_at=datetime.fromisoformat(task_data.get("scheduled_at", datetime.utcnow().isoformat()))
            )
            
            # Store task
            self.collection_tasks[task.task_id] = task
            
            # Add to appropriate priority queue
            await self.task_queues[task.priority].put(task)
            
            self.logger.info(f"Created task {task.task_id} from message queue")
            
        except Exception as e:
            self.logger.error(f"Error creating task from message: {str(e)}")
    
    def _start_workers(self):
        """Start worker processes."""
        try:
            # Create workers for each priority level
            for priority in DataPriority:
                worker_count = self._get_worker_count_for_priority(priority)
                
                for i in range(worker_count):
                    worker_id = f"worker_{priority.value}_{i}"
                    self.workers[worker_id] = asyncio.create_task(
                        self._worker_loop(worker_id, priority)
                    )
            
            self.logger.info(f"Started {len(self.workers)} worker processes")
            
        except Exception as e:
            self.logger.error(f"Error starting workers: {str(e)}")
    
    def _get_worker_count_for_priority(self, priority: DataPriority) -> int:
        """Get number of workers for priority level."""
        if priority == DataPriority.CRITICAL:
            return max(1, self.max_workers // 4)
        elif priority == DataPriority.HIGH:
            return max(2, self.max_workers // 3)
        elif priority == DataPriority.NORMAL:
            return max(3, self.max_workers // 2)
        else:  # LOW
            return max(1, self.max_workers // 4)
    
    async def _worker_loop(self, worker_id: str, priority: DataPriority):
        """Worker process loop."""
        try:
            self.logger.info(f"Worker {worker_id} started for priority {priority.value}")
            
            while self.worker_active:
                try:
                    # Get task from queue
                    task = await asyncio.wait_for(
                        self.task_queues[priority].get(),
                        timeout=1.0
                    )
                    
                    # Process task
                    await self._process_task(task, worker_id)
                    
                except asyncio.TimeoutError:
                    # No task available, continue
                    continue
                except Exception as e:
                    self.logger.error(f"Error in worker {worker_id}: {str(e)}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in worker {worker_id}: {str(e)}")
    
    async def _process_task(self, task: DataCollectionTask, worker_id: str):
        """Process a data collection task."""
        try:
            start_time = time.time()
            
            # Update task status
            task.status = DataStatus.PROCESSING
            task.metadata["worker_id"] = worker_id
            task.metadata["started_at"] = datetime.utcnow().isoformat()
            
            # Get pipeline for source type
            pipeline = self._get_pipeline_for_source(task.source_type)
            if not pipeline:
                await self._fail_task(task, f"No pipeline found for source type: {task.source_type}")
                return
            
            # Execute pipeline processors
            result = await self._execute_pipeline(pipeline, task)
            
            # Validate data quality if enabled
            if self.config.get("quality_check_enabled", True):
                if not await self._validate_data_quality(task.source_type, result):
                    await self._fail_task(task, "Data quality validation failed")
                    return
            
            # Remove duplicates if enabled
            if self.config.get("deduplication_enabled", True):
                result = await self._remove_duplicates(task.source_type, result)
            
            # Update task with result
            task.result = result
            task.status = DataStatus.COMPLETED
            task.processing_time_ms = int((time.time() - start_time) * 1000)
            task.metadata["completed_at"] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.metrics["tasks_processed"] += 1
            self._update_processing_time_metrics(task.processing_time_ms)
            
            # Cache result
            cache_key = f"task_result_{task.task_id}"
            await self.cache_manager.set(cache_key, result, ttl=self.task_cache_ttl)
            
            self.logger.info(f"Worker {worker_id} completed task {task.task_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing task {task.task_id}: {str(e)}")
            await self._retry_task(task, str(e))
    
    async def _execute_pipeline(self, pipeline: DataPipeline, task: DataCollectionTask) -> Dict[str, Any]:
        """Execute data processing pipeline."""
        try:
            result = {"source_config": task.source_config}
            
            for processor in pipeline.processors:
                if processor == "fetch_data":
                    result = await self._fetch_data(task.source_type, task.source_config)
                elif processor == "validate_data":
                    result = await self._validate_source_data(task.source_type, result)
                elif processor == "transform_data":
                    result = await self._transform_data(task.source_type, result)
                elif processor == "analyze_sentiment":
                    result = await self._analyze_sentiment(result)
                elif processor == "extract_entities":
                    result = await self._extract_entities(result)
                elif processor == "store_data":
                    result = await self._store_data(task.source_type, result)
                else:
                    self.logger.warning(f"Unknown processor: {processor}")
                
                if not result:
                    raise Exception(f"Processor {processor} failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing pipeline {pipeline.pipeline_id}: {str(e)}")
            raise
    
    async def _fetch_data(self, source_type: DataSourceType, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from source."""
        try:
            if source_type == DataSourceType.YAHOO_FINANCE:
                return await self._fetch_yahoo_finance_data(config)
            elif source_type == DataSourceType.SOCIAL_MEDIA:
                return await self._fetch_social_media_data(config)
            elif source_type == DataSourceType.NEWS_FEEDS:
                return await self._fetch_news_feed_data(config)
            else:
                return {"error": f"Unsupported source type: {source_type}"}
                
        except Exception as e:
            self.logger.error(f"Error fetching data from {source_type}: {str(e)}")
            raise
    
    async def _fetch_yahoo_finance_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Yahoo Finance API."""
        try:
            symbols = config.get("symbols", [])
            if not symbols:
                return {"error": "No symbols provided"}
            
            # Simulate Yahoo Finance API call
            # In production, this would make actual API calls
            data = {
                "source": "yahoo_finance",
                "symbols": symbols,
                "data": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for symbol in symbols:
                data["data"][symbol] = {
                    "price": 100.0 + (hash(symbol) % 50),
                    "change": (hash(symbol) % 10) - 5,
                    "volume": hash(symbol) % 1000000,
                    "market_cap": hash(symbol) % 1000000000
                }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching Yahoo Finance data: {str(e)}")
            raise
    
    async def _fetch_social_media_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from social media APIs."""
        try:
            platforms = config.get("platforms", [])
            keywords = config.get("keywords", [])
            
            if not platforms or not keywords:
                return {"error": "No platforms or keywords provided"}
            
            # Simulate social media data collection
            # In production, this would make actual API calls
            data = {
                "source": "social_media",
                "platforms": platforms,
                "keywords": keywords,
                "posts": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for platform in platforms:
                for keyword in keywords:
                    # Generate mock posts
                    for i in range(5):
                        sentiment_score = (hash(keyword + platform + str(i)) % 100) / 100
                        data["posts"].append({
                            "platform": platform,
                            "keyword": keyword,
                            "content": f"Mock content about {keyword} on {platform}",
                            "sentiment": sentiment_score,
                            "timestamp": datetime.utcnow().isoformat(),
                            "engagement": hash(keyword + str(i)) % 1000
                        })
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching social media data: {str(e)}")
            raise
    
    async def _fetch_news_feed_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from news feed APIs."""
        try:
            sources = config.get("sources", [])
            categories = config.get("categories", [])
            
            if not sources:
                return {"error": "No news sources provided"}
            
            # Simulate news feed data collection
            # In production, this would make actual API calls
            data = {
                "source": "news_feeds",
                "sources": sources,
                "categories": categories,
                "articles": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for source in sources:
                for category in categories:
                    # Generate mock articles
                    for i in range(3):
                        data["articles"].append({
                            "source": source,
                            "category": category,
                            "title": f"Mock {category} article from {source}",
                            "content": f"Mock content about {category}",
                            "url": f"https://{source}/article/{hash(source + category + str(i))}",
                            "published_at": datetime.utcnow().isoformat(),
                            "sentiment": (hash(source + category + str(i)) % 100) / 100
                        })
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching news feed data: {str(e)}")
            raise
    
    async def _validate_source_data(self, source_type: DataSourceType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate source data structure."""
        try:
            # Basic validation
            if not data or "error" in data:
                raise Exception("Invalid data structure")
            
            # Source-specific validation
            if source_type == DataSourceType.YAHOO_FINANCE:
                if "symbols" not in data or "data" not in data:
                    raise Exception("Missing required Yahoo Finance fields")
            elif source_type == DataSourceType.SOCIAL_MEDIA:
                if "posts" not in data:
                    raise Exception("Missing required social media fields")
            elif source_type == DataSourceType.NEWS_FEEDS:
                if "articles" not in data:
                    raise Exception("Missing required news feed fields")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error validating {source_type} data: {str(e)}")
            raise
    
    async def _transform_data(self, source_type: DataSourceType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data to standard format."""
        try:
            # Add transformation metadata
            transformed_data = {
                **data,
                "transformed_at": datetime.utcnow().isoformat(),
                "transformation_version": "1.0"
            }
            
            # Source-specific transformations
            if source_type == DataSourceType.YAHOO_FINANCE:
                # Add calculated fields
                for symbol, stock_data in transformed_data["data"].items():
                    stock_data["pe_ratio"] = stock_data["price"] / (hash(symbol) % 10 + 1)
                    stock_data["market_cap_rank"] = hash(symbol) % 100
            
            elif source_type == DataSourceType.SOCIAL_MEDIA:
                # Add sentiment aggregation
                posts = transformed_data["posts"]
                if posts:
                    avg_sentiment = sum(post["sentiment"] for post in posts) / len(posts)
                    transformed_data["sentiment_summary"] = {
                        "average_sentiment": avg_sentiment,
                        "total_posts": len(posts),
                        "positive_posts": len([p for p in posts if p["sentiment"] > 0.5]),
                        "negative_posts": len([p for p in posts if p["sentiment"] < -0.5])
                    }
            
            return transformed_data
            
        except Exception as e:
            self.logger.error(f"Error transforming {source_type} data: {str(e)}")
            raise
    
    async def _analyze_sentiment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment in data."""
        try:
            # Add sentiment analysis metadata
            analyzed_data = {
                **data,
                "sentiment_analyzed_at": datetime.utcnow().isoformat(),
                "sentiment_model": "mock_v1.0"
            }
            
            # Analyze sentiment for posts/articles
            if "posts" in data:
                for post in analyzed_data["posts"]:
                    # Mock sentiment analysis
                    post["sentiment_details"] = {
                        "positive": max(0, post["sentiment"]),
                        "negative": max(0, -post["sentiment"]),
                        "neutral": 1 - abs(post["sentiment"]),
                        "confidence": 0.8
                    }
            
            if "articles" in data:
                for article in analyzed_data["articles"]:
                    # Mock sentiment analysis
                    article["sentiment_details"] = {
                        "positive": max(0, article["sentiment"]),
                        "negative": max(0, -article["sentiment"]),
                        "neutral": 1 - abs(article["sentiment"]),
                        "confidence": 0.8
                    }
            
            return analyzed_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
    
    async def _extract_entities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from data."""
        try:
            # Add entity extraction metadata
            entity_data = {
                **data,
                "entities_extracted_at": datetime.utcnow().isoformat(),
                "entity_model": "mock_v1.0"
            }
            
            # Extract entities from articles
            if "articles" in data:
                for article in entity_data["articles"]:
                    # Mock entity extraction
                    article["entities"] = {
                        "companies": ["MockCompany", "Initech"],
                        "people": ["John Doe", "Jane Smith"],
                        "locations": ["New York", "London"],
                        "topics": ["finance", "technology", "stocks"]
                    }
            
            return entity_data
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {str(e)}")
            raise
    
    async def _store_data(self, source_type: DataSourceType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed data."""
        try:
            # Add storage metadata
            stored_data = {
                **data,
                "stored_at": datetime.utcnow().isoformat(),
                "storage_location": "distributed_cache"
            }
            
            # Generate storage key
            storage_key = f"{source_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Store in cache
            await self.cache_manager.set(storage_key, stored_data, ttl=86400)  # 24 hours
            
            # Add storage info to data
            stored_data["storage_key"] = storage_key
            
            return stored_data
            
        except Exception as e:
            self.logger.error(f"Error storing {source_type} data: {str(e)}")
            raise
    
    def _get_pipeline_for_source(self, source_type: DataSourceType) -> Optional[DataPipeline]:
        """Get data pipeline for source type."""
        for pipeline in self.data_pipelines.values():
            if pipeline.source_type == source_type and pipeline.enabled:
                return pipeline
        return None
    
    async def _validate_data_quality(self, source_type: DataSourceType, data: Dict[str, Any]) -> bool:
        """Validate data quality using rules."""
        try:
            for rule in self.quality_rules.values():
                if (rule.enabled and 
                    source_type in rule.source_types and 
                    not rule.validation_function(data)):
                    self.logger.warning(f"Data quality rule {rule.rule_id} failed for {source_type}")
                    return False
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating data quality: {str(e)}")
            return False
    
    async def _remove_duplicates(self, source_type: DataSourceType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate data entries."""
        try:
            # Simple duplicate removal based on content hash
            if source_type == DataSourceType.SOCIAL_MEDIA and "posts" in data:
                seen_hashes = set()
                unique_posts = []
                
                for post in data["posts"]:
                    content_hash = hashlib.md5(post["content"].encode()).hexdigest()
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        unique_posts.append(post)
                
                data["posts"] = unique_posts
                data["duplicates_removed"] = len(data.get("posts", [])) - len(unique_posts)
            
            elif source_type == DataSourceType.NEWS_FEEDS and "articles" in data:
                seen_hashes = set()
                unique_articles = []
                
                for article in data["articles"]:
                    content_hash = hashlib.md5(article["title"] + article["content"]).encode().hexdigest()
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        unique_articles.append(article)
                
                data["articles"] = unique_articles
                data["duplicates_removed"] = len(data.get("articles", [])) - len(unique_articles)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error removing duplicates: {str(e)}")
            return data
    
    def _validate_yahoo_finance_data(self, data: Dict[str, Any]) -> bool:
        """Validate Yahoo Finance data structure."""
        try:
            if "symbols" not in data or "data" not in data:
                return False
            
            for symbol, stock_data in data["data"].items():
                required_fields = ["price", "change", "volume"]
                for field in required_fields:
                    if field not in stock_data:
                        return False
                    
                    # Validate data types and ranges
                    if field in ["price", "change", "volume"]:
                        if not isinstance(stock_data[field], (int, float)):
                            return False
                        if stock_data[field] < 0:
                            return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating Yahoo Finance data: {str(e)}")
            return False
    
    def _validate_social_media_data(self, data: Dict[str, Any]) -> bool:
        """Validate social media data structure."""
        try:
            if "posts" not in data:
                return False
            
            for post in data["posts"]:
                required_fields = ["platform", "content", "sentiment"]
                for field in required_fields:
                    if field not in post:
                        return False
                
                # Validate sentiment range
                if not isinstance(post["sentiment"], (int, float)):
                    return False
                if post["sentiment"] < -1 or post["sentiment"] > 1:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating social media data: {str(e)}")
            return False
    
    def _validate_news_feed_data(self, data: Dict[str, Any]) -> bool:
        """Validate news feed data structure."""
        try:
            if "articles" not in data:
                return False
            
            for article in data["articles"]:
                required_fields = ["title", "content", "source"]
                for field in required_fields:
                    if field not in article:
                        return False
                
                # Validate sentiment range
                if "sentiment" in article:
                    if not isinstance(article["sentiment"], (int, float)):
                        return False
                    if article["sentiment"] < -1 or article["sentiment"] > 1:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating news feed data: {str(e)}")
            return False
    
    async def _retry_task(self, task: DataCollectionTask, error_message: str):
        """Retry a failed task."""
        try:
            task.retry_count += 1
            task.error_message = error_message
            
            if task.retry_count >= task.max_retries:
                await self._fail_task(task, f"Max retries exceeded: {error_message}")
            else:
                task.status = DataStatus.RETRYING
                task.metadata["retry_at"] = (datetime.utcnow() + timedelta(seconds=self.config.get("retry_delay", 60))).isoformat()
                
                # Schedule retry
                await asyncio.sleep(self.config.get("retry_delay", 60))
                await self.task_queues[task.priority].put(task)
                
                self.logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
            
        except Exception as e:
            self.logger.error(f"Error retrying task {task.task_id}: {str(e)}")
            await self._fail_task(task, f"Retry failed: {str(e)}")
    
    async def _fail_task(self, task: DataCollectionTask, error_message: str):
        """Mark task as failed."""
        try:
            task.status = DataStatus.FAILED
            task.error_message = error_message
            task.metadata["failed_at"] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.metrics["tasks_failed"] += 1
            
            self.logger.error(f"Task {task.task_id} failed: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error failing task {task.task_id}: {str(e)}")
    
    def _update_processing_time_metrics(self, processing_time_ms: int):
        """Update processing time metrics."""
        try:
            current_avg = self.metrics["avg_processing_time_ms"]
            total_tasks = self.metrics["tasks_processed"]
            
            # Calculate new average
            new_avg = ((current_avg * (total_tasks - 1)) + processing_time_ms) / total_tasks
            self.metrics["avg_processing_time_ms"] = round(new_avg, 2)
            
        except Exception as e:
            self.logger.error(f"Error updating processing time metrics: {str(e)}")
    
    async def create_collection_task(
        self,
        source_type: DataSourceType,
        priority: DataPriority,
        source_config: Dict[str, Any],
        scheduled_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a new data collection task."""
        try:
            task_id = str(uuid.uuid4())
            
            task = DataCollectionTask(
                task_id=task_id,
                source_type=source_type,
                priority=priority,
                source_config=source_config,
                created_at=datetime.utcnow(),
                scheduled_at=scheduled_at or datetime.utcnow()
            )
            
            # Store task
            self.collection_tasks[task_id] = task
            
            # Add to appropriate priority queue
            if scheduled_at and scheduled_at > datetime.utcnow():
                # Schedule for later
                await asyncio.sleep((scheduled_at - datetime.utcnow()).total_seconds())
            
            await self.task_queues[task.priority].put(task)
            
            # Cache task
            cache_key = f"collection_task_{task_id}"
            await self.cache_manager.set(cache_key, task.__dict__, ttl=self.task_cache_ttl)
            
            self.logger.info(f"Created collection task: {task_id}")
            
            return {
                "success": True,
                "task_id": task_id,
                "priority": priority.value,
                "source_type": source_type.value,
                "scheduled_at": task.scheduled_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating collection task: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_collection_tasks(
        self,
        source_type: Optional[DataSourceType] = None,
        status: Optional[DataStatus] = None,
        priority: Optional[DataPriority] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get collection tasks with optional filtering."""
        try:
            tasks = list(self.collection_tasks.values())
            
            # Apply filters
            if source_type:
                tasks = [t for t in tasks if t.source_type == source_type]
            
            if status:
                tasks = [t for t in tasks if t.status == status]
            
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            
            # Sort by creation date (newest first)
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply limit
            tasks = tasks[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "task_id": t.task_id,
                    "source_type": t.source_type.value,
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat(),
                    "scheduled_at": t.scheduled_at.isoformat(),
                    "retry_count": t.retry_count,
                    "max_retries": t.max_retries,
                    "processing_time_ms": t.processing_time_ms,
                    "error_message": t.error_message,
                    "metadata": t.metadata
                }
                for t in tasks
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting collection tasks: {str(e)}")
            return []
    
    async def get_data_pipelines(self) -> List[Dict[str, Any]]:
        """Get all data pipelines."""
        try:
            pipelines = list(self.data_pipelines.values())
            
            # Convert to dictionaries
            return [
                {
                    "pipeline_id": p.pipeline_id,
                    "name": p.name,
                    "description": p.description,
                    "source_type": p.source_type.value,
                    "processors": p.processors,
                    "enabled": p.enabled,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in pipelines
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting data pipelines: {str(e)}")
            return []
    
    async def get_quality_rules(self) -> List[Dict[str, Any]]:
        """Get all data quality rules."""
        try:
            rules = list(self.quality_rules.values())
            
            # Convert to dictionaries
            return [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "source_types": [st.value for st in r.source_types],
                    "enabled": r.enabled,
                    "created_at": r.created_at.isoformat()
                }
                for r in rules
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting quality rules: {str(e)}")
            return []
    
    async def get_collection_metrics(self) -> Dict[str, Any]:
        """Get data collection metrics."""
        try:
            # Update queue sizes
            for priority, queue in self.task_queues.items():
                self.metrics["queue_sizes"][priority.value] = queue.qsize()
            
            # Calculate worker utilization
            active_workers = sum(1 for w in self.workers.values() if not w.done())
            self.metrics["worker_utilization"] = {
                "active_workers": active_workers,
                "total_workers": len(self.workers),
                "utilization_percent": round((active_workers / len(self.workers)) * 100, 2) if self.workers else 0
            }
            
            return {
                "tasks_processed": self.metrics["tasks_processed"],
                "tasks_failed": self.metrics["tasks_failed"],
                "success_rate": round(
                    ((self.metrics["tasks_processed"] - self.metrics["tasks_failed"]) / 
                     max(1, self.metrics["tasks_processed"])) * 100, 2
                ),
                "avg_processing_time_ms": self.metrics["avg_processing_time_ms"],
                "queue_sizes": self.metrics["queue_sizes"],
                "worker_utilization": self.metrics["worker_utilization"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting collection metrics: {str(e)}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown the distributed data collector."""
        try:
            self.logger.info("Shutting down distributed data collector...")
            
            # Stop workers
            self.worker_active = False
            
            # Wait for workers to finish
            if self.workers:
                await asyncio.gather(*self.workers.values(), return_exceptions=True)
            
            # Close Redis connection
            if self.redis_client:
                self.redis_client.close()
                await self.redis_client.wait_closed()
            
            self.logger.info("Distributed data collector shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")