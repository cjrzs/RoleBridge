<template>
  <div class="translation-interface">
    <div class="input-section">
      <h2>输入内容</h2>
      <textarea
        v-model="inputContent"
        placeholder="请输入要翻译的内容..."
        rows="8"
        class="input-textarea"
      ></textarea>
      
      <div class="role-selector">
        <div class="selector-group">
          <label>源角色（可选）</label>
          <select v-model="sourceRole" class="role-select">
            <option value="">不指定</option>
            <option value="product">产品经理</option>
            <option value="developer">开发工程师</option>
            <option value="ops">运营</option>
            <option value="management">管理层</option>
            <option value="other">其他</option>
          </select>
          <input
            v-if="sourceRole === 'other'"
            v-model="customSourceRole"
            type="text"
            placeholder="请输入自定义角色名称"
            class="custom-role-input"
          />
        </div>
        
        <div class="selector-group">
          <label>目标角色 *</label>
          <select v-model="targetRole" class="role-select" required>
            <option value="">请选择</option>
            <option value="developer">开发工程师</option>
            <option value="product">产品经理</option>
            <option value="ops">运营</option>
            <option value="management">管理层</option>
            <option value="other">其他</option>
          </select>
          <input
            v-if="targetRole === 'other'"
            v-model="customTargetRole"
            type="text"
            placeholder="请输入自定义角色名称"
            class="custom-role-input"
          />
        </div>
      </div>
      
      <div class="mode-selector">
        <label>
          <input type="radio" v-model="useAgent" :value="true" />
          使用Agent模式（实时思考过程）
        </label>
        <label>
          <input type="radio" v-model="useAgent" :value="false" />
          使用传统模式
        </label>
      </div>
      
      <div class="button-group">
        <button
          @click="handleTranslate"
          :disabled="!canTranslate"
          class="translate-button"
        >
          {{ isTranslating ? '翻译中...' : '开始翻译' }}
        </button>
        <button
          @click="clearResults"
          :disabled="clearDisabled"
          class="clear-button"
        >
          清除翻译结果
        </button>
      </div>
    </div>
    
    <div class="output-section">
      <h2>翻译结果</h2>
      
      <!-- Thinking Process Display (Agent Mode) -->
      <div v-if="useAgent && thinkingSteps.length > 0" class="thinking-process">
        <div class="thinking-header" @click="toggleThinkingCollapse">
          <h3>🤔 Agent思考过程</h3>
          <span class="collapse-icon">{{ isThinkingCollapsed ? '▼' : '▲' }}</span>
        </div>
        <div v-show="!isThinkingCollapsed" class="thinking-steps">
          <div
            v-for="(step, index) in thinkingSteps"
            :key="index"
            class="thinking-step"
            :class="step.type"
          >
            <div class="step-header">
              <span class="step-icon">{{ getStepIcon(step.type) }}</span>
              <span class="step-type">{{ getStepTypeName(step.type) }}</span>
              <span class="step-time">{{ formatTime(step.timestamp) }}</span>
            </div>
            <div class="step-content">{{ step.content }}</div>
          </div>
        </div>
      </div>
      
      <div v-if="translatedContent" class="output-content" v-html="formattedOutput"></div>
      <div v-else class="placeholder">
        <p>翻译结果将显示在这里...</p>
      </div>
      
      <div v-if="uncertainties.length > 0" class="uncertainties">
        <h3>需要确认的问题</h3>
        <ul>
          <li v-for="(item, index) in uncertainties" :key="index">{{ item }}</li>
        </ul>
      </div>
    </div>
    
    <!-- Confirmation Modal -->
    <div v-if="showConfirmationModal" class="modal-overlay" @click="closeConfirmationModal">
      <div class="modal-content" @click.stop>
        <h3>❓ 需要确认</h3>
        <p class="confirmation-question">{{ currentConfirmation?.question }}</p>
        <div v-if="currentConfirmation?.options" class="confirmation-options">
          <button
            v-for="(value, key) in currentConfirmation.options"
            :key="key"
            @click="respondToConfirmation(key)"
            class="option-button"
          >
            {{ value }}
          </button>
        </div>
        <div class="modal-actions">
          <button @click="respondToConfirmation(null)" class="cancel-button">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { marked } from 'marked'

