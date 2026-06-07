// API 通信类型定义

export type SSEEventType = 'message' | 'interrupt' | 'error';

export type StreamResponseType = '[EMPATHY]' | '[PLANS]' | '[REQUIRE_USER_CONFIRM]';

export type ThreadStatus = 'active' | 'waiting_confirmation' | 'completed';

export interface StreamChatRequest {
  message: string;
  thread_id: string;
}

export interface StreamChatResponse {
  thread_id: string;
  status: ThreadStatus;
  message_count: number;
}

export interface ThreadState {
  thread_id: string;
  status: ThreadStatus;
  messages: Array<{
    id?: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
  }>;
  metadata: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface SSEMessageEvent {
  type: SSEEventType;
  data: string;
  rawEvent: MessageEvent;
}

export interface ParsedSSEData {
  type: 'empathy' | 'plans' | 'require_confirmation' | 'raw';
  content: string | Record<string, any>;
  raw: string;
}

export interface StreamHookState {
  isConnected: boolean;
  isWaiting: boolean;
  threadId: string | null;
  currentMessage: string;
  messages: ParsedSSEData[];
  error: string | null;
  plans: WanderPlan[];
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

export interface RiskAssessment {
  is_risky: boolean;
  risk_level: string;
  message: string;
  requires_confirmation: boolean;
}

// Hook 配置选项
export interface UseSoloStreamOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (data: ParsedSSEData) => void;
  onWaitingForConfirmation?: () => void;
  onError?: (error: string) => void;
  onConnectionChange?: (isConnected: boolean) => void;
}

// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ResumeThreadRequest {
  thread_id: string;
  user_confirmed: boolean;
}

export interface ResumeThreadResponse {
  message: string;
  thread_id: string;
  status: ThreadStatus;
}

// 地图相关类型
export interface MapInstancePin {
  id: string;
  name: string;
  lat: number;
  lng: number;
  category?: string;
  description?: string;
}
