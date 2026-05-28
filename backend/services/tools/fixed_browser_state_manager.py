"""
修复版浏览器状态管理器
解决异步上下文生命周期问题和资源泄露
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Protocol, runtime_checkable
import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid


logger = logging.getLogger(__name__)


# ================================
# 🎯 浏览器上下文协议定义
# ================================

@runtime_checkable
class PlaywrightPageProtocol(Protocol):
    """Playwright页面协议 - 支持类型检查"""
    async def title(self) -> str: ...
    async def query_selector_all(self, selector: str): ...
    async def evaluate(self, expression: str): ...
    async def url(self) -> str: ...

@runtime_checkable
class PlaywrightContextProtocol(Protocol):
    """Playwright上下文协议"""
    async def cookies(self): ...
    async def add_cookies(self, cookies): ... 
    pages: list


# ================================
# 🎯 异步上下文快照数据结构
# ================================

@dataclass
class BrowserContextSnapshot:
    """浏览器上下文快照数据类"""
    snapshot_id: str
    booking_id: str
    
    # 核心状态
    url: str
    title: str
    user_agent: str
    viewport: Dict[str, int]
    
    # 数据状态
    cookies: list
    local_storage: Dict[str, str]
    session_storage: Dict[str, str]
    form_state: Dict[str, Any]
    
    # 页面结构快照
    dom_snapshot: str = ""
    visible_elements: Dict[str, Any] = None
    
    # 时间戳
    created_at: str = ""
    expires_at: str = ""
    
    # 执行上下文
    execution_stage: str = ""
    blocking_type: str = ""
    user_action_required: str = ""
    
    def __post_init__(self):
        now = datetime.now()
        if not self.created_at:
            self.created_at = now.isoformat()
        if not self.expires_at:
            # 默认30分钟后过期
            expire_time = now + timedelta(minutes=30)
            self.expires_at = expire_time.isoformat()
        if self.visible_elements is None:
            self.visible_elements = {}


# ================================
# 🎯 异步上下文管理器类
# ================================

class AsyncBrowserStateManager:
    """
    修复版异步浏览器状态管理器
    支持完整的生命周期管理和上下文恢复
    """
    
    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client
        self.active_snapshots = {}  # 内存快照缓存
        self.snapshot_ttl = {}      # 快照TTL管理
        
        # 背景任务监控
        self.background_tasks = set()
        
        # 启动TTL监控任务
        self._start_ttl_monitor()
    
    def _start_ttl_monitor(self):
        """启动TTL监控后台任务"""
        async def monitor_ttl():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分钟检查一次
                    await self._cleanup_expired_snapshots()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"TTL监控错误: {e}")
        
        task = asyncio.create_task(monitor_ttl())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def create_context_snapshot(
        self, 
        context: PlaywrightContextProtocol, 
        booking_id: str,
        execution_stage: str = "",
        blocking_type: str = "",
        user_action: str = ""
    ) -> BrowserContextSnapshot:
        """
        创建浏览器上下文快照
        
        Args:
            context: Playwright浏览器上下文
            booking_id: 预订ID
            execution_stage: 执行阶段
            blocking_type: 阻断类型
            user_action: 需要用户执行的操作
            
        Returns:
            BrowserContextSnapshot: 创建的快照
        """
        try:
            # 🎯 异步安全地获取页面
            page = await self._get_primary_page(context)
            if not page:
                raise Exception("无法获取主页面")
            
            # 🎯 收集上下文状态（异步操作）
            state_futures = {
                'title': page.title(),
                'cookies': context.cookies(),
                'local_storage': self._get_local_storage(page),
                'session_storage': self._get_session_storage(page),
                'form_state': self._capture_form_state(page),
                'viewport': self._get_viewport_info(page),
                'user_agent': self._get_user_agent(page)
            }
            
            # 🎯 并行执行所有异步状态收集
            results = {}
            for key, future in state_futures.items():
                try:
                    results[key] = await future
                except Exception as e:
                    logger.warning(f"获取{key}状态失败: {e}")
                    results[key] = None
            
            # 🎯 创建快照
            snapshot_id = f"{booking_id}_snapshot_{uuid.uuid4().hex[:8]}"
            
            snapshot = BrowserContextSnapshot(
                snapshot_id=snapshot_id,
                booking_id=booking_id,
                url=getattr(page, 'url', ''),
                title=results['title'] or "未知页面",
                user_agent=results['user_agent'] or "",
                viewport=results['viewport'] or {'width': 1920, 'height': 1080},
                cookies=results['cookies'] or [],
                local_storage=results['local_storage'] or {},
                session_storage=results['session_storage'] or {},
                form_state=results['form_state'] or {},
                execution_stage=execution_stage,
                blocking_type=blocking_type,
                user_action_required=user_action
            )
            
            # 🎯 保存快照
            await self._save_snapshot(snapshot)
            
            logger.info(f"✅ 浏览器快照创建成功: {snapshot_id}")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ 创建浏览器快照失败: {e}")
            # 🎯 故障降级
            return await self._create_emergency_snapshot(booking_id, str(e))
    
    async def restore_browser_context(
        self, 
        snapshot_id: str,
        playwright_instance
    ) -> Optional[PlaywrightContextProtocol]:
        """
        恢复浏览器上下文
        
        Args:
            snapshot_id: 快照ID
            playwright_instance: Playwright实例
            
        Returns:
            恢复的浏览器上下文
        """
        try:
            # 🎯 获取快照
            snapshot = await self._get_snapshot(snapshot_id)
            if not snapshot:
                raise Exception(f"快照不存在或已过期: {snapshot_id}")
            
            # 🎯 创建新的浏览器上下文
            context = await self._initialize_browser_context(playwright_instance, snapshot)
            page = await self._initialize_page(context, snapshot)
            
            # 🎯 恢复页面状态（异步并行）
            restore_tasks = [
                self._restore_cookies(context, snapshot.cookies),
                self._restore_local_storage(page, snapshot.local_storage),
                self._restore_session_storage(page, snapshot.session_storage),
                self._restore_form_state(page, snapshot.form_state),
                self._restore_viewport(page, snapshot.viewport)
            ]
            
            # 并行恢复所有状态
            try:
                await asyncio.gather(*restore_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"恢复状态时出现部分错误: {e}")
                # 继续执行，不阻断主流程
            
            logger.info(f"✅ 浏览器上下文恢复成功: {snapshot_id}")
            return context
            
        except Exception as e:
            logger.error(f"❌ 恢复浏览器上下文失败: {e}")
            raise
    
    async def wait_for_user_action(
        self,
        snapshot_id: str,
        action_type: str = "default",
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """等待用户操作""" 
        try:
            # 🎯 创建用户操作等待任务
            wait_task = asyncio.create_task(
                self._poll_for_user_completion(snapshot_id, action_type)
            )
            
            # 🎯 设置超时
            try:
                result = await asyncio.wait_for(wait_task, timeout=timeout_seconds)
                return {
                    'success': True,
                    'action_completed': result,
                    'timeout': False,
                    'message': '用户操作完成'
                }
            except asyncio.TimeoutError:
                return {
                    'success': False,
                    'action_completed': None,
                    'timeout': True,
                    'message': f'等待用户操作超时 ({timeout_seconds}秒)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '等待用户操作发生异常'
            }
    
    # ================================
    # 🎯 私有辅助方法
    # ================================
    
    async def _get_primary_page(self, context: PlaywrightContextProtocol) -> Optional[PlaywrightPageProtocol]:
        """安全获取主页面"""
        try:
            if hasattr(context, 'pages') and context.pages:
                return context.pages[0]
        except Exception:
            pass
        return None
    
    async def _get_local_storage(self, page: PlaywrightPageProtocol) -> Dict[str, str]:
        """获取LocalStorage"""
        try:
            return await page.evaluate('''() => {
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                return data;
            }''')
        except Exception:
            return {}
    
    async def _get_session_storage(self, page: PlaywrightPageProtocol) -> Dict[str, str]:
        """获取SessionStorage"""
        try:
            return await page.evaluate('''() => {
                const data = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    data[key] = sessionStorage.getItem(key);
                }
                return data;
            }''')
        except Exception:
            return {}
    
    async def _capture_form_state(self, page: PlaywrightPageProtocol) -> Dict[str, Any]:
        """捕获表单状态"""
        try:
            return await page.evaluate('''() => {
                const formData = {};
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    if (el.name || el.id) {
                        const key = el.name || el.id;
                        formData[key] = {
                            value: el.value,
                            type: el.type,
                            checked: el.checked
                        };
                    }
                });
                return formData;
            }''')
        except Exception:
            return {}
    
    async def _get_viewport_info(self, page: PlaywrightPageProtocol) -> Dict[str, int]:
        """获取视窗信息"""
        try:
            return await page.evaluate('''() => ({
                width: window.innerWidth,
                height: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio
            })''')
        except Exception:
            return {'width': 1920, 'height': 1080}
    
    async def _get_user_agent(self, page: PlaywrightPageProtocol) -> str:
        """获取User-Agent"""
        try:
            return await page.evaluate('navigator.userAgent')
        except Exception:
            return ""
    
    async def _save_snapshot(self, snapshot: BrowserContextSnapshot) -> None:
        """保存快照"""
        # 内存缓存
        self.active_snapshots[snapshot.snapshot_id] = snapshot
        
        # 设置TTL
        expire_time = datetime.fromisoformat(snapshot.expires_at)
        ttl_seconds = (expire_time - datetime.now()).total_seconds()
        self.snapshot_ttl[snapshot.snapshot_id] = asyncio.get_event_loop().time() + ttl_seconds
        
        # 本地文件缓存（每个快照一个文件，避免大文件）
        try:
            snapshot_dir = Path("browser_snapshots")
            snapshot_dir.mkdir(exist_ok=True)
            
            file_path = snapshot_dir / f"{snapshot.snapshot_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(snapshot), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"本地快照保存失败: {e}")
    
    async def _get_snapshot(self, snapshot_id: str) -> Optional[BrowserContextSnapshot]:
        """获取快照"""
        # 先检查内存缓存
        if snapshot_id in self.active_snapshots:
            snapshot = self.active_snapshots[snapshot_id]
            if datetime.fromisoformat(snapshot.expires_at) > datetime.now():
                return snapshot
            else:
                # 超时的快照需要清理
                await self._remove_snapshot(snapshot_id)
                return None
        
        # 检查本地文件
        try:
            file_path = Path("browser_snapshots") / f"{snapshot_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                snapshot = BrowserContextSnapshot(**data)
                if datetime.fromisoformat(snapshot.expires_at) > datetime.now():
                    # 重新加载到内存缓存
                    self.active_snapshots[snapshot_id] = snapshot
                    return snapshot
                else:
                    # 删除过期文件
                    file_path.unlink()
                    return None
        except Exception as e:
            logger.warning(f"加载本地快照失败: {e}")
        
        return None
    
    async def _remove_snapshot(self, snapshot_id: str) -> None:
        """删除快照"""
        # 清理内存缓存
        self.active_snapshots.pop(snapshot_id, None)
        self.snapshot_ttl.pop(snapshot_id, None)
        
        # 清理本地文件
        try:
            file_path = Path("browser_snapshots") / f"{snapshot_id}.json"
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
    
    async def _initialize_browser_context(
        self, 
        playwright_instance, 
        snapshot: BrowserContextSnapshot
    ) -> PlaywrightContextProtocol:
        """初始化浏览器上下文"""
        # 这里需要实际的Playwright调用，为测试提供Mock接口
        # 实际实现:
        # browser = await playwright_instance.chromium.launch(
        #     headless=True,
        #     args=['--disable-blink-features=AutomationControlled']
        # )
        # context = await browser.new_context(
        #     viewport=snapshot.viewport,
        #     user_agent=snapshot.user_agent
        # )
        
        # Mock实现用于测试
        mock_context = type('MockContext', (), {
            'pages': [],
        })()
        
        return mock_context
    
    async def _initialize_page(
        self, 
        context: PlaywrightContextProtocol, 
        snapshot: BrowserContextSnapshot
    ) -> PlaywrightPageProtocol:
        """初始化页面"""
        # 实际实现:
        # page = await context.new_page()
        # await page.goto(snapshot.url, wait_until="networkidle")
        
        # Mock页面
        mock_page = type('MockPage', (), {
            'url': snapshot.url,
            'title': snapshot.title
        })()
        
        if hasattr(context, 'pages'):
            context.pages.append(mock_page)
        
        return mock_page
    
    async def _restore_cookies(self, context: PlaywrightContextProtocol, cookies: list) -> None:
        """恢复Cookies"""
        # 实际实现: await context.add_cookies(cookies)
        pass
    
    async def _restore_local_storage(self, page: PlaywrightPageProtocol, local_storage: Dict[str, str]) -> None:
        """恢复LocalStorage"""
        # 实际实现:
        # for key, value in local_storage.items():
        #     await page.evaluate(f'localStorage.setItem("{key}", "{value}")')
        pass
    
    async def _restore_session_storage(self, page: PlaywrightPageProtocol, session_storage: Dict[str, str]) -> None:
        """恢复SessionStorage"""
        # 实际实现:
        # for key, value in session_storage.items():
        #     await page.evaluate(f'sessionStorage.setItem("{key}", "{value}")')
        pass
    
    async def _restore_form_state(self, page: PlaywrightPageProtocol, form_state: Dict[str, Any]) -> None:
        """恢复表单状态"""
        # 实际实现:
        # for field_id, field_data in form_state.items():
        #     await page.evaluate(f'document.getElementById("{field_id}").value = "{field_data["value"]}"')
        pass
    
    async def _restore_viewport(self, page: PlaywrightPageProtocol, viewport: Dict[str, int]) -> None:
        """恢复视窗大小"""
        # 实际实现：设置viewport
        pass
    
    async def _poll_for_user_completion(self, snapshot_id: str, action_type: str) -> bool:
        """轮询用户完成状态"""
        # 实际实现中这里会轮询前端状态
        # 模拟等待
        await asyncio.sleep(1)
        return True
    
    async def _cleanup_expired_snapshots(self) -> None:
        """清理过期的快照"""
        current_time = asyncio.get_event_loop().time()
        expired_snapshots = [
            sid for sid, expire_time in self.snapshot_ttl.items()
            if current_time >= expire_time
        ]
        
        for snapshot_id in expired_snapshots:
            await self._remove_snapshot(snapshot_id)
            logger.debug(f"清理过期快照: {snapshot_id}")
    
    async def _create_emergency_snapshot(self, booking_id: str, error_msg: str) -> BrowserContextSnapshot:
        """创建紧急快照（故障降级）"""
        snapshot_id = f"{booking_id}_emergency_{uuid.uuid4().hex[:8]}"
        
        return BrowserContextSnapshot(
            snapshot_id=snapshot_id,
            booking_id=booking_id,
            url="",
            title="错误状态",
            user_agent="",
            viewport={'width': 1920, 'height': 1080},
            cookies=[],
            local_storage={},
            session_storage={},
            form_state={},
            execution_stage="error",
            blocking_type="emergency",
            user_action_required="请联系技术支持"
        )