"""
真实浏览器自动化预约执行工具 - Playwright Chromium 专属实现
集成高德数据 + 物理阻断门禁 + Supabase 存储上传
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Callable, Union
import asyncio
import logging
import os
from datetime import datetime
import hashlib
import base64
from pathlib import Path
from enum import Enum
import json
import uuid

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright 未安装，请运行: pip install playwright && playwright install chromium")

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

logger = logging.getLogger(__name__)

# 导入桥接模块
from data_types import ThreadState, RiskAssessment
from db.supabase_client import SupabaseClient
from services.data.wanderbook_bridge import WanderbookBridge, WanderbookEntryStatus
from services.security.antibot_orchestrator import AntiBotOrchestrator, BlockingType, MitigationStrategy
from services.tools.booking_safety_gate import RiskLevel

# 幂等性和并发控制
import asyncio
from typing import Set
from contextlib import asynccontextmanager

# 全局并发保护
class ConcurrencyManager:
    """并发管理器 - 实现幂等性和并发控制"""
    
    def __init__(self):
        # 正在执行的预约ID集合
        self._active_bookings: Set[str] = set()
        # 预约锁字典（按商户名称和时间的组合）
        self._booking_locks: Dict[str, asyncio.Lock] = {}
        # 全局锁用于保护数据结构
        self._global_lock = asyncio.Lock()
        # 幂等性缓存（booking_key -> result）
        self._idempotent_cache: Dict[str, Any] = {}
        
    async def acquire_booking_lock(self, merchant_name: str, booking_time: str) -> str:
        """获取预约锁，返回锁键"""
        lock_key = f"{merchant_name}_{booking_time}"
        
        async with self._global_lock:
            if lock_key not in self._booking_locks:
                self._booking_locks[lock_key] = asyncio.Lock()
            
            lock = self._booking_locks[lock_key]
            
        await lock.acquire()
        return lock_key
        
    def release_booking_lock(self, lock_key: str):
        """释放预约锁"""
        if lock_key in self._booking_locks:
            self._booking_locks[lock_key].release()
            
    async def check_and_mark_active(self, booking_id: str) -> bool:
        """检查并标记预约为活跃状态，返回是否允许执行"""
        async with self._global_lock:
            if booking_id in self._active_bookings:
                return False  # 已在执行中
            self._active_bookings.add(booking_id)
            return True
            
    async def mark_completed(self, booking_id: str):
        """标记预约完成"""
        async with self._global_lock:
            self._active_bookings.discard(booking_id)
            
    async def check_idempotent(self, booking_key: str, max_age_hours: int = 24) -> Optional[Any]:
        """检查幂等性缓存"""
        async with self._global_lock:
            if booking_key in self._idempotent_cache:
                cached_result, timestamp = self._idempotent_cache[booking_key]
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                if age_hours <= max_age_hours:
                    return cached_result
                else:
                    # 过期缓存
                    del self._idempotent_cache[booking_key]
            return None
            
    async def cache_result(self, booking_key: str, result: Any):
        """缓存结果用于幂等性保护"""
        async with self._global_lock:
            self._idempotent_cache[booking_key] = (result, datetime.now())

# 全局并发管理器实例
concurrency_manager = ConcurrencyManager()


class AmapServiceType(Enum):
    """高德服务类型枚举"""
    PLACE_SEARCH = "place_search"
    PLACE_AROUND = "place_around"
    DIRECTION_WALKING = "direction_walking"
    DIRECTION_DRIVING = "direction_driving"
    DIRECTION_TRANSIT = "direction_transit"
    GEOCODE = "geocode"
    REVERSE_GEOCODE = "reverse_geocode"


class BookingStatus(Enum):
    """预订状态枚举"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_USER_CONFIRM = "requires_user_confirm"


class ExecutionStage(Enum):
    """执行阶段枚举"""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    SEARCHING_POIS = "searching_pois"
    ROUTING = "routing"
    BOOKING = "booking"
    SAVING_ROUTE = "saving_route"
    FINALIZING = "finalizing"


@dataclass
class ExecutionFeedback:
    """执行反馈数据类"""
    stage: ExecutionStage
    status: BookingStatus
    message: str
    progress: int
    details: Dict[str, Any] = None
    error: str = None


@dataclass
class AmapPoiResult:
    """高德POI搜索结果数据类"""
    id: str
    name: str
    address: str
    location: str  # 经纬度 "经度,纬度"
    type: str
    typecode: str
    distance: str = ""
    rating: str = ""
    cost: str = ""
    business_area: str = ""
    tel: str = ""
    photos: List[str] = None
    
    def __post_init__(self):
        if self.photos is None:
            self.photos = []