export default {
  name: 'TranslationInterface',
  data() {
    return {
      inputContent: '',
      sourceRole: '',
      customSourceRole: '',
      targetRole: '',
      customTargetRole: '',
      translatedContent: '',
      uncertainties: [],
      isTranslating: false,
      useAgent: true, // Default to Agent mode
      websocket: null,
      thinkingSteps: [],
      showConfirmationModal: false,
      currentConfirmation: null,
      isThinkingCollapsed: false
    }
  },
  computed: {
    canTranslate() {
      const hasContent = this.inputContent.trim()
      const hasTargetRole = this.targetRole && (this.targetRole !== 'other' || this.customTargetRole.trim())
      return hasContent && hasTargetRole && !this.isTranslating
    },
    effectiveSourceRole() {
      // 返回实际使用的源角色值
      return this.sourceRole === 'other' ? this.customSourceRole.trim() : this.sourceRole || null
    },
    effectiveTargetRole() {
      // 返回实际使用的目标角色值
      return this.targetRole === 'other' ? this.customTargetRole.trim() : this.targetRole
    },
    formattedOutput() {
      // Render markdown to HTML
      if (!this.translatedContent) return ''
      try {
        return marked(this.translatedContent)
      } catch (error) {
        console.error('Markdown parsing error:', error)
        return this.translatedContent.replace(/\n/g, '<br>')
      }
    },
    clearDisabled() {
      return !this.translatedContent &&
        this.uncertainties.length === 0 &&
        this.thinkingSteps.length === 0 &&
        !this.showConfirmationModal &&
        !this.currentConfirmation
    }
  },
  methods: {
    async handleTranslate() {
      if (!this.canTranslate) return
      
      this.isTranslating = true
      this.translatedContent = ''
      this.uncertainties = []
      this.thinkingSteps = []
      this.isThinkingCollapsed = false
      
      if (this.useAgent) {
        await this.handleTranslateWithAgent()
      } else {
        await this.handleTranslateTraditional()
      }
    },
    
    async handleTranslateTraditional() {
      try {
        const response = await axios.post('/api/translate', {
          content: this.inputContent,
          target_role: this.effectiveTargetRole,
          source_role: this.effectiveSourceRole
        })
        
        this.translatedContent = response.data.translated_content
        this.uncertainties = response.data.uncertainties || []
      } catch (error) {
        console.error('Translation error:', error)
        alert('翻译失败，请稍后重试')
      } finally {
        this.isTranslating = false
      }
    },
    
    async handleTranslateWithAgent() {
      // Get WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/api/ws/translate`
      
      return new Promise((resolve, reject) => {
        try {
          this.websocket = new WebSocket(wsUrl)
          
          this.websocket.onopen = () => {
            console.log('WebSocket connected')
            // Send translation request
            this.websocket.send(JSON.stringify({
              type: 'start_translation',
              data: {
                content: this.inputContent,
                target_role: this.effectiveTargetRole,
                source_role: this.effectiveSourceRole
              }
            }))
          }
          
          this.websocket.onmessage = (event) => {
            try {
              const message = JSON.parse(event.data)
              this.handleWebSocketMessage(message)
            } catch (error) {
              console.error('Failed to parse WebSocket message:', error)
              console.error('Raw message data:', event.data)
              alert('收到格式错误的消息，请刷新页面重试')
              this.isTranslating = false
              if (this.websocket) {
                this.websocket.close()
                this.websocket = null
              }
            }
          }
          
          this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error)
            alert('WebSocket连接错误，请稍后重试')
            this.isTranslating = false
            reject(error)
          }
          
          this.websocket.onclose = () => {
            console.log('WebSocket disconnected')
            this.isTranslating = false
            resolve()
          }
        } catch (error) {
          console.error('Failed to create WebSocket:', error)
          alert('无法建立WebSocket连接，请检查服务器配置')
          this.isTranslating = false
          reject(error)
        }
      })
    },
    
    handleWebSocketMessage(message) {
      const { type, data } = message
      
      switch (type) {
        case 'thinking':
        case 'action':
        case 'observation':
        case 'decision':
          // Add thinking step
          this.thinkingSteps.push({
            type: type === 'action' ? 'act' : type === 'observation' ? 'observe' : type === 'decision' ? 'decision' : 'think',
            content: data.content || data,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata
          })
          break
          
        case 'role_check':
          // Role check completed - add as observation
          if (data && !data.is_predefined) {
            this.thinkingSteps.push({
              type: 'observe',
              content: `角色检查完成：'${data.role_name}'是未知角色，需要进行模板分析`,
              timestamp: new Date().toISOString()
            })
          }
          break
          
        case 'role_analyzed':
          // Role analysis completed (for unknown roles)
          // This is already handled by thinking steps, but we can add additional processing if needed
          if (data && data.analysis) {
            this.thinkingSteps.push({
              type: 'observe',
              content: `角色分析完成，已为'${data.role_name}'生成模板结构`,
              timestamp: new Date().toISOString()
            })
          }
          break
          
        case 'framework_extracted':
          // Framework extraction completed
          if (data && data.uncertainties_count !== undefined) {
            this.thinkingSteps.push({
              type: 'observe',
              content: `决策框架数据提取完成，发现${data.uncertainties_count}个不确定点`,
              timestamp: new Date().toISOString()
            })
          }
          break
          
        case 'confirmation_request':
          // Show confirmation modal
          this.currentConfirmation = data
          this.showConfirmationModal = true
          break
          
        case 'translation_chunk':
          // Append translation chunk (only for predefined roles)
          if (!this.translatedContent) {
            this.translatedContent = ''
          }
          this.translatedContent += data
          break
          
        case 'completed':
          // Translation completed
          this.uncertainties = data.uncertainties || []
          this.isTranslating = false
          // Auto-collapse thinking process after completion
          this.isThinkingCollapsed = true
          if (this.websocket) {
            this.websocket.close()
            this.websocket = null
          }
          break
          
        case 'error':
          // Handle error
          console.error('Translation error:', data.error)
          alert(`翻译错误: ${data.error}`)
          this.isTranslating = false
          if (this.websocket) {
            this.websocket.close()
            this.websocket = null
          }
          break
          
        case 'pong':
          // Heartbeat response
          break
          
        default:
          console.log('Unknown message type:', type, data)
      }
    },
    
    respondToConfirmation(response) {
      if (this.currentConfirmation && this.websocket) {
        this.websocket.send(JSON.stringify({
          type: 'confirmation_response',
          data: {
            request_id: this.currentConfirmation.request_id,
            response: response
          }
        }))
      }
      this.closeConfirmationModal()
    },
    
    closeConfirmationModal() {
      this.showConfirmationModal = false
      this.currentConfirmation = null
    },

    clearResults() {
      this.translatedContent = ''
      this.uncertainties = []
      this.thinkingSteps = []
      this.showConfirmationModal = false
      this.currentConfirmation = null
      this.isThinkingCollapsed = false
    },
    
    getStepIcon(type) {
      const icons = {
        'think': '💭',
        'act': '⚡',
        'observe': '👀',
        'confirm': '❓',
        'decision': '✅'
      }
      return icons[type] || '📝'
    },
    
    getStepTypeName(type) {
      const names = {
        'think': '思考',
        'act': '行动',
        'observe': '观察',
        'confirm': '确认',
        'decision': '决策'
      }
      return names[type] || type
    },
    
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN')
    },
    
    toggleThinkingCollapse() {
      this.isThinkingCollapsed = !this.isThinkingCollapsed
    }
  },
  
  beforeUnmount() {
    if (this.websocket) {
      this.websocket.close()
    }
  }
}
</script>

