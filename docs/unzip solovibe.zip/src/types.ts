export type ScreenId =
  | "challenge"       // 1. 今日挑战
  | "chat"            // 2. AI 单人对话
  | "solutions"       // 3. 3个定制方案
  | "booking"         // 4. AI 正在安排/一键预约
  | "pk"              // 5. 今日轻量PK
  | "resonance"       // 6. 发现同路人/同城共鸣
  | "map"             // 7. 城市副本
  | "index";          // 8. 一人友好指数

export interface Message {
  id: string;
  role: "user" | "model";
  content: string;
  timestamp: string;
}

export interface WanderPlan {
  id: string;
  title: string;
  category: string;
  duration: string;
  cost: string;
  area: string;
  quote: string;
  highlightTag: string;
  subChips: string[];
  description: string;
  image: string;
}

export interface PKParticipant {
  rank: number;
  name: string;
  avatarText: string;
  timeSpent: string;
  rating: number;
  isSelf?: boolean;
}

export interface CommunityLine {
  id: string;
  title: string;
  selectedCount: number;
  activeWord: string;
  tags: string[];
  image: string;
}

export interface MapInstancePin {
  id: string;
  type: "completed" | "unexplored" | "solo_friendly";
  lat: number;
  lng: number;
  title: string;
  icon: string;
  badge?: string;
}

export interface RecommendedPlace {
  id: string;
  name: string;
  image: string;
  score: number;
  distance: string;
  checkinsToday: number;
  description: string;
  activityType: "checkin" | "challenge";
  activityText: string;
}
