"""
商家数据库模块 - 提供完整的合成商家数据
包含餐饮、休闲、文化等各种类型商家信息
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import random
from datetime import datetime, timedelta


class MerchantType(Enum):
    """商家类型枚举"""
    COFFEE_SHOP = "咖啡店"
    RESTAURANT = "餐厅"
    PARK = "公园"
    BOOKSTORE = "书店"
    ART_GALLERY = "艺术画廊"
    MUSEUM = "博物馆"
    LIBRARY = "图书馆"
    CINEMA = "电影院"
    SHOPPING_MALL = "购物中心"
    FITNESS_CENTER = "健身中心"
    SPA = "SPA中心"
    BAKERY = "面包店"
    TEA_HOUSE = "茶馆"
    WINE_BAR = "酒吧"


@dataclass
class MenuItem:
    """菜单项数据类"""
    name: str
    description: str
    price: float
    tags: List[str]
    calories: Optional[int] = None
    image: Optional[str] = None


@dataclass
class PackageDeal:
    """套餐数据类"""
    name: str
    items: List[MenuItem]
    original_price: float
    discounted_price: float
    description: str
    tags: List[str] = None


@dataclass
class OperatingHours:
    """营业时间数据类"""
    monday: str = "09:00-21:00"
    tuesday: str = "09:00-21:00"
    wednesday: str = "09:00-21:00"
    thursday: str = "09:00-21:00"
    friday: str = "09:00-22:00"
    saturday: str = "08:00-22:00"
    sunday: str = "08:00-21:00"


@dataclass
class Location:
    """位置信息数据类"""
    address: str
    latitude: float
    longitude: float
    area: str
    district: str
    nearby_landmarks: List[str] = None


@dataclass
class Merchant:
    """完整商家信息数据类"""
    id: str
    name: str
    type: MerchantType
    location: Location
    rating: float  # 1-5分
    price_level: int  # 1-4, $到$$$$
    description: str
    features: List[str]  # 特色标签
    menu: List[MenuItem]  # 菜单
    packages: List[PackageDeal]  # 套餐
    operating_hours: OperatingHours
    contact: str  # 电话
    website: Optional[str] = None
    image_gallery: List[str] = None
    solo_friendly: bool = True  # 是否一个人友好
    wifi_available: bool = True
    power_outlets: bool = True
    parking_available: bool = False


# === 咖啡店数据 ===
COFFEE_SHOPS = [
    Merchant(
        id="coffee-001",
        name="静谧时光咖啡",
        type=MerchantType.COFFEE_SHOP,
        location=Location(
            address="朝阳区三里屯南路88号",
            latitude=39.9375,
            longitude=116.4460,
            area="三里屯",
            district="朝阳区",
            nearby_landmarks=["三里屯太古里", "酒吧街"]
        ),
        rating=4.6,
        price_level=2,
        description="一家温馨的独立咖啡店，专门为独自前来的客人营造安静舒适的环境。店内装修简约而温暖，每一处细节都考虑到一个人的体验。",
        features=["安静环境", "插座充足", "WiFi快速", "书籍角", "轻音乐"],
        menu=[
            MenuItem("手冲单品咖啡", "埃塞俄比亚耶加雪菲，花香浓郁", 38, ["单品", "手工", "精品"], 5),
            MenuItem("美式咖啡", "香醇美式，适合独处思考", 25, ["经典", "清爽"]),
            MenuItem("拿铁咖啡", "奶香浓郁的意式拿铁", 32, ["奶咖", "香滑"]),
            MenuItem("抹茶拿铁", "日本进口抹茶，香甜可口", 35, ["无咖啡因", "抹茶"]),
            MenuItem("手工蛋糕", "每日新鲜制作的手工蛋糕", 28, ["甜品", "手工"]),
            MenuItem("三明治", "新鲜蔬菜三明治", 22, ["轻食", "健康"])
        ],
        packages=[
            PackageDeal(
                name="独享下午茶套餐",
                items=[
                    MenuItem("手冲咖啡", "单品手冲", 38, ["单品"]),
                    MenuItem("手工蛋糕", "新鲜蛋糕", 28, ["甜品"])],
                original_price=66,
                discounted_price=50,
                description="适合独自品味的下午茶时光",
                tags=["优惠", "下午茶", "独处友好"]
            )
        ],
        operating_hours=OperatingHours(
            monday="07:30-21:00",
            saturday="08:00-22:00",
            sunday="08:00-21:00"
        ),
        contact="010-8591-2345",
        website="www.tranquiltime.coffee",
        image_gallery=["/images/coffee1.jpg", "/images/coffee2.jpg"],
        solo_friendly=True
    ),
    Merchant(
        id="coffee-002",
        name="怡然书咖",
        type=MerchantType.COFFEE_SHOP,
        location=Location(
            address="海淀区五道口华清嘉园12号楼底商",
            latitude=39.9880,
            longitude=116.3380,
            area="五道口",
            district="海淀区",
            nearby_landmarks=["清华大学", "五道口购物中心"]
        ),
        rating=4.4,
        price_level=2,
        description="书店咖啡厅结合的概念店，提供安静阅读空间。书架上有各类书籍可供翻阅，氛围非常适合一个人静心阅读或工作。",
        features=["书店环境", "安静阅读角", "WiFi", "插座", "静音区"],
        menu=[
            MenuItem("卡布奇诺", "意式经典卡布奇诺", 30, ["经典", "奶咖"]),
            MenuItem("手冲耶加雪菲", "花香型单品咖啡", 42, ["单品", "花香"]),
            MenuItem("伯爵茶", "英式伯爵花果茶", 25, ["茶饮", "英式"]),
            MenuItem("芝士蛋糕", "纽约风味芝士蛋糕", 32, ["甜品", "芝士"])
        ],
        packages=[
            PackageDeal(
                name="读书时光套餐",
                items=[
                    MenuItem("卡布奇诺", "经典卡布", 30, ["经典"])],
                original_price=35,
                discounted_price=30,
                description="一杯咖啡的读书时光",
                tags=["读书", "安静", "优惠"]
            )
        ],
        operating_hours=OperatingHours(
            monday="08:00-22:00",
            friday="08:00-23:00",
            saturday="08:00-23:00"
        ),
        contact="010-6234-5678",
        solo_friendly=True
    )
]

# === 餐厅数据 ===
RESTAURANTS = [
    Merchant(
        id="restaurant-001",
        name="慢食小馆",
        type=MerchantType.RESTAURANT,
        location=Location(
            address="东城区南锣鼓巷123号",
            latitude=39.9368,
            longitude=116.4010,
            area="南锣鼓巷",
            district="东城区",
            nearby_landmarks=["南锣鼓巷胡同", "什刹海"]
        ),
        rating=4.5,
        price_level=3,
        description="胡同里的小众餐厅，主打慢生活理念。环境安静，适合一个人慢慢品味美食，感受慢节奏的生活。",
        features=["胡同环境", "慢食理念", "安静", "文艺", "小桌设计"],
        menu=[
            MenuItem("慢炖牛肉面", "24小时慢炖的红烧牛肉面", 45, ["招牌", "慢食", "温暖"]),
            MenuItem("蒸蛋羹", "嫩滑的蒸蛋羹配上时令蔬菜", 28, ["清淡", "营养"]),
            MenuItem("手工饺子", "现包现煮的手工饺子", 35, ["手工", "家常"]),
            MenuItem("时令蔬菜", "当季新鲜蔬菜拼盘", 22, ["健康", "时令"]),
            MenuItem("红豆汤", "慢火熬制的传统红豆汤", 18, ["甜品", "传统"])
        ],
        packages=[
            PackageDeal(
                name="慢食套餐",
                items=[
                    MenuItem("慢炖牛肉面", "招牌牛肉面", 45, ["招牌"]),
                    MenuItem("时令蔬菜", "营养蔬菜", 22, ["健康"]),
                    MenuItem("红豆汤", "甜品", 18, ["甜品"])],
                original_price=85,
                discounted_price=70,
                description="体验慢食文化的完整套餐",
                tags=["慢食", "套餐", "优惠"]
            )
        ],
        operating_hours=OperatingHours(
            monday="11:00-21:00",
            saturday="10:00-22:00"
        ),
        contact="010-6402-8899",
        solo_friendly=True
    )
]

# === 公园数据 ===
PARK_LANDSCAPES = [
    Merchant(
        id="park-001",
        name="朝阳公园",
        type=MerchantType.PARK,
        location=Location(
            address="朝阳区朝阳公园南路1号",
            latitude=39.9330,
            longitude=116.4770,
            area="朝阳公园",
            district="朝阳区",
            nearby_landmarks=["蓝色港湾", "朝阳医院"]
        ),
        rating=4.7,
        price_level=1,  # 免费公园
        description="城市中心的绿肺，是独自散步、思考、放松的理想场所。园内设施齐全，景色宜人，非常适合一个人慢慢游走。",
        features=["大面积绿地", "湖景", "步道", "运动设施", "安静区域"],
        menu=[],  # 公园无菜单
        packages=[],
        operating_hours=OperatingHours(
            monday="06:00-22:00",
            tuesday="06:00-22:00",
            wednesday="06:00-22:00",
            thursday="06:00-22:00",
            friday="06:00-22:00",
            saturday="05:30-22:30",
            sunday="05:30-22:30"
        ),
        contact="010-6501-8800",
        solo_friendly=True,
        parking_available=True
    )
]

# === 书店数据 ===
BOOKSTORES = [
    Merchant(
        id="bookstore-001",
        name="单向空间",
        type=MerchantType.BOOKSTORE,
        location=Location(
            address="朝阳区花家地南街8号",
            latitude=39.9820,
            longitude=116.4640,
            area="花家地",
            district="朝阳区",
            nearby_landmarks=["中央美术学院", "望京SOHO"]
        ),
        rating=4.6,
        price_level=2,
        description="知名独立书店，定期举办文化活动。为读者提供安静的阅读环境和丰富的文化活动，是文艺青年的聚集地。",
        features=["独立书店", "文化活动", "安静阅读", "咖啡区", "展览"],
        menu=[],
        packages=[],
        operating_hours=OperatingHours(
            monday="10:00-22:00",
            saturday="10:00-23:00",
            sunday="10:00-22:00"
        ),
        contact="010-8457-7645",
        website="www.one-way.cn",
        solo_friendly=True
    )
]

# === 整合所有商家 ===
ALL_MERCHANTS = COFFEE_SHOPS + RESTAURANTS + PARK_LANDSCAPES + BOOKSTORES

# === 商家分类映射 ===
MERCHANTS_BY_TYPE = {
    MerchantType.COFFEE_SHOP: COFFEE_SHOPS,
    MerchantType.RESTAURANT: RESTAURANTS,
    MerchantType.PARK: PARK_LANDSCAPES,
    MerchantType.BOOKSTORE: BOOKSTORES
}


def get_random_merchant(merchant_type: Optional[MerchantType] = None) -> Merchant:
    """获取随机商家"""
    if merchant_type and merchant_type in MERCHANTS_BY_TYPE:
        merchants = MERCHANTS_BY_TYPE[merchant_type]
    else:
        merchants = ALL_MERCHANTS
    
    return random.choice(merchants)


def get_merchants_by_area(area: str) -> List[Merchant]:
    """根据地区获取商家"""
    return [merchant for merchant in ALL_MERCHANTS if merchant.location.area == area]


def get_merchants_by_type(merchant_type: MerchantType) -> List[Merchant]:
    """根据类型获取商家"""
    return MERCHANTS_BY_TYPE.get(merchant_type, [])


def search_merchants_by_features(features: List[str]) -> List[Merchant]:
    """根据特色搜索商家"""
    result = []
    for merchant in ALL_MERCHANTS:
        if any(feature in merchant.features for feature in features):
            result.append(merchant)
    return result