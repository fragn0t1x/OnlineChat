// support-widget.js
(function() {
  // Определяем базовый URL автоматически
  const scriptSrc = document.currentScript?.src || '';
  const widgetDomain = new URL(scriptSrc).origin;
  const API_BASE = `${widgetDomain}/api`;

  let chatId = localStorage.getItem('support_chat_id');
  let isPolling = false;
  let audioContext = null;
  let lastRenderedCount = 0;

  // Создаём DOM-элементы
  function createWidget() {
    if (document.getElementById('support-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'support-widget';
    widget.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 340px;
      z-index: 10000;
      display: none;
      background: white;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    `;
    widget.innerHTML = `
      <div style="padding:16px 20px;background:#4361ee;color:white;font-weight:600;font-size:18px;">
        💬 Поддержка
        <span id="online-status" style="float:right;display:flex;align-items:center;gap:6px;font-size:12px;">
          <div style="width:8px;height:8px;border-radius:50%;background:#28a745;"></div>
          <span>Онлайн</span>
        </span>
      </div>
      <div id="support-messages" style="height:300px;padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;"></div>
      <div id="typing-indicator" style="padding:8px 16px;font-size:12px;color:#6c757d;display:none;">Оператор печатает...</div>
      <div style="padding:12px;border-top:1px solid #dee2e6;display:flex;gap:8px;">
        <input type="text" id="support-input" placeholder="Напишите сообщение..." style="flex:1;padding:10px 14px;border:1px solid #dee2e6;border-radius:24px;outline:none;font-size:14px;" />
        <button onclick="window.supportWidget.sendMessage()" style="width:40px;height:40px;border-radius:50%;background:#4361ee;color:white;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;padding:0;">➤</button>
      </div>
    `;
    document.body.appendChild(widget);

    const toggleBtn = document.createElement('div');
    toggleBtn.id = 'toggle-widget';
    toggleBtn.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      background: #4361ee;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(67,97,238,0.4);
      z-index: 10001;
      font-size: 24px;
    `;
    toggleBtn.textContent = '💬';
    toggleBtn.onclick = () => window.supportWidget.toggleWidget();
    document.body.appendChild(toggleBtn);
  }

  // Инициализация аудио
  function playNotificationSound() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    oscillator.frequency.value = 800;
    gainNode.gain.value = 0.1;
    oscillator.start();
    setTimeout(() => oscillator.stop(), 200);
  }

  // Форматирование даты
  function formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date >= today) return 'Сегодня';
    if (date >= yesterday) return 'Вчера';

    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'numeric', year: 'numeric' });
  }

  // Форматирование времени
  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  }

  // Методы виджета
  window.supportWidget = {
    toggleWidget: function() {
      const widget = document.getElementById('support-widget');
      const isVisible = widget.style.display === 'block';

      if (!isVisible) {
        widget.style.display = 'block';
        if (!chatId) this.initChat();
        this.startPolling();
      } else {
        widget.style.display = 'none';
        this.stopPolling();
      }
    },

    initChat: async function() {
      const res = await fetch(`${API_BASE}/chat/start`);
      const data = await res.json();
      chatId = data.chat_id;
      localStorage.setItem('support_chat_id', chatId);
      this.loadMessages();
    },

    loadMessages: async function() {
      if (!chatId) return;
      try {
        const messagesEl = document.getElementById('support-messages');
        if (!messagesEl) return;

        const wasAtBottom = messagesEl.scrollHeight - messagesEl.scrollTop === messagesEl.clientHeight;

        const res = await fetch(`${API_BASE}/chat/${chatId}`);
        const data = await res.json();

        if (data.messages.length !== lastRenderedCount) {
          this.renderMessages(data.messages);
          lastRenderedCount = data.messages.length;

          if (wasAtBottom) {
            messagesEl.scrollTop = messagesEl.scrollHeight;
          }

          if (data.messages.length > 0) {
            const lastMsg = data.messages[data.messages.length - 1];
            if (lastMsg.sender === 'operator') {
              playNotificationSound();
            }
          }
        }

        // Статус "оператор печатает"
        const typingRes = await fetch(`${API_BASE}/chat/${chatId}/typing?role=operator`);
        const typingData = await typingRes.json();
        const typingEl = document.getElementById('typing-indicator');
        if (typingEl) {
          typingEl.style.display = typingData.is_typing ? 'block' : 'none';
        }
      } catch (e) {
        console.error('Ошибка загрузки сообщений:', e);
      }
    },

    renderMessages: function(messages) {
      const el = document.getElementById('support-messages');
      if (!el) return;

      const groups = {};
      messages.forEach(m => {
        const dateKey = formatDate(m.created_at);
        if (!groups[dateKey]) groups[dateKey] = [];
        groups[dateKey].push(m);
      });

      el.innerHTML = '';
      Object.keys(groups).forEach(dateLabel => {
        const dateDiv = document.createElement('div');
        dateDiv.style.marginTop = '16px';
        dateDiv.style.fontSize = '12px';
        dateDiv.style.color = '#6c757d';
        dateDiv.style.textAlign = 'center';
        dateDiv.textContent = dateLabel;
        el.appendChild(dateDiv);

        groups[dateLabel].forEach(m => {
          const div = document.createElement('div');
          div.className = `message ${m.sender === 'visitor' ? 'visitor' : 'operator'}`;
          div.style.maxWidth = '80%';
          div.style.padding = '10px 14px';
          div.style.borderRadius = '18px';
          div.style.lineHeight = '1.4';
          if (m.sender === 'visitor') {
            div.style.alignSelf = 'flex-end';
            div.style.background = '#4361ee';
            div.style.color = 'white';
            div.style.borderBottomRightRadius = '4px';
          } else {
            div.style.alignSelf = 'flex-start';
            div.style.background = '#e9ecef';
            div.style.color = '#212529';
            div.style.borderBottomLeftRadius = '4px';
          }

          div.textContent = m.text || '—';

          const timeEl = document.createElement('div');
          timeEl.style.fontSize = '10px';
          timeEl.style.opacity = '0.7';
          timeEl.style.marginTop = '4px';
          timeEl.style.textAlign = m.sender === 'visitor' ? 'right' : 'left';
          timeEl.textContent = formatTime(m.created_at);
          div.appendChild(timeEl);

          el.appendChild(div);
        });
      });
    },

    sendMessage: async function() {
      const text = document.getElementById('support-input').value.trim();
      if (!text) return;

      await fetch(`${API_BASE}/chat/${chatId}/typing`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({role: 'visitor', is_typing: false})
      });

      const formData = new FormData();
      formData.append('text', text);
      const res = await fetch(`${API_BASE}/chat/${chatId}/message`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        document.getElementById('support-input').value = '';
        this.loadMessages();
      }
    },

    startPolling: function() {
      if (isPolling) return;
      isPolling = true;
      this.loadMessages();
      this.pollInterval = setInterval(() => this.loadMessages(), 2000);
    },

    stopPolling: function() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }
      isPolling = false;
    }
  };

  // Обработка Enter
  document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.id === 'support-input') {
      window.supportWidget.sendMessage();
    }
  });

  // Обработка набора текста
  document.addEventListener('input', (e) => {
    if (e.target.id === 'support-input' && chatId) {
      fetch(`${API_BASE}/chat/${chatId}/typing`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({role: 'visitor', is_typing: true})
      });

      clearTimeout(this.typingTimeout);
      this.typingTimeout = setTimeout(() => {
        fetch(`${API_BASE}/chat/${chatId}/typing`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({role: 'visitor', is_typing: false})
        });
      }, 2000);
    }
  });

  // Инициализация
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();