import { WanderPlan, PKParticipant, CommunityLine, MapInstancePin, RecommendedPlace } from "./types";

// Official hotlinked assets from the HTML screenshots
export const ASSETS = {
  userProfile: "https://lh3.googleusercontent.com/aida-public/AB6AXuAmDTf3nqLDyYNJ3I5tDJ7fS00VVoXmS2gNZqe482p0BxS_XihGpQbSxau4xYZDL2C8MPLRh_ATdW1HHBrMC2E5NKz6U-9wNRTqqBld6U7n5zzlmJNt8yz29bqMWtQCo1Ui7HD_kAq16fT2omJmx6TlzYQ7EGcLkNDV081qkaNQuwqP18evcbF-m56xQ-MJ_1FCUPi3f0T1995tcPFSPZ-km7n3u0yAtvxeEjvlsiLZ_BeiBh5kVQenRWE90oaC7Yua0e4LkDcFHeI",
  
  // Plan A - Riverside Coffee Window View (used on Screen 4 A, Screen 3)
  riversideCoffeeA: "https://lh3.googleusercontent.com/aida-public/AB6AXuC9o8wP1-ZoG3TYWgppJNt0-oOH3QaPliWFM07VwCiQB-_Jb-ZomwKyElzo3AtwpiInCB7dj5_Vq_ZeBUUZen6Fzmrg35bhT10Rtjtqamppqt3ROM__-vngV8gT0_hIYzZ_tRVaSLLiXAjyVZcEghx6pOjXKKs6A9tlCHuXCH8I0NAaqRjzZo1QVuH1CKzlm6-B1drUzlLj2GX8ABDQEDG0Dm6B24BJp3kgaw-dS7gdPlvL4LfOjbvko6fqTOrr4ngBe0qb8BGdQk4",
  
  // Alternative Cozy Riverside Brew Counter Interior (Screen 3 Main, Screen 7 recommendation 1)
  riversideCoffeeB: "https://lh3.googleusercontent.com/aida-public/AB6AXuBstCNbOhuetHsyvMGF83RqMIz4uKxRO5EZaCLn1itRf0_5KzQxQG0b7fGdxhg4wwZOXFqWWE2lyF4g-759w9aN-MA3Bg0GyMY4xtnMFMl_rU7-vUqyI4g9Ydpa9lUDl3BgRsJkold24lMP3RnB0iyjm3cyrpYhM-925vpzo8hl-tur61cdlLc1p3xQ0DLpJCrGsmqbrIqE5Vx_fTuH7hUODeDH6sCi43nEYKMOfQg1VOOocV518_5L5jbwQ3t2SKYIuD3oF00MGoA",
  
  // Vinyl store exploration (Screen 4 B)
  vinylStore: "https://lh3.googleusercontent.com/aida-public/AB6AXuCPzvH36XoPggKiAHJSysE9HGhwrHyH3gHSDxJvRHzfxIyP84Te6HlJZ3wJg2fSz0NZiBUaxHIj1Gv4wMFYxPYN9R_PvimxyM_G1tnFCIqbf4t6mNR1NOS2bcZsKwBuhtLzNAnle8LM_Hy6me8tbOBDTEhjEjHP17uq8iidulMSC4xie3qvmZTsK_IeNSTufi8psu63nIIPOT6ROXH_4NcSbQF4m2kJSpN_vAoP4DBBDT-OVclGXoa_PZw1n1yDQzm8-UZiYQGKJGA",
  
  // Park Sunset Bench (Screen 4 C)
  parkSunset: "https://lh3.googleusercontent.com/aida-public/AB6AXuDwYJ6TsAKKOwHK11igZepJoEEzLDYk3qxTIMjIFo6FEpZv41xuRmBW-c3ZTTTEC9nsM4k33Au34ZH-WVdLic-EuXPFwaligyoXy61-q3b36gSc4w5AERY4Hd3PwZaWmTfnYOZEzDG1qiNsiUIPe6cu0GNcyMeQGKETRF3z9ymkqmCLpHxuKESOIvOSZHwleSgEjkV5PY0cO8dOV1REPGiac0l_QZjwqKNZHWnXYug3_US34gOxmk8kuUk18M6zJ2eBig-veDrmtoY",
  
  // Map Background
  mapBox: "https://lh3.googleusercontent.com/aida-public/AB6AXuB7hY5hQD7qNC905YJX6FzxAVvERlRUvAFOiDYEWjz8wZ4oa5tvJfyclMj_JtuCVa44mjmhLVwMrihp54UdUQPd-N_7VENKL_vqai2Lk4cuxdAKpgDRaRoqDuDVl2Lw-05amflhfjeLtQorIPmItX-Cd2I2g0xd9WrSN-_2iuI7rH89e47u8KPtmmuIeZm0yOog_sTF7OdPYBn__exaR_6rDblNn9t0R1cEMSw7lDkSa4DvluIoSQrW8LSB43qlcPMJVONHCOhTRTY",
  
  // Cafe wood racks (Screen 7 suggestion 1 alternative / detail)
  cafeWood: "https://lh3.googleusercontent.com/aida-public/AB6AXuBLk0rmVWtDP-bXxyQxdn0N1ccX4dDyX5boUUfPfIWXFzyTb4sB8Yy1nGKQvlRuank9edIxit-J1zTT-1ZaCS7OJwOkHe03U1NKlihrXHI_U_XBUXtSQAdTU0H_pXB6H6EtbSoQrvkLtDhgvWix5K7DnEHO3EESqNoRvB116qvNNdvVxNj_LPcs635aftkEkE4u5gs87x-Q_f89u267RlaIwrpC_Vus0OVTHbBIUhnkSYg5Hy5_UcU1cRuqHt86738WbZ3vTWmc-m8",
  
  // Book shelves (Screen 7 bookstore Suggestion 2)
  bookstore: "https://lh3.googleusercontent.com/aida-public/AB6AXuAf5BhMilmqniVDeJIq30d6EeXUQFvAhDFzPl92K4JvFeJi5WmAEruIiwrQaURstHNNTFYAEulYs-NLGvA1Z-meMa56w8jo6LJmb_DXkQv-94F9YozDSY0QrI4Ly2u3F6AInZ28Clhn_Q8-f_4i7gRcgoFFpbGDGd3OUGYJDp9lg1y2ia86lobnRzO_ji3Q7EGJPGMRYBSyINOG_AJw5gTyviRcqF7UEUqY9ARa4x3SjYRD_Qex_LpRGYWoUVD0xVcvKEql8REuVM4",
};