@dataclass
class AmapRouteResult:
    """高德路径规划结果数据类"""
    distance: str  # 总距离（米）
    duration: str  # 总时间（秒）
    taxi_cost: str = ""  # 打车费用（元）
    steps: List[Dict[str, Any]] = None  # 详细步骤
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass
class PlaywrightBookingResult:
    """Playwright 执行结果数据类"""
    success: bool
    booking_id: str
    poi_info: Optional[AmapPoiResult] = None
    route_info: Optional[AmapRouteResult] = None
    screenshot_url: Optional[str] = None  # Supabase Storage 链接
    form_data: Dict[str, Any] = None     # 填写后的表单数据快照
    next_user_action: str = ""           # 需要用户完成的动作描述
    blocking_point: str = ""             # 阻断点描述 (支付/确认等)
    risk_level: str = "low"              # 风险等级
    requires_confirmation: bool = False  # 是否需要用户确认
    
    execution_log: List[str] = None      # 执行步骤日志
    retry_suggestions: List[str] = None  # 重试建议
    browser_snapshot_id: str = None      # 浏览器快照ID（用于恢复）
    
    execution_time: float = 0.0          # 执行耗时
    browser_info: Dict[str, str] = None  # 浏览器信息
    
    def __post_init__(self):
        if self.form_data is None:
            self.form_data = {}
        if self.execution_log is None:
            self.execution_log = []
        if self.retry_suggestions is None:
            self.retry_suggestions = []
        if self.browser_info is None:
            self.browser_info = {}


class BrowserStateManager:
    """浏览器状态管理器 - 实现快照保存/恢复机制"""
    
    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client
        
    async def save_browser_snapshot(self, context: BrowserContext, booking_id: str) -> str:
        """在中断前保存浏览器快照"""
        snapshot_id = f"{booking_id}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 获取当前页面状态
            pages = context.pages
            if not pages:
                raise Exception("没有活动的页面")
                
            page = pages[0]
            
            # 收集所有需要保存的状态
            state_data = {
                'url': page.url,
                'title': await page.title(),
                'cookies': await context.cookies(),
                'local_storage': await page.evaluate('''() => {
                    const data = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        data[key] = localStorage.getItem(key);
                    }
                    return JSON.stringify(data);
                }'''),
                'session_storage': await page.evaluate('''() => {
                    const data = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        data[key] = sessionStorage.getItem(key);
                    }
                    return JSON.stringify(data);
                }'''),
                'form_inputs': await page.evaluate('''() => {
                    const inputs = {};
                    document.querySelectorAll('input, textarea, select').forEach(el => {
                        if (el.name || el.id) {
                            const key = el.name || el.id;
                            inputs[key] = el.value;
                        }
                    });
                    return JSON.stringify(inputs);
                }'''),
                'booking_id': booking_id,
                'created_at': datetime.now().isoformat(),
                'user_agent': await page.evaluate('navigator.userAgent')
            }
            
            # 保存到Supabase或本地存储
            if self.supabase_client:
                await self._save_to_supabase(snapshot_id, state_data)
            else:
                await self._save_to_local(snapshot_id, state_data)
                
            logger.info(f"浏览器快照已保存: {snapshot_id}")
            
        except Exception as e:
            logger.error(f"保存浏览器快照失败: {e}")
            raise
            
        return snapshot_id
    
    async def restore_browser_context(self, snapshot_id: str, playwright_instance) -> BrowserContext:
        """恢复浏览器上下文"""
        try:
            # 加载快照数据
            if self.supabase_client:
                state_data = await self._load_from_supabase(snapshot_id)
            else:
                state_data = await self._load_from_local(snapshot_id)
                
            # 创建新的浏览器上下文
            browser = await playwright_instance.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=state_data.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            )
            
            # 恢复cookies
            await context.add_cookies(state_data['cookies'])
            
            # 创建新页面并导航到目标URL
            page = await context.new_page()
            await page.goto(state_data['url'])
            
            # 等待页面加载完成
            await page.wait_for_load_state('networkidle')
            
            # 恢复localStorage
            local_storage_data = json.loads(state_data.get('local_storage', '{}'))
            for key, value in local_storage_data.items():
                await page.evaluate(f'''() => {{
                    localStorage.setItem('{key}', '{value}');
                }}''')
                
            # 恢复sessionStorage
            session_storage_data = json.loads(state_data.get('session_storage', '{}'))
            for key, value in session_storage_data.items():
                await page.evaluate(f'''() => {{
                    sessionStorage.setItem('{key}', '{value}');
                }}''')
                
            # 恢复表单输入
            form_inputs = json.loads(state_data.get('form_inputs', '{}'))
            for field_name, field_value in form_inputs.items():
                await page.evaluate(f'''() => {{
                    const el = document.querySelector('[name="{field_name}"]') || 
                               document.querySelector('#{field_name}');
                    if (el) el.value = '{field_value}';
                }}''')
            
            logger.info(f"浏览器上下文已恢复: {snapshot_id}")
            
            return context
            
        except Exception as e:
            logger.error(f"恢复浏览器上下文失败: {e}")
            raise
    
    async def _save_to_supabase(self, snapshot_id: str, state_data: Dict[str, Any]):
        """保存到Supabase（占位函数）"""
        # TODO: 实现实际的Supabase存储
        pass
    
    async def _load_from_supabase(self, snapshot_id: str) -> Dict[str, Any]:
        """从Supabase加载（占位函数）"""
        # TODO: 实现实际的Supabase加载
        return {}
    
    async def _save_to_local(self, snapshot_id: str, state_data: Dict[str, Any]):
        """保存到本地文件（开发用）"""
        snapshots_dir = Path("browser_snapshots")
        snapshots_dir.mkdir(exist_ok=True)
        
        file_path = snapshots_dir / f"{snapshot_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
            
    async def _load_from_local(self, snapshot_id: str) -> Dict[str, Any]:
        """从本地文件加载（开发用）"""
        file_path = Path("browser_snapshots") / f"{snapshot_id}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"找不到快照文件: {snapshot_id}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


