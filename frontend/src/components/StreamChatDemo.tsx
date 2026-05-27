import React, { useState, useEffect } from 'react';
import { useSoloStream, useSimpleSoloStream } from '../hooks/useSoloStream';

/**
 * 流式聊天演示组件
 * 展示SSE连接、消息处理和HITL中断功能
 */
export const StreamChatDemo: React.FC = () => {
  const [inputMessage, setInputMessage] = useState('');
  const [sessionThreadId, setSessionThreadId] = useState<string | null>(null);
  
  // 使用完整功能的Hook
  const {
    isConnected,
    isWaiting,
    threadId,
    currentMessage,
    messages,
    error,
    plans,
    sendMessage,
    resumeThread,
    reset
  } = useSoloStream({
    autoReconnect: true,
    maxReconnectAttempts: 3,
    onMessage: (data) => {
      console.log('收到消息:', data);
    },
    onWaitingForConfirmation: () => {
      console.log('等待用户确认...');
      // 这里可以触发UI弹窗
    },
    onError: (errorMsg) => {
      console.error('流错误:', errorMsg);
    }
  });

  // 处理发送消息
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    
    try {
      const threadId = await sendMessage(inputMessage, sessionThreadId || undefined);
      setSessionThreadId(threadId);
      setInputMessage('');
    } catch (error) {
      console.error('发送消息失败:', error);
    }
  };

  // 处理用户确认
  const handleUserConfirmation = async (confirmed: boolean) => {
    if (!threadId) return;
    
    try {
      await resumeThread(threadId, confirmed);
      console.log(`用户${confirmed ? '确认' : '取消'}了操作`);
    } catch (error) {
      console.error('恢复线程失败:', error);
    }
  };

  // 处理回车发送
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">SoloVibe 流式聊天演示</h1>
        
        {/* 连接状态 */}
        <div className="flex items-center space-x-4 mb-6">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm text-gray-600">
            连接状态: {isConnected ? '已连接' : '未连接'}
          </span>
          
          <div className={`px-3 py-1 rounded-full text-xs ${isWaiting ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
            {isWaiting ? '等待确认' : '正常运行'}
          </div>
          
          {threadId && (
            <span className="text-sm text-gray-500">
              Thread ID: {threadId}
            </span>
          )}
        </div>

        {/* 输入区域 */}
        <div className="flex space-x-2 mb-6">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的消息..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isWaiting}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isWaiting}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            发送
          </button>
        </div>

        {/* HITL中断确认区域 */}
        {isWaiting && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-yellow-800 mb-2">需要您的确认</h3>
            <p className="text-yellow-700 mb-4">AI助手提出了一些建议，请您确认是否继续执行。</p>
            <div className="flex space-x-3">
              <button
                onClick={() => handleUserConfirmation(true)}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
              >
                确认继续
              </button>
              <button
                onClick={() => handleUserConfirmation(false)}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
              >
                取消操作
              </button>
            </div>
          </div>
        )}

        {/* 错误信息 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
            <p className="text-red-800">错误: {error}</p>
          </div>
        )}

        {/* 当前消息显示 */}
        {currentMessage && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-800 mb-2">当前消息</h3>
            <p className="text-blue-700">{currentMessage}</p>
          </div>
        )}

        {/* 计划显示 */}
        {plans.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-green-800 mb-3">推荐的计划 ({plans.length})</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {plans.map((plan, index) => (
                <div key={index} className="bg-white rounded border p-3">
                  <h4 className="font-medium text-gray-800">{plan.title}</h4>
                  <p className="text-sm text-gray-600 mt-1">{plan.description}</p>
                  <div className="flex justify-between text-sm text-gray-500 mt-2">
                    <span>{plan.duration}</span>
                    <span>{plan.cost}</span>
                    <span>{plan.area}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {plan.subChips.map((chip, chipIndex) => (
                      <span key={chipIndex} className="px-2 py-1 bg-gray-100 text-xs rounded">
                        {chip}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 消息历史 */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">消息历史</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {messages.map((message, index) => (
              <div key={index} className={`p-3 rounded text-sm ${
                message.type === 'empathy' ? 'bg-blue-100 text-blue-800' :
                message.type === 'plans' ? 'bg-green-100 text-green-800' :
                message.type === 'require_confirmation' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                <div className="flex justify-between items-start">
                  <span className="font-medium">
                    {message.type === 'empathy' && '同理心回应'}
                    {message.type === 'plans' && '计划提案'}
                    {message.type === 'require_confirmation' && '需要确认'}
                    {message.type === 'raw' && '其他消息'}
                  </span>
                  <span className="text-xs opacity-75">#{index + 1}</span>
                </div>
                <p className="mt-1">{String(message.content)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 控制按钮 */}
        <div className="flex space-x-3 mt-6">
          <button
            onClick={reset}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            重置会话
          </button>
        </div>
      </div>

      {/* 快速演示区域 */}
      <QuickDemoSection />
    </div>
  );
};

/**
 * 快速演示区域
 */
const QuickDemoSection: React.FC = () => {
  const { sendSimpleMessage, isWaiting, plans } = useSimpleSoloStream();
  
  const quickMessages = [
    "我想找个地方独自待会儿",
    "推荐一些适合独自体验的活动",
    "心情不太好，有什么建议吗？"
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-gray-800">快速演示</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {quickMessages.map((message, index) => (
          <button
            key={index}
            onClick={() => sendSimpleMessage(message)}
            disabled={isWaiting}
            className="p-3 bg-gray-100 hover:bg-gray-200 rounded-lg text-left disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <p className="text-sm text-gray-700">{message}</p>
          </button>
        ))}
      </div>

      {isWaiting && (
        <div className="mt-4 p-3 bg-yellow-100 border border-yellow-200 rounded text-yellow-800">
          等待用户确认...
        </div>
      )}

      {plans.length > 0 && (
        <div className="mt-4">
          <h3 className="font-medium text-gray-700 mb-2">最新计划:</h3>
          <div className="space-y-2">
            {plans.slice(-1).map((plan, index) => (
              <div key={index} className="text-sm text-gray-600">
                <strong>{plan.title}</strong> - {plan.area} ({plan.duration})
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamChatDemo;
