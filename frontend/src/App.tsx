import React, { useState } from 'react'
import { MapPage } from './components/MapPage'
import { StreamChatDemo } from './components/StreamChatDemo'
import './index.css'

function App() {
  const [currentPage, setCurrentPage] = useState<'chat' | 'map'>('chat')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 导航头部 */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-800">🧘‍♀️ SoloVibe</h1>
            <nav className="flex space-x-4">
              <button 
                onClick={() => setCurrentPage('chat')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'chat' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                🤖 AI对话
              </button>
              <button 
                onClick={() => setCurrentPage('map')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'map' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                🗺️ 发现好去处
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* 主要内容区域 */}
      <main className="container mx-auto px-4 py-6">
        {currentPage === 'chat' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">🧠 Gemini 2.5 Pro 智能对话</h2>
            <p className="text-gray-600 mb-6">
              基于自适应情商机制的对话体验
            </p>
            <StreamChatDemo />
          </div>
        )}
        
        {currentPage === 'map' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">🎯 独处好去处</h2>
            <p className="text-gray-600 mb-6">
              发现治愈系的安静角落
            </p>
            <MapPage 
              center={{ lat: 31.2304, lng: 121.4737 }} 
              zoom={12}
            />
          </div>
        )}
      </main>

      {/* 页脚说明 */}
      <footer className="bg-white border-t mt-8">
        <div className="container mx-auto px-4 py-4">
          <div className="text-center text-sm text-gray-500">
            <p>使用 Gemini 2.5 Pro 驱动 • 支持流式 SSE • 自适应情商算法</p>
            <p>(c) 2026 SoloVibe - 让独处更有意义</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App