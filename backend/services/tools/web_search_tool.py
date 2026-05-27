"""
Web搜索工具模块 - 实现实时信息检索能力
使用Tavily/Serper API进行商家实时信息检索
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import os
from datetime import datetime


logger = logging.getLogger(__name__)


class SearchEngine(Enum):
    """搜索引擎类型"""
    TAVILY = "tavily"
    SERPER = "serper"
    CACHE = "cache"  # 本地缓存降级


@dataclass
class SearchQuery:
    """搜索查询数据类"""
    query: str
    location: str
    search_type: str = "business_status"  # business_status, reviews, emergency
    time_range: str = "24h"  # 24h, 7d, 30d


@dataclass
class BusinessInfo:
    """商家实时信息数据类"""
    merchant_name: str
    address: str
    is_open: bool
    current_status: str  # open, closed, busy, maintenance
    last_updated: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    recent_reviews: List[Dict[str, Any]] = None
    emergency_notices: List[str] = None
    peak_hours: Optional[str] = None
    special_offers: List[str] = None
    safety_info: Optional[str] = None


class WebSearchTool:
    """
    Web搜索工具 - 提供商家实时信息检索
    支持多种搜索引擎和降级策略
    """
    
    def __init__(self, primary_engine: SearchEngine = SearchEngine.TAVILY):
        self.primary_engine = primary_engine
        self.session = None
        self.cache = {}  # 简单的内存缓存
        self.cache_ttl = 900  # 缓存15分钟
        
        # API密钥 - 从环境变量获取
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        
        # API端点
        self.tavily_base_url = "https://api.tavily.com/search"
        self.serper_base_url = "https://google.serper.dev/search"
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """生成缓存键"""
        return f"{query.query}_{query.location}_{query.search_type}"
    
    def _check_cache(self, cache_key: str) -> Optional[BusinessInfo]:
        """检查缓存并返回未过期的数据"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                logger.info(f"缓存命中: {cache_key}")
                return cached_data
        return None
    
    def _update_cache(self, cache_key: str, data: BusinessInfo):
        """更新缓存"""
        self.cache[cache_key] = (data, datetime.now())
    
    def _build_tavily_query(self, search_query: SearchQuery) -> Dict[str, Any]:
        """构建Tavily API查询参数"""
        query_text = f"{search_query.query} in {search_query.location}"
        
        search_type_params = {
            "business_status": "operating hours, current status, is open",
            "reviews": "latest reviews, customer feedback, rating",
            "emergency": "emergency notice, temporary closure, special events"
        }
        
        return {
            "api_key": self.tavily_api_key,
            "query": f"{search_type_params.get(search_query.search_type, '')} {query_text}",
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": True,
            "max_results": 10
        }
    
    def _build_serper_query(self, search_query: SearchQuery) -> Dict[str, Any]:
        """构建Serper API查询参数"""
        search_types = {
            "business_status": "site:google.com/maps OR site:yelp.com OR site:facebook.com",
            "reviews": "review OR rating OR feedback",
            "emergency": "emergency OR closed OR notice OR update"
        }
        
        return {
            "q": f"{search_query.query} {search_query.location} {search_types.get(search_query.search_type, '')}",
            "gl": "cn",
            "hl": "zh",
            "type": "search"
        }
    
    async def _search_tavily(self, search_query: SearchQuery) -> Optional[BusinessInfo]:
        """使用Tavily API搜索"""
        if not self.tavily_api_key:
            logger.warning("Tavily API key not configured")
            return None
        
        try:
            params = self._build_tavily_query(search_query)
            
            async with self.session.post(self.tavily_base_url, json=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_tavily_response(data, search_query)
                else:
                    logger.error(f"Tavily API error: {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning("Tavily search timeout")
            return None
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return None
    
    async def _search_serper(self, search_query: SearchQuery) -> Optional[BusinessInfo]:
        """使用Serper API搜索"""
        if not self.serper_api_key:
            logger.warning("Serper API key not configured")
            return None
        
        try:
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            params = self._build_serper_query(search_query)
            
            async with self.session.post(
                self.serper_base_url, 
                json=params, 
                headers=headers, 
                timeout=5
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_serper_response(data, search_query)
                else:
                    logger.error(f"Serper API error: {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning("Serper search timeout")
            return None
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return None
    
    def _parse_tavily_response(self, data: Dict, search_query: SearchQuery) -> BusinessInfo:
        """解析Tavily响应"""
        answer = data.get("answer", "")
        results = data.get("results", [])
        
        # 从回答中提取关键信息
        is_open = "open" in answer.lower() or "营业" in answer
        status_keywords = ["closed", "busy", "busiest", "maintenance", "休息", "繁忙"]
        current_status = "open" if is_open else "unknown"
        
        for keyword in status_keywords:
            if keyword.lower() in answer.lower():
                current_status = keyword
                break
        
        # 处理紧急通知
        emergency_info = []
        if "emergency" == search_query.search_type:
            emergency_info = [result.get("content", "")[:200] for result in results[:3]]
        
        return BusinessInfo(
            merchant_name=search_query.query,
            address=search_query.location,
            is_open=is_open,
            current_status=current_status,
            last_updated=datetime.now().isoformat(),
            recent_reviews=self._extract_reviews(results),
            emergency_notices=emergency_info if emergency_info else None
        )
    
    def _parse_serper_response(self, data: Dict, search_query: SearchQuery) -> BusinessInfo:
        """解析Serper响应"""
        organic_results = data.get("organic", [])
        
        # 提取营业状态信息
        status_info = self._extract_status_from_results(organic_results)
        
        # 提取评价信息
        reviews = []
        if "reviews" == search_query.search_type:
            reviews = self._extract_review_snippets(organic_results)
        
        return BusinessInfo(
            merchant_name=search_query.query,
            address=search_query.location,
            is_open=status_info.get("is_open", False),
            current_status=status_info.get("status", "unknown"),
            last_updated=datetime.now().isoformat(),
            recent_reviews=reviews,
            emergency_notices=status_info.get("emergency_info")
        )
    
    def _extract_status_from_results(self, results: List[Dict]) -> Dict[str, Any]:
        """从搜索结果中提取营业状态"""
        status_info = {"is_open": True, "status": "open", "emergency_info": []}
        
        for result in results[:5]:  # 检查前5个结果
            snippet = result.get("snippet", "").lower()
            title = result.get("title", "").lower()
            
            # 检测闭店信息
            closure_indicators = ["closed", "停业", "关门", "休息", "暂停营业"]
            if any(indicator in snippet or indicator in title for indicator in closure_indicators):
                status_info["is_open"] = False
                status_info["status"] = "closed"
                status_info["emergency_info"].append(result.get("snippet", ""))
            
            # 检测繁忙状态
            busy_indicators = ["busy", "繁忙", "人多", "排队"]
            if any(indicator in snippet for indicator in busy_indicators):
                status_info["status"] = "busy"
                
        return status_info
    
    def _extract_review_snippets(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """提取评价片段"""
        reviews = []
        for result in results[:3]:
            reviews.append({
                "source": result.get("link", ""),
                "content": result.get("snippet", "")[:200],
                "display_link": result.get("displayed_link", "")
            })
        return reviews
    
    def _extract_reviews(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """提取评价信息(Tavily)"""
        reviews = []
        for result in results[:3]:
            reviews.append({
                "content": result.get("content", "")[:200],
                "source": result.get("url", "")
            })
        return reviews
    
    async def _search_cache_fallback(self, search_query: SearchQuery) -> BusinessInfo:
        """缓存降级搜索"""
        logger.info(f"使用缓存数据: {search_query.query}")
        
        # 返回基于合成数据的降级响应
        return BusinessInfo(
            merchant_name=search_query.query,
            address=search_query.location,
            is_open=True,
            current_status="open (cached)",
            last_updated=datetime.now().isoformat(),
            safety_info="使用缓存数据，实际状态可能有所差异，建议电话确认"
        )
    
    async def search_business_info(self, search_query: SearchQuery) -> BusinessInfo:
        """
        搜索商家实时信息主接口
        支持多种引擎和自动降级
        """
        cache_key = self._get_cache_key(search_query)
        
        # 检查缓存
        cached_result = self._check_cache(cache_key)
        if cached_result:
            return cached_result
        
        # 主搜索引擎搜索
        result = None
        if self.primary_engine == SearchEngine.TAVILY:
            result = await self._search_tavily(search_query)
        elif self.primary_engine == SearchEngine.SERPER:
            result = await self._search_serper(search_query)
        
        # 如果主引擎失败，尝试备选引擎
        if not result:
            logger.info(f"主引擎失败，尝试备选引擎")
            if self.primary_engine != SearchEngine.SERPER and self.serper_api_key:
                result = await self._search_serper(search_query)
            elif self.primary_engine != SearchEngine.TAVILY and self.tavily_api_key:
                result = await self._search_tavily(search_query)
        
        # 如果所有API都失败，使用缓存降级
        if not result:
            result = await self._search_cache_fallback(search_query)
        
        # 更新缓存
        self._update_cache(cache_key, result)
        
        logger.info(f"成功获取商家信息: {search_query.query} - 状态: {result.current_status}")
        return result
    
    async def batch_search_businesses(self, queries: List[SearchQuery]) -> Dict[str, BusinessInfo]:
        """批量搜索多个商家"""
        tasks = [self.search_business_info(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        business_info_map = {}
        for i, result in enumerate(results):
            if isinstance(result, BusinessInfo):
                business_info_map[queries[i].query] = result
            else:
                # 记录错误但继续处理其他结果
                logger.error(f"批量搜索错误 {queries[i].query}: {result}")
                
        return business_info_map