<style scoped>
.translation-interface {
  display: grid;
  grid-template-columns: 3fr 7fr;
  gap: 2rem;
  margin-top: 2rem;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
  height: 100%;
}

.input-section,
.output-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 100%;
  overflow-x: auto;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  max-height: 100%;
}

h2 {
  margin-bottom: 1rem;
  color: #667eea;
}

.input-textarea {
  width: 100%;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 1rem;
}

.input-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.role-selector {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.selector-group {
  flex: 1;
}

.selector-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.role-select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  background: white;
}

.role-select:focus {
  outline: none;
  border-color: #667eea;
}

.custom-role-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  margin-top: 0.5rem;
  background: white;
}

.custom-role-input:focus {
  outline: none;
  border-color: #667eea;
}

.mode-selector {
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.mode-selector label {
  display: block;
  margin-bottom: 0.5rem;
  cursor: pointer;
}

.mode-selector label:last-child {
  margin-bottom: 0;
}

.button-group {
  display: flex;
  gap: 0.75rem;
}

.translate-button,
.clear-button {
  flex: 1;
  padding: 1rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.3s;
}

.translate-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.translate-button:hover:not(:disabled),
.clear-button:hover:not(:disabled) {
  opacity: 0.9;
}

.translate-button:disabled,
.clear-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.clear-button {
  background: #e0e0e0;
  color: #333;
}

.thinking-process {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 4px solid #667eea;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.thinking-header:hover {
  opacity: 0.8;
}

.thinking-header h3 {
  margin-bottom: 0;
  color: #667eea;
  font-size: 1.1rem;
}

.collapse-icon {
  color: #667eea;
  font-size: 0.9rem;
  transition: transform 0.3s;
}

.thinking-steps {
  max-height: 300px;
  overflow-y: auto;
}

.thinking-step {
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #ddd;
}

.thinking-step.think {
  border-left-color: #667eea;
}

.thinking-step.act {
  border-left-color: #f59e0b;
}

.thinking-step.observe {
  border-left-color: #10b981;
}

.thinking-step.decision {
  border-left-color: #8b5cf6;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.step-icon {
  font-size: 1.2rem;
}

.step-type {
  font-weight: 600;
  color: #555;
}

.step-time {
  margin-left: auto;
  color: #999;
  font-size: 0.85rem;
}

.step-content {
  color: #333;
  line-height: 1.5;
}

.output-content {
  min-height: 200px;
  max-height: 500px;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 4px;
  line-height: 1.6;
  overflow-y: auto;
}

/* Markdown styles */
.output-content :deep(h1),
.output-content :deep(h2),
.output-content :deep(h3),
.output-content :deep(h4),
.output-content :deep(h5),
.output-content :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  color: #333;
}