export const INITIAL_WANDER_PLANS: WanderPlan[] = [
  {
    id: "plan-a",
    category: "轻松治愈",
    highlightTag: "静谧午后",
    title: "静谧午后：河边漫步与手冲咖啡",
    duration: "1.5h",
    cost: "¥40",
    area: "滨江公园区域",
    quote: "“适合你当下的低精力状态，通过流水与咖啡香气进行感官治愈。”",
    subChips: ["散步", "咖啡", "放空"],
    image: ASSETS.riversideCoffeeA,
    description: "检测到你当前能量值稍低，更适合轻松、低压力、可独处的放松型活动。这些方案能帮你温和地恢复状态。"
  },
  {
    id: "plan-b",
    category: "探索尝鲜",
    highlightTag: "探索尝鲜",
    title: "城市寻宝：复古黑胶店探索之旅",
    duration: "2h",
    cost: "¥20",
    area: "大学路艺术街区",
    quote: "“满足你轻微的好奇心，在旋律中寻找与城市连接的新鲜感。”",
    subChips: ["逛店", "音乐", "艺术"],
    image: ASSETS.vinylStore,
    description: "带着寻宝的心态在旧胶片里寻找温暖回响，不需过度社交也能获得新鲜而复古的心灵触动。"
  },
  {
    id: "plan-c",
    category: "低成本放空",
    highlightTag: "低成本放空",
    title: "夕阳漫游：公园长椅观察计划",
    duration: "45min",
    cost: "¥0",
    area: "市民公园南门区",
    quote: "“近距离、零压力的身心充电，观察世界的同时回归内心。”",
    subChips: ["公园", "日落", "冥想"],
    image: ASSETS.parkSunset,
    description: "坐在一张洒满金色夕阳的长椅上，什么也不做，只是享受微风和飞鸟掠过的风景，回归自然和本心。"
  }
];

export const MOCK_LEADERBOARD: PKParticipant[] = [
  { rank: 1, name: "独行者 042", avatarText: "042", timeSpent: "28 分钟", rating: 5.0 },
  { rank: 2, name: "城市漫游者", avatarText: "漫", timeSpent: "32 分钟", rating: 4.9 },
  { rank: 3, name: "云端漫步人", avatarText: "云", timeSpent: "35 分钟", rating: 4.9 },
  { rank: 15, name: "我", avatarText: "我", timeSpent: "进行中 --", rating: 4.8, isSelf: true }
];

export const COMMUNITY_LINES: CommunityLine[] = [
  {
    id: "line-1",
    title: "咖啡散步线",
    selectedCount: 12,
    activeWord: "放空治愈",
    tags: ["治愈", "安静"],
    image: ASSETS.riversideCoffeeB
  },
  {
    id: "line-2",
    title: "小吃探索线",
    selectedCount: 45,
    activeWord: "烟火之气",
    tags: ["热闹", "接地气"],
    image: "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=300&q=80"
  },
  {
    id: "line-3",
    title: "安静放空线",
    selectedCount: 8,
    activeWord: "无人打扰",
    tags: ["REST", "冥想"],
    image: ASSETS.bookstore
  }
];

export const MAP_PINS: MapInstancePin[] = [
  { id: "pin-1", type: "completed", lat: 100, lng: 100, title: "静谧小吃餐馆 (已点亮)", icon: "restaurant" },
  { id: "pin-2", type: "unexplored", lat: 200, lng: 120, title: "午后咖啡馆 (待点亮)", icon: "local_cafe" },
  { id: "pin-3", type: "solo_friendly", lat: 240, lng: 220, title: "言几又书店 (一人友好)", icon: "menu_book", badge: "一人友好 🌟" }
];

export const RECOMMENDED_PLACES: RecommendedPlace[] = [
  {
    id: "place-1",
    name: "Riverside Brew 河畔咖啡",
    image: ASSETS.riversideCoffeeB,
    score: 4.8,
    distance: "800m",
    checkinsToday: 12,
    description: "“提供单人静谧阅读区，窗外江景极佳，非常适合你现在的放松需求。”",
    activityType: "checkin",
    activityText: "去打卡"
  },
  {
    id: "place-2",
    name: "言几又书店",
    image: ASSETS.bookstore,
    score: 5.0,
    distance: "1.2km",
    checkinsToday: 38,
    description: "“超高挑空和无死角单人座位，完美的被书香裹挟的沉浸感受。”",
    activityType: "challenge",
    activityText: "踢馆挑战"
  }
];

export const RIVERSIDE_EVAL_DIMENSIONS = [
  { label: "单人座友好", score: 9.5, percentage: 95 },
  { label: "环境安静度", score: 8.8, percentage: 88 },
  { label: "一人套餐支持", score: 9.0, percentage: 90 },
  { label: "独处不尴尬度", score: 9.2, percentage: 92 },
  { label: "停留舒适度", score: 8.5, percentage: 85 },
  { label: "交通便利性", score: 8.0, percentage: 80 }
];