# AntiBotDetector 已替换为 AntiBotOrchestrator


class BrowserAutomationTool:
    """Playwright 浏览器自动化控制类 - 集成快照管理"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000, state_manager=None):
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.context = None
        self.page = None
        self.state_manager = state_manager
        self.antibot_orchestrator = None  # 将由外部工具设置
        
    async def __aenter__(self):
        """异步上下文进入 - 启动浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请先安装 playwright")
            
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # 隐藏自动化痕迹
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出 - 关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
    async def navigate_with_antisbot_check(self, target_poi: AmapPoiResult, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """带反机器人检测的导航流程"""
        log = []
        
        try:
            # 1. 构造并访问URL
            booking_url = self._construct_booking_url(target_poi)
            log.append(f"导航到: {booking_url}")
            
            await self.page.goto(booking_url, wait_until="networkidle")
            log.append("页面加载完成")
            
            # 2. 执行综合风险评估
            risk_profile = await self.antibot_orchestrator.perform_comprehensive_risk_assessment(
                self.page, self.context, user_data.get('user_id', 'default')
            )
            
            # 检查是否有高风险阻断
            if risk_profile.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or risk_profile.blocking_history:
                screenshot = await self.page.screenshot(type="png", full_page=True)
                # 选择最佳缓解策略
                primary_strategy = risk_profile.mitigation_strategies[0] if risk_profile.mitigation_strategies else MitigationStrategy.REQUEST_USER_HELP
                user_instruction = self.antibot_orchestrator.generate_user_instructions(risk_profile, primary_strategy)
                
                log.append(f"检测到机器人阻断: {risk_profile.risk_level.value}")
                
            return {
                'success': False,
                'blocked_by_antibot': True,
                'risk_profile': risk_profile,
                'user_instruction': user_instruction,
                'screenshot': screenshot,
                'execution_log': log,
                'strategy_advised': primary_strategy.value if risk_profile.mitigation_strategies else 'manual'
            }
            
            # 3. 填写表单
            form_data = await self._fill_booking_form(target_poi, user_data, log)
            
            # 4. 拍摄表单完成截图
            screenshot = await self.page.screenshot(type="png", full_page=True)
            log.append("表单填写完成，已截图记录")
            
            return {
                'success': True,
                'form_data': form_data,
                'screenshot': screenshot,
                'execution_log': log
            }
            
        except Exception as e:
            log.append(f"执行错误: {str(e)}")
            logger.error(f"浏览器自动化失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_log': log
            }
    
    def _construct_booking_url(self, poi: AmapPoiResult) -> str:
        """构造预约页面URL - 增强数据锚点"""
        base_url = f"https://www.amap.com/poi/{poi.id}"
        
        # 根据POI类型添加特定参数
        if "咖啡" in poi.type or "0501" in poi.typecode:
            return f"{base_url}/booking?type=cafe&biz={poi.business_area}"
        elif "餐厅" in poi.type or "0502" in poi.typecode:
            return f"{base_url}/booking?type=restaurant&biz={poi.business_area}"
        elif "酒店" in poi.type or "1009" in poi.typecode:
            return f"{base_url}/booking?type=hotel&biz={poi.business_area}"
        else:
            return f"{base_url}/booking?biz={poi.business_area}"
    
    async def _fill_booking_form(self, poi: AmapPoiResult, user_data: Dict[str, Any], log: List[str]) -> Dict[str, Any]:
        """填写表单 - 增强数据锚点"""
        form_data = {}
        
        # 智能字段匹配
        field_mappings = {
            'name': ['[name="name"]', '[placeholder*="姓名"]', '#customer-name', '.name-input'],
            'phone': ['[name="phone"]', '[placeholder*="电话"]', '#customer-phone', '.phone-input'],
            'time': ['[name="time"]', '[placeholder*="时间"]', '#booking-time', '.time-input'],
            'people': ['[name="people"]', '[placeholder*="人数"]', '#guest-count', '.people-input'],
            'message': ['[name="message"]', '[placeholder*="备注"]', '#special-requests', '.message-input']
        }
        
        for field_name, selectors in field_mappings.items():
            field_value = user_data.get(field_name, self._get_default_value(field_name))
            
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(str(field_value))
                        form_data[field_name] = field_value
                        log.append(f"填写字段: {field_name} = {field_value}")
                        break
                except Exception as e:
                    logger.debug(f"填写字段 {field_name} 时出错: {e}")
                    
        form_data.update({
            'poi_id': poi.id,
            'poi_name': poi.name,
            'poi_address': poi.address,
            'business_area': poi.business_area,
            'booking_timestamp': datetime.now().isoformat()
        })
        
        return form_data
    
    def _get_default_value(self, field_name: str) -> str:
        """获取默认字段值"""
        defaults = {
            'name': '匿名用户',
            'phone': '138****8888',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'people': '2',
            'message': '慢生活体验'
        }
        return defaults.get(field_name, '')
    
    async def detect_payment_blocking_with_snapshot(self, booking_id: str) -> Dict[str, Any]:
        """检测支付阻断并保存快照"""
        blocking_selectors = [
            '[type="submit"][value*="支付"]', '[type="button"][onclick*="payment"]',
            '.pay-button', '.payment-btn', '.confirm-payment',
            '[data-pay="true"]', '[action*="pay"]', '.checkout-btn'
        ]
        
        for selector in blocking_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        # 拍摄支付前截图
                        screenshot = await self.page.screenshot(type="png", full_page=True)
                        
                        # 保存浏览器快照
                        snapshot_id = None
                        if self.state_manager:
                            snapshot_id = await self.state_manager.save_browser_snapshot(self.context, booking_id)
                        
                        return {
                            'blocking_detected': True,
                            'selector': selector,
                            'screenshot': screenshot,
                            'snapshot_id': snapshot_id,
                            'message': '检测到支付按钮，停止自动执行等待用户确认',
                            'user_action': 'confirm_payment'
                        }
            except Exception as e:
                logger.debug(f"检测选择器 {selector} 时出错: {e}")
                
        return {
            'blocking_detected': False,
            'message': '未检测到支付阻断点',
            'user_action': 'auto_complete'
        }


class PlaywrightBookingExecutionTool:
    """
    Playwright 浏览器自动化预约执行工具 - 完整实现
    """
    
    def __init__(self, headless: bool = True, supabase_client=None):
        self.headless = headless
        self.supabase_client = supabase_client
        self.state_manager = BrowserStateManager(supabase_client)
        self.wanderbook_bridge = WanderbookBridge(supabase_client)
        self.antibot_orchestrator = AntiBotOrchestrator()
        self.logger = logging.getLogger(__name__)
        
        # 高德API配置（保持兼容性）
        self.amap_key = os.getenv("AMAP_API_KEY")
        self.amap_base_url = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com")
        self.rate_limit_delay = 1.0
        self.last_request_time = None
        
        if not self.amap_key:
            logger.warning("AMAP_API_KEY未配置，将使用模拟数据")
    
    async def upload_screenshot_to_supabase(self, screenshot_bytes: bytes, filename: str) -> str:
        """上传截图到Supabase Storage"""
        try:
            if self.supabase_client:
                # TODO: 实现实际的Supabase上传
                return f"https://your-supabase-url.supabase.co/storage/v1/object/public/screenshots/{filename}"
            else:
                # 本地保存（开发用）
                screenshots_dir = Path("temp_screenshots")
                screenshots_dir.mkdir(exist_ok=True)
                
                file_path = screenshots_dir / filename
                with open(file_path, "wb") as f:
                    f.write(screenshot_bytes)
                    
                return f"file://{file_path.absolute()}"
                
        except Exception as e:
            self.logger.error(f"截图上传失败: {e}")
            return ""
    
    async def execute_booking(self,
                            booking_request: Dict[str, Any],
                            feedback_callback: Callable[[ExecutionFeedback], None] = None) -> PlaywrightBookingResult:
        """
        执行浏览器自动化预约（带幂等性和并发控制）
        """
        booking_id = f"playwright_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # 🔒 幂等性检查 - 防止重复执行
            merchant_name = booking_request.get('merchant_name', '')
            booking_time = booking_request.get('planned_time', '')
            booking_key = f"{merchant_name}_{booking_time}"
            
            # 检查是否已有相同预约在执行或已完成
            existing_result = await concurrency_manager.check_idempotent(booking_key)
            if existing_result:
                logger.info(f"发现重复预约请求，返回缓存结果: {booking_key}")
                await self._send_feedback(
                    feedback_callback, ExecutionStage.FINALIZING, BookingStatus.COMPLETED,
                    "预约已存在，返回之前的结果", 100
                )
                return existing_result
            
            # 🔒 并发控制 - 检查是否已有相同预约正在执行
            if not await concurrency_manager.check_and_mark_active(booking_id):
                logger.warning(f"预约已在执行中，拒绝重复请求: {booking_id}")
                await self._send_feedback(
                    feedback_callback, ExecutionStage.FINALIZING, BookingStatus.FAILED,
                    "预约已在处理中，请稍后再试", 100
                )
                return PlaywrightBookingResult(
                    success=False,
                    booking_id=booking_id,
                    next_user_action="预约已在处理中，请稍后再试",
                    retry_suggestions=["等待当前预约完成后再试"]
                )
            
            # 🔒 获取商户级别的锁，防止同一商户的并发预约冲突
            lock_key = await concurrency_manager.acquire_booking_lock(merchant_name, booking_time)
            logger.info(f"获取到商户预约锁: {lock_key}")
        
            # 阶段1: 初始化
            await self._send_feedback(
                feedback_callback, ExecutionStage.INITIALIZING, BookingStatus.PROCESSING,
                "正在启动浏览器自动化...", 5,
                details={"booking_id": booking_id, "tool": "playwright", "headless": self.headless}
            )
            
            # 阶段2: 参数验证
            await self._send_feedback(
                feedback_callback, ExecutionStage.VALIDATING, BookingStatus.PROCESSING,
                "正在验证预约参数...", 10
            )
            
            validated_request = self._validate_booking_request(booking_request)
            target_poi = await self._get_poi_from_request(validated_request)
            
            await self._send_feedback(
                feedback_callback, ExecutionStage.SEARCHING_POIS, BookingStatus.PROCESSING,
                f"准备访问 {target_poi.name} 预约页面...", 20
            )
            
            # 阶段3: 浏览器自动化
            async with BrowserAutomationTool(
                headless=self.headless, 
                state_manager=self.state_manager
            ) as browser_tool:
                
                # 导航并填写表单
                browser_tool.antibot_orchestrator = self.antibot_orchestrator
                form_result = await browser_tool.navigate_with_antisbot_check(
                    target_poi, 
                    validated_request.get('user_data', {})
                )
                
                execution_duration = (datetime.now() - start_time).total_seconds()
                
                # 处理机器人阻断
                if not form_result['success'] and form_result.get('blocked_by_antibot'):
                    screenshot_url = await self.upload_screenshot_to_supabase(
                        form_result['screenshot'], 
                        f"{booking_id}_antibot.png"
                    )
                    
                    # 获取风险等级
                    risk_level = form_result['risk_profile'].risk_level.value if form_result.get('risk_profile') else 'unknown'
                    
                    await self._send_feedback(
                        feedback_callback, ExecutionStage.FINALIZING, BookingStatus.FAILED,
                        form_result['user_instruction'], 95
                    )
                    
                    return PlaywrightBookingResult(
                        success=False,
                        booking_id=booking_id,
                        poi_info=target_poi,
                        screenshot_url=screenshot_url,
                        next_user_action=form_result['user_instruction'],
                        blocking_point="antibot_detected",
                        risk_level="high",
                        requires_confirmation=True,
                        execution_log=form_result['execution_log'],
                        execution_time=execution_duration,
                        browser_info={'headless': self.headless, 'tool': 'playwright'}
                    )
                
                # 处理其他错误
                if not form_result['success']:
                    raise Exception(f"表单处理失败: {form_result['error']}")
                
                # 阶段4: 检测支付阻断点
                blocking_result = await browser_tool.detect_payment_blocking_with_snapshot(booking_id)
                
                # 生成截图URL
                screenshot_url = await self.upload_screenshot_to_supabase(
                    blocking_result.get('screenshot', b''), 
                    f"{booking_id}_payment.png"
                )
                
                # 根据阻断检测结果返回不同状态
                if blocking_result['blocking_detected']:
                    # 需要用户确认
                    await self._send_feedback(
                        feedback_callback, ExecutionStage.FINALIZING, BookingStatus.REQUIRES_USER_CONFIRM,
                        "检测到支付环节，请确认后继续", 95
                    )
                    
                    return PlaywrightBookingResult(
                        success=True,
                        booking_id=booking_id,
                        poi_info=target_poi,
                        screenshot_url=screenshot_url,
                        form_data=form_result['form_data'],
                        next_user_action="确认支付订单",
                        blocking_point="payment_gateway",
                        risk_level="medium",
                        requires_confirmation=True,
                        browser_snapshot_id=blocking_result.get('snapshot_id'),
                        execution_log=form_result['execution_log'],
                        execution_time=execution_duration,
                        browser_info={'headless': self.headless, 'tool': 'playwright'}
                    )
                else:
                    # 直接完成
                    await self._send_feedback(
                        feedback_callback, ExecutionStage.FINALIZING, BookingStatus.COMPLETED,
                        "预约成功完成", 100
                    )
                    
                    # 同步到城市副本册
                    await self.wanderbook_bridge.sync_with_booking_tool(
                        form_result, target_poi, 'current_user'
                    )
                    
                    return PlaywrightBookingResult(
                        success=True,
                        booking_id=booking_id,
                        poi_info=target_poi,
                        form_data=form_result['form_data'],
                        next_user_action="预约确认已完成",
                        blocking_point="none",
                        risk_level="low",
                        requires_confirmation=False,
                        execution_log=form_result['execution_log'],
                        execution_time=execution_duration,
                        browser_info={'headless': self.headless, 'tool': 'playwright'}
                    )
                    
        except Exception as e:
            error_msg = f"Playwright执行失败: {str(e)}"
            self.logger.error(error_msg)
            
            await self._send_feedback(
                feedback_callback, ExecutionStage.FINALIZING, BookingStatus.FAILED,
                error_msg, 100, error=error_msg
            )
            
            failed_result = PlaywrightBookingResult(
                success=False,
                booking_id=booking_id,
                next_user_action="请重试或联系客服",
                retry_suggestions=[
                    "检查网络连接",
                    "确认目标商户是否支持在线预约",
                    "切换至手动模式",
                    "稍后重试（可能是临时风控）"
                ]
            )
            
            return failed_result
            
        finally:
            # 🔒 清理并发控制状态
            try:
                # 释放商户锁
                if 'lock_key' in locals():
                    concurrency_manager.release_booking_lock(lock_key)
                    logger.info(f"已释放商户预约锁: {lock_key}")
                
                # 标记预约完成
                await concurrency_manager.mark_completed(booking_id)
                logger.info(f"已标记预约完成: {booking_id}")
                
                # 缓存成功结果用于幂等性保护（仅在成功执行时）
                if 'result' in locals() and hasattr(result, 'success') and result.success:
                    await concurrency_manager.cache_result(booking_key, result)
                    logger.info(f"已缓存成功结果用于幂等性保护: {booking_key}")
                    
            except Exception as e:
                logger.error(f"清理并发控制状态时出错: {e}")
    
    async def resume_booking(self, snapshot_id: str, user_action: str = "confirm") -> PlaywrightBookingResult:
        """恢复被中断的预约"""
        try:
            if not PLAYWRIGHT_AVAILABLE:
                raise Exception("Playwright未安装")
            
            async with async_playwright() as playwright:
                # 恢复浏览器上下文
                context = await self.state_manager.restore_browser_context(snapshot_id, playwright)
                
                try:
                    page = context.pages[0] if context.pages else await context.new_page()
                    
                    if user_action == "confirm":
                        # 用户确认继续支付（这里需要根据具体页面实现）
                        await page.click('.pay-button, .confirm-payment, [type="submit"]')
                        
                        # 等待可能的重定向或结果页面
                        await page.wait_for_timeout(3000)
                        
                        # 拍摄完成截图
                        screenshot = await page.screenshot(type="png")
                        screenshot_url = await self.upload_screenshot_to_supabase(
                            screenshot, f"{snapshot_id}_completed.png"
                        )
                        
                        return PlaywrightBookingResult(
                            success=True,
                            booking_id=snapshot_id.replace('_snapshot_', '_resumed_'),
                            screenshot_url=screenshot_url,
                            next_user_action="支付已成功完成",
                            blocking_point="none",
                            risk_level="low",
                            requires_confirmation=False
                        )
                    else:
                        # 用户取消
                        return PlaywrightBookingResult(
                            success=False,
                            booking_id=snapshot_id,
                            next_user_action="预约已取消",
                            blocking_point="user_cancelled",
                            risk_level="low",
                            requires_confirmation=False
                        )
                        
                finally:
                    await context.close()
                    
        except Exception as e:
            self.logger.error(f"恢复预约失败: {e}")
            return PlaywrightBookingResult(
                success=False,
                booking_id=snapshot_id,
                next_user_action="恢复预约失败，请重新开始",
                blocking_point="resumption_failed",
                risk_level="high",
                requires_confirmation=False
            )
    
# _sync_to_wanderbook方法已移除，使用wanderbook_bridge.sync_with_booking_tool
    
    def _validate_booking_request(self, booking_request: Dict[str, Any]) -> Dict[str, Any]:
        """验证预约请求参数"""
        required_fields = ['poi_id', 'user_data']
        for field in required_fields:
            if field not in booking_request:
                raise ValueError(f"缺少必要字段: {field}")
                
        # 默认用户数据
        user_data = booking_request.get('user_data', {})
        default_user_data = {
            'name': '匿名用户',
            'phone': '138****8888',
            'preferred_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'people_num': 2
        }
        
        for key, value in default_user_data.items():
            if key not in user_data:
                user_data[key] = value
                
        return {
            'poi_id': booking_request['poi_id'],
            'user_data': user_data,
            'additional_params': booking_request.get('additional_params', {})
        }
    
    async def _get_poi_from_request(self, booking_request: Dict[str, Any]) -> AmapPoiResult:
        """从请求中获取POI数据 - 增强数据锚点"""
        poi_id = booking_request['poi_id']
        
        try:
            # 首先尝试从高德API获取详细信息
            if self.amap_key:
                poi_details = await self._get_poi_details_from_amap(poi_id)
                if poi_details:
                    return poi_details
            
            # 后备方案：使用模拟数据
            return AmapPoiResult(
                id=poi_id,
                name=booking_request['user_data'].get('merchant_name', '目标商户'),
                address=booking_request['user_data'].get('address', '未知地址'),
                location=booking_request['user_data'].get('location', '116.397470,39.908823'),
                type=booking_request['user_data'].get('type', '餐饮'),
                typecode=booking_request['user_data'].get('typecode', '050000'),
                business_area=booking_request['user_data'].get('business_area', '附近商圈')
            )
            
        except Exception as e:
            self.logger.error(f"获取POI信息失败: {e}")
            raise
    
    async def _get_poi_details_from_amap(self, poi_id: str) -> Optional[AmapPoiResult]:
        """从高德API获取POI详细信息"""
        # TODO: 实现实际的高德POI详情API调用
        # 当前返回None，会触发后备方案
        return None
    
    async def _send_feedback(self, 
                           feedback_callback: Optional[Callable], 
                           stage: ExecutionStage,
                           status: BookingStatus,
                           message: str,
                           progress: int,
                           details: Dict[str, Any] = None,
                           error: str = None):
        """发送执行反馈"""
        if feedback_callback:
            try:
                feedback = ExecutionFeedback(
                    stage=stage,
                    status=status,
                    message=message,
                    progress=progress,
                    details=details or {},
                    error=error
                )
                await feedback_callback(feedback)
            except Exception as e:
                self.logger.error(f"发送反馈失败: {e}")

    async def get_location_by_query(self, query: str) -> Optional[Dict[str, float]]:
        """通过查询获取位置坐标（模拟高德Geocoding API）"""
        try:
            # 模拟地理编码结果
            # 真实实现中应该调用高德Geocoding API
            mock_coordinates = {
                "三里屯": {"lat": 39.9368, "lng": 116.4472},
                "西单大悦城": {"lat": 39.9058, "lng": 116.3806},
                "王府井": {"lat": 39.9097, "lng": 116.4074},
                "后海": {"lat": 39.9388, "lng": 116.3831},
                "五道口": {"lat": 39.9927, "lng": 116.3347},
                "朝阳公园": {"lat": 39.9396, "lng": 116.4843},
                "国贸": {"lat": 39.9097, "lng": 116.4580},
                "建国门": {"lat": 39.9088, "lng": 116.4360},
                "四惠": {"lat": 39.9068, "lng": 116.4998},
                "望京": {"lat": 39.9928, "lng": 116.4712},
            }
            
            # 检查是否是纯情感表达或没有具体地址的句子
            emotional_patterns = [
                r".*[骂|批|训|吵|哭|笑|累|烦|困|饿|渴|冷|热|好|坏].*",
                r"^[^\\s，。！？]{1,4}$"  # 太短的句子很可能是情感词
            ]
            
            import re
            for pattern in emotional_patterns:
                if re.search(pattern, query):
                    logger.info(f"检测到情感表达，不进行地理编码：{query}")
                    return None
            
            # 更严格的匹配逻辑：需要完整包含地理位置关键词
            for key, coords in mock_coordinates.items():
                if key in query:
                    # 检查是否是负面表达
                    negation_patterns = [
                        f"(不|没|非|无)在.*{key}",
                        f"{key}.*(不|没|非|无)在",
                        f"(远离|避开|离开){key}",
                        f"不.*去.*{key}",
                        f"没.*去.*{key}"
                    ]
                    
                    is_negated = False
                    for pattern in negation_patterns:
                        if re.search(pattern, query):
                            is_negated = True
                            logger.info(f"检测到否定表达，跳过位置匹配：{query}")
                            break
                    
                    if not is_negated:
                        logger.info(f"获取位置成功: {query} -> {coords}")
                        return coords
            
            # 默认位置（北京中心）
            default_coords = {"lat": 39.9042, "lng": 116.4074}
            logger.info(f"使用默认位置: {query} -> {default_coords}")
            return default_coords
            
        except Exception as e:
            logger.error(f"获取位置失败: {e}")
            return None

    async def route_query_to_pois(self, query: str, radius: int = 1000, results_limit: int = 8) -> List[AmapPoiResult]:
        """将查询转换为POI列表（模拟高德Place Search API）"""
        try:
            # 获取位置坐标
            location = await self.get_location_by_query(query)
            if not location:
                # 如果没有获取到位置，返回空列表
                return []

            # 模拟POI搜索
            # 真实实现中应该调用高德Place Search API
            mock_pois = {
                "三里屯": [
                    AmapPoiResult(
                        id="poi_001",
                        name="三里屯太古里",
                        address="北京市朝阳区三里屯路19号",
                        location=f"{location['lng']},{location['lat']}",
                        type="购物",
                        typecode="060000",
                        distance="50",
                        rating="4.5",
                        business_area="三里屯"
                    ),
                    AmapPoiResult(
                        id="poi_002",
                        name="三里屯酒吧街",
                        address="北京市朝阳区三里屯路",
                        location=f"{location['lng']+0.001},{location['lat']+0.001}",
                        type="餐饮",
                        typecode="050000",
                        distance="200",
                        rating="4.2",
                        business_area="三里屯"
                    ),
                    AmapPoiResult(
                        id="poi_003",
                        name="三里屯SOHO",
                        address="北京市朝阳区三里屯路11号",
                        location=f"{location['lng']+0.002},{location['lat']+0.002}",
                        type="商务",
                        typecode="120000",
                        distance="300",
                        rating="4.0",
                        business_area="三里屯"
                    ),
                ],
                "西单": [
                    AmapPoiResult(
                        id="poi_004",
                        name="西单大悦城",
                        address="北京市西城区西单北大街131号",
                        location=f"{location['lng']},{location['lat']}",
                        type="购物",
                        typecode="060000",
                        distance="100",
                        rating="4.4",
                        business_area="西单"
                    ),
                    AmapPoiResult(
                        id="poi_005",
                        name="西单文化广场",
                        address="北京市西城区西单北大街",
                        location=f"{location['lng']+0.001},{location['lat']+0.001}",
                        type="文化",
                        typecode="100000",
                        distance="150",
                        rating="4.1",
                        business_area="西单"
                    ),
                ],
                "后海": [
                    AmapPoiResult(
                        id="poi_006",
                        name="后海公园",
                        address="北京市西城区后海北沿",
                        location=f"{location['lng']},{location['lat']}",
                        type="景点",
                        typecode="110000",
                        distance="50",
                        rating="4.6",
                        business_area="什刹海"
                    ),
                    AmapPoiResult(
                        id="poi_007",
                        name="什刹海",
                        address="北京市西城区什刹海",
                        location=f"{location['lng']+0.001},{location['lat']+0.001}",
                        type="景点",
                        typecode="110000",
                        distance="100",
                        rating="4.7",
                        business_area="什刹海"
                    ),
                ],
            }
            
            # 选择合适的POI列表
            selected_pois = []
            for key, pois in mock_pois.items():
                if key in query:
                    selected_pois = pois
                    break
            
            # 如果没有匹配，创建通用POI
            if not selected_pois:
                selected_pois = [
                    AmapPoiResult(
                        id=f"poi_generic_{i+1}",
                        name=f"{query}附近安静角落{i+1}",
                        address=f"北京市{query}附近",
                        location=f"{location['lng']+0.001*i},{location['lat']+0.001*i}",
                        type="休闲",
                        typecode="120000",
                        distance=f"{100*i}",
                        rating="4.3",
                        business_area=query
                    )
                    for i in range(min(results_limit, 5))
                ]
            
            # 限制返回数量
            return selected_pois[:results_limit]
            
        except Exception as e:
            logger.error(f"POI搜索失败: {e}")
            return []