.output-content :deep(h1) {
  font-size: 1.8em;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.3em;
}

.output-content :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 0.3em;
}

.output-content :deep(h3) {
  font-size: 1.3em;
}

.output-content :deep(p) {
  margin-bottom: 1em;
}

.output-content :deep(ul),
.output-content :deep(ol) {
  margin-left: 1.5em;
  margin-bottom: 1em;
}

.output-content :deep(li) {
  margin-bottom: 0.5em;
}

.output-content :deep(code) {
  background: #f4f4f4;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.output-content :deep(pre) {
  background: #f4f4f4;
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 1em;
}

.output-content :deep(pre code) {
  background: none;
  padding: 0;
}

.output-content :deep(blockquote) {
  border-left: 4px solid #667eea;
  padding-left: 1em;
  margin-left: 0;
  color: #666;
  font-style: italic;
}

.output-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.output-content :deep(th),
.output-content :deep(td) {
  border: 1px solid #ddd;
  padding: 0.5em;
  text-align: left;
}

.output-content :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.output-content :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.output-content :deep(a:hover) {
  text-decoration: underline;
}

.output-content :deep(strong) {
  font-weight: 600;
}

.output-content :deep(em) {
  font-style: italic;
}

.placeholder {
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.uncertainties {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
}

.uncertainties h3 {
  margin-bottom: 0.5rem;
  color: #856404;
}

.uncertainties ul {
  margin-left: 1.5rem;
  color: #856404;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-content h3 {
  margin-bottom: 1rem;
  color: #667eea;
}

.confirmation-question {
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
  line-height: 1.6;
  color: #333;
}

.confirmation-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.option-button {
  padding: 0.75rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.3s;
}

.option-button:hover {
  opacity: 0.9;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
}

.cancel-button {
  padding: 0.5rem 1rem;
  background: #e0e0e0;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.cancel-button:hover {
  background: #d0d0d0;
}

@media (max-width: 768px) {
  .translation-interface {
    grid-template-columns: 1fr;
  }
}
</style>
