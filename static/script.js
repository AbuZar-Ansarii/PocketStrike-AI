// App State
let conversations = [];
let activeConversationId = null;
let isGenerating = false;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const menuBtn = document.getElementById('menuBtn');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const newChatBtn = document.getElementById('newChatBtn');
const sidebarHistory = document.getElementById('sidebarHistory');
const clearBtn = document.getElementById('clearBtn');
const messagesContainer = document.getElementById('messagesContainer');
const welcomeScreen = document.getElementById('welcomeScreen');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const headerModelBadge = document.getElementById('headerModelBadge');
const statusProvider = document.getElementById('statusProvider');
const statusModel = document.getElementById('statusModel');
const statusTelegram = document.getElementById('statusTelegram');
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeIcon = document.getElementById('themeIcon');

// MCP DOM Elements
const mcpModal = document.getElementById('mcpModal');
const addMcpBtn = document.getElementById('addMcpBtn');
const mcpCancelBtn = document.getElementById('mcpCancelBtn');
const mcpSubmitBtn = document.getElementById('mcpSubmitBtn');
const mcpName = document.getElementById('mcpName');
const mcpUrl = document.getElementById('mcpUrl');
const sidebarMcpList = document.getElementById('sidebarMcpList');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadConversations();
    initEventListeners();
    fetchBackendStatus();
    loadMcpConnections();
    renderAll();
});

// Event Listeners
function initEventListeners() {
    // Mobile Sidebar Toggle
    menuBtn.addEventListener('click', toggleSidebar);
    closeSidebarBtn.addEventListener('click', toggleSidebar);
    sidebarOverlay.addEventListener('click', toggleSidebar);

    // Theme Toggle
    themeToggleBtn.addEventListener('click', toggleTheme);

    // New Chat Action
    newChatBtn.addEventListener('click', () => {
        createNewChat();
        if (window.innerWidth <= 768) toggleSidebar();
    });

    // Clear Chats
    clearBtn.addEventListener('click', clearAllConversations);

    // Textarea Auto-grow and Enter-to-Submit
    chatInput.addEventListener('input', autoGrowInput);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            const isMobile = window.innerWidth <= 768;
            if (!isMobile) {
                e.preventDefault();
                handleSend();
            }
        }
        setTimeout(autoGrowInput, 0);
    });

    // Send Button Click
    sendBtn.addEventListener('click', handleSend);

    // MCP Modal Toggles
    if (addMcpBtn) addMcpBtn.addEventListener('click', openMcpModal);
    if (mcpCancelBtn) mcpCancelBtn.addEventListener('click', closeMcpModal);
    if (mcpSubmitBtn) mcpSubmitBtn.addEventListener('click', handleAddMcp);
    
    // Close modal on background click
    window.addEventListener('click', (e) => {
        if (e.target === mcpModal) closeMcpModal();
    });
}

// Initialize Theme from LocalStorage or default to dark
function initTheme() {
    const savedTheme = localStorage.getItem('pocketstrike_theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        setLightModeIcon();
    } else {
        document.body.classList.remove('light-mode');
        setDarkModeIcon();
    }
}

// Toggle between light and dark modes
function toggleTheme() {
    const isLight = document.body.classList.toggle('light-mode');
    if (isLight) {
        localStorage.setItem('pocketstrike_theme', 'light');
        setLightModeIcon();
    } else {
        localStorage.setItem('pocketstrike_theme', 'dark');
        setDarkModeIcon();
    }
}

// Show moon icon (click to switch to dark mode)
function setLightModeIcon() {
    themeIcon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    themeToggleBtn.setAttribute('title', 'Switch to Dark Mode');
}

// Show sun icon (click to switch to light mode)
function setDarkModeIcon() {
    themeIcon.innerHTML = '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    themeToggleBtn.setAttribute('title', 'Switch to Light Mode');
}

// Toggle Sidebar for Mobile
function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('show');
}

// Auto-grow textarea height
function autoGrowInput() {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight - 12) + 'px';
}

// Fetch configured AI & Telegram status from the server
async function fetchBackendStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            // Update Footer info
            statusProvider.textContent = data.provider;
            statusModel.textContent = data.model;
            headerModelBadge.textContent = `${data.provider} • ${data.model}`;
            
            // Telegram Bot Badge
            const tgBadge = statusTelegram;
            const tgText = tgBadge.querySelector('.status-tg-text');
            tgText.textContent = data.telegram_status;
            if (data.telegram_enabled) {
                tgBadge.className = 'status-value-tg active';
            } else {
                tgBadge.className = 'status-value-tg disabled';
            }
        }
    } catch (error) {
        console.error('Error fetching backend status:', error);
        statusProvider.textContent = 'Offline';
        statusModel.textContent = 'None';
        headerModelBadge.textContent = 'Offline Server';
    }
}

// Load conversations from LocalStorage and sync with server
async function loadConversations() {
    // 1. Initial load from LocalStorage for instant UI render
    const saved = localStorage.getItem('pocketstrike_conversations');
    if (saved) {
        try {
            conversations = JSON.parse(saved);
            const savedActiveId = localStorage.getItem('pocketstrike_active_id');
            if (savedActiveId && conversations.some(c => c.id === savedActiveId)) {
                activeConversationId = savedActiveId;
            } else if (conversations.length > 0) {
                activeConversationId = conversations[0].id;
            }
        } catch (e) {
            console.error('Error parsing conversations:', e);
            conversations = [];
        }
    }
    
    // 2. Fetch latest history from the server (local disk) to sync
    try {
        const response = await fetch('/api/history/load');
        if (response.ok) {
            const serverConversations = await response.json();
            if (serverConversations && serverConversations.length > 0) {
                conversations = serverConversations;
                
                // Set active conversation if not set or invalid
                const savedActiveId = localStorage.getItem('pocketstrike_active_id');
                if (savedActiveId && conversations.some(c => c.id === savedActiveId)) {
                    activeConversationId = savedActiveId;
                } else {
                    activeConversationId = conversations[0].id;
                }
                
                // Save back to LocalStorage to sync
                localStorage.setItem('pocketstrike_conversations', JSON.stringify(conversations));
                localStorage.setItem('pocketstrike_active_id', activeConversationId);
                renderAll();
            }
        }
    } catch (error) {
        console.error('Error loading history from server:', error);
    }
}

// Save conversations to LocalStorage and sync to server
async function saveConversations() {
    localStorage.setItem('pocketstrike_conversations', JSON.stringify(conversations));
    localStorage.setItem('pocketstrike_active_id', activeConversationId);
    
    // Sync to server background file storage
    try {
        await fetch('/api/history/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(conversations)
        });
    } catch (e) {
        console.error('Failed to sync history to server:', e);
    }
}

// Create a new empty chat conversation
function createNewChat(initialTitle = 'New Chat') {
    const newChat = {
        id: 'chat_' + Date.now(),
        title: initialTitle,
        messages: []
    };
    conversations.unshift(newChat);
    activeConversationId = newChat.id;
    saveConversations();
    renderAll();
    chatInput.focus();
    return newChat;
}

// Select a chat conversation
function selectConversation(id) {
    activeConversationId = id;
    saveConversations();
    renderAll();
    if (window.innerWidth <= 768) toggleSidebar();
}

// Delete a conversation
function deleteConversation(id, event) {
    if (event) event.stopPropagation();
    
    conversations = conversations.filter(c => c.id !== id);
    if (activeConversationId === id) {
        activeConversationId = conversations.length > 0 ? conversations[0].id : null;
    }
    saveConversations();
    renderAll();
}

// Rename conversation title
function renameConversation(id, event) {
    if (event) event.stopPropagation();
    const chat = conversations.find(c => c.id === id);
    if (!chat) return;

    const newTitle = prompt('Rename this chat:', chat.title);
    if (newTitle && newTitle.trim()) {
        chat.title = newTitle.trim();
        saveConversations();
        renderAll();
    }
}

// Clear all chats
function clearAllConversations() {
    if (confirm('Are you sure you want to clear all conversations?')) {
        conversations = [];
        activeConversationId = null;
        saveConversations();
        renderAll();
    }
}

// Fill textarea from suggested template card
function fillPrompt(promptText) {
    chatInput.value = promptText;
    autoGrowInput();
    chatInput.focus();
}

// Handle sending message
async function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isGenerating) return;

    // Clear input box
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Get or create active chat
    let activeChat = conversations.find(c => c.id === activeConversationId);
    if (!activeChat) {
        // Auto generate clean title based on first query
        const autoTitle = text.length > 25 ? text.substring(0, 25) + '...' : text;
        activeChat = createNewChat(autoTitle);
    }

    // Auto rename default chat title if first message
    if (activeChat.messages.length === 0 && activeChat.title === 'New Chat') {
        activeChat.title = text.length > 25 ? text.substring(0, 25) + '...' : text;
    }

    // Append User Message
    activeChat.messages.push({ role: 'user', content: text });
    saveConversations();
    renderAll();
    scrollToBottom();

    // Show Typing Indicator
    isGenerating = true;
    toggleSendButton();
    renderTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: activeChat.messages })
        });

        removeTypingIndicator();

        if (response.ok) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let done = false;
            let streamedText = "";
            
            // Add placeholder for assistant message
            const assistantMessageIndex = activeChat.messages.length;
            activeChat.messages.push({ role: 'assistant', content: "" });
            renderAll();
            
            // Access the target bubble element directly for speed
            const messageDivs = messagesContainer.querySelectorAll('.message.assistant');
            const lastMessageDiv = messageDivs[messageDivs.length - 1];
            const lastBubble = lastMessageDiv.querySelector('.message-bubble');
            
            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: !done });
                    streamedText += chunk;
                    
                    // Inspect for final history sync message
                    const syncIndex = streamedText.indexOf('\n[HISTORY_SYNC]:');
                    if (syncIndex !== -1) {
                        const syncData = streamedText.substring(syncIndex + 16);
                        streamedText = streamedText.substring(0, syncIndex);
                        try {
                            const updatedMessages = JSON.parse(syncData);
                            activeChat.messages = updatedMessages;
                        } catch (err) {
                            console.error("Failed to parse history sync:", err);
                        }
                        break;
                    }
                    
                    // Update active conversation text state
                    activeChat.messages[assistantMessageIndex].content = streamedText;
                    
                    // Render markdown structure directly and scroll down
                    lastBubble.innerHTML = parseMarkdown(streamedText);
                    scrollToBottom();
                }
            }
        } else {
            const errText = await response.text();
            activeChat.messages.push({ role: 'assistant', content: `⚠️ Error from server (Status ${response.status}): ${errText}` });
        }
    } catch (e) {
        removeTypingIndicator();
        activeChat.messages.push({ role: 'assistant', content: `⚠️ Network error: Could not reach Flask server. Check if Termux server is running. (${e.message})` });
    }

    isGenerating = false;
    toggleSendButton();
    saveConversations();
    renderAll();
    scrollToBottom();
}

// Toggle Send button disabled state
function toggleSendButton() {
    sendBtn.disabled = isGenerating;
}

// Render typing indicator block
function renderTypingIndicator() {
    const indicatorHtml = `
        <div class="message assistant" id="typingIndicator">
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12A10 10 0 0 1 12 2z"></path><path d="M12 8v4"></path><path d="M12 16h.01"></path></svg>
            </div>
            <div class="message-content-wrapper">
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', indicatorHtml);
    scrollToBottom();
}

// Remove typing indicator from layout
function removeTypingIndicator() {
    const element = document.getElementById('typingIndicator');
    if (element) element.remove();
}

// Scroll chat window to bottom
function scrollToBottom() {
    const chatWindow = document.querySelector('.chat-window');
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Master Render Function
function renderAll() {
    renderSidebarHistory();
    renderMessages();
}

// Render sidebar conversation items
function renderSidebarHistory() {
    sidebarHistory.innerHTML = '';
    
    if (conversations.length === 0) {
        sidebarHistory.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; padding: 1rem 0.25rem; text-align: center;">No history yet</div>';
        return;
    }

    conversations.forEach(chat => {
        const isActive = chat.id === activeConversationId;
        const item = document.createElement('div');
        item.className = `history-item ${isActive ? 'active' : ''}`;
        item.onclick = () => selectConversation(chat.id);
        
        item.innerHTML = `
            <div class="history-item-content">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                <span class="history-item-title">${escapeHtml(chat.title)}</span>
            </div>
            <div class="history-actions">
                <button class="history-action-btn" onclick="renameConversation('${chat.id}', event)" title="Rename">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                </button>
                <button class="history-action-btn" onclick="deleteConversation('${chat.id}', event)" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>
        `;
        sidebarHistory.appendChild(item);
    });
}

// Render active messages
function renderMessages() {
    const activeChat = conversations.find(c => c.id === activeConversationId);
    
    if (!activeChat || activeChat.messages.length === 0) {
        welcomeScreen.style.display = 'flex';
        messagesContainer.innerHTML = '';
        return;
    }

    welcomeScreen.style.display = 'none';
    messagesContainer.innerHTML = '';

    const msgs = activeChat.messages;
    let i = 0;
    while (i < msgs.length) {
        const msg = msgs[i];
        if (msg.role === 'system') {
            i++;
            continue;
        }

        const isToolCall = msg.content.startsWith('[TOOL_CALL:');
        const isToolResult = msg.content.startsWith('[TOOL_RESULT:');

        if (isToolCall) {
            const match = msg.content.match(/\[TOOL_CALL:\s*(\w+)\(([\s\S]*?)\)\s*\]/);
            const toolName = match ? match[1] : 'Tool';
            
            // Check if next message is the tool result
            let nextMsg = (i + 1 < msgs.length) ? msgs[i + 1] : null;
            let toolResultText = null;
            
            if (nextMsg && nextMsg.content.startsWith('[TOOL_RESULT:')) {
                toolResultText = nextMsg.content;
                i++; // Consume the result message
            }
            
            const toolDiv = document.createElement('div');
            toolDiv.className = 'tool-execution-block collapsed';
            
            if (toolResultText) {
                const resultMatch = toolResultText.match(/\[TOOL_RESULT:\s*\w+\s*output\]\n([\s\S]*)/);
                const rawOutput = resultMatch ? resultMatch[1].trim() : toolResultText;
                
                toolDiv.innerHTML = `
                    <div class="tool-execution-header" onclick="toggleToolBlock(this)">
                        <div class="tool-status-left">
                            <span class="tool-status-icon">🔧</span>
                            <span class="tool-status-text">Used tool <code class="tool-code">${escapeHtml(toolName)}</code></span>
                        </div>
                        <span class="tool-toggle-arrow">▶</span>
                    </div>
                    <div class="tool-execution-result">
                        <pre><code>${escapeHtml(rawOutput)}</code></pre>
                    </div>
                `;
            } else {
                const isRunning = (i === msgs.length - 1) && isGenerating;
                toolDiv.className = `tool-execution-block collapsed${isRunning ? ' running' : ''}`;
                
                toolDiv.innerHTML = `
                    <div class="tool-execution-header" ${isRunning ? '' : 'onclick="toggleToolBlock(this)"'}>
                        <div class="tool-status-left">
                            <span class="tool-status-icon">${isRunning ? '🔄' : '🔧'}</span>
                            <span class="tool-status-text">${isRunning ? 'Running' : 'Used'} tool <code class="tool-code">${escapeHtml(toolName)}</code>${isRunning ? '...' : ''}</span>
                        </div>
                        ${isRunning ? '<span class="tool-status-spinner"></span>' : '<span class="tool-toggle-arrow">▶</span>'}
                    </div>
                    ${isRunning ? '' : `
                    <div class="tool-execution-result">
                        <pre style="color: var(--text-muted); font-style: italic;">No output recorded</pre>
                    </div>`}
                `;
            }
            messagesContainer.appendChild(toolDiv);
            i++;
            continue;
        }

        if (isToolResult) {
            const resultMatch = msg.content.match(/\[TOOL_RESULT:\s*(\w+)\s*output\]\n([\s\S]*)/);
            const toolName = resultMatch ? resultMatch[1] : 'Tool';
            const rawOutput = resultMatch ? resultMatch[2].trim() : msg.content;
            
            const toolDiv = document.createElement('div');
            toolDiv.className = 'tool-execution-block collapsed';
            toolDiv.innerHTML = `
                <div class="tool-execution-header" onclick="toggleToolBlock(this)">
                    <div class="tool-status-left">
                        <span class="tool-status-icon">📥</span>
                        <span class="tool-status-text">Result from <code class="tool-code">${escapeHtml(toolName)}</code></span>
                    </div>
                    <span class="tool-toggle-arrow">▶</span>
                </div>
                <div class="tool-execution-result">
                    <pre><code>${escapeHtml(rawOutput)}</code></pre>
                </div>
            `;
            messagesContainer.appendChild(toolDiv);
            i++;
            continue;
        }

        // Render normal user/assistant message
        const isUser = msg.role === 'user';
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

        const avatarIcon = isUser 
            ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`
            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>`;

        const renderedContent = isUser ? escapeHtml(msg.content) : parseMarkdown(msg.content);

        msgDiv.innerHTML = `
            <div class="message-avatar">
                ${avatarIcon}
            </div>
            <div class="message-content-wrapper">
                <div class="message-bubble">
                    ${renderedContent}
                </div>
                <div class="message-actions">
                    <button class="msg-action-btn" onclick="copyMessageText(this)" title="Copy Message">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    </button>
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        i++;
    }
}

// Toggle collapsible tool block output
function toggleToolBlock(header) {
    const block = header.closest('.tool-execution-block');
    if (block) {
        block.classList.toggle('collapsed');
    }
}

// Copy raw message text
function copyMessageText(btn) {
    const wrapper = btn.closest('.message-content-wrapper');
    const bubble = wrapper.querySelector('.message-bubble');
    // Get innerText so we copy the rendered plain text, not HTML
    const text = bubble.innerText;

    navigator.clipboard.writeText(text).then(() => {
        const origSvg = btn.innerHTML;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        setTimeout(() => {
            btn.innerHTML = origSvg;
        }, 1500);
    });
}

// Copy Code Block Helper
function copyCodeBlock(btn) {
    const pre = btn.closest('.code-header').nextElementSibling;
    const code = pre.querySelector('code').innerText;
    
    navigator.clipboard.writeText(code).then(() => {
        const origText = btn.innerText;
        btn.innerText = 'Copied!';
        btn.style.color = 'var(--accent-green)';
        btn.style.borderColor = 'var(--accent-green)';
        setTimeout(() => {
            btn.innerText = origText;
            btn.style.color = '';
            btn.style.borderColor = '';
        }, 2000);
    });
}

// Simple HTML escaping to prevent XSS
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Regex-based Markdown Parser
function parseMarkdown(text) {
    if (!text) return "";

    let html = text;

    // 1. Parse Code Blocks ```code```
    // Store blocks to prevent parsing inside them later
    const codeBlocks = [];
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        const placeholder = `__CODE_BLOCK_PLACEHOLDER_${codeBlocks.length}__`;
        const escapedCode = escapeHtml(code.trim());
        const header = `
            <div class="code-header">
                <span>${lang.toUpperCase() || 'CODE'}</span>
                <button class="copy-code-btn" onclick="copyCodeBlock(this)">Copy</button>
            </div>
        `;
        codeBlocks.push(`${header}<pre><code>${escapedCode}</code></pre>`);
        return placeholder;
    });

    // 2. Escape HTML outside of placeholders to prevent rendering arbitrary tags
    // First let's identify the placeholders so we don't escape them
    const placeholderRegex = /__CODE_BLOCK_PLACEHOLDER_\d+__/g;
    const segments = html.split(placeholderRegex);
    const matches = html.match(placeholderRegex) || [];
    
    let escapedHtml = "";
    for (let i = 0; i < segments.length; i++) {
        escapedHtml += escapeHtml(segments[i]);
        if (i < matches.length) {
            escapedHtml += matches[i];
        }
    }
    html = escapedHtml;

    // 3. Parse bold **text**
    html = html.replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>');

    // 4. Parse inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 5. Parse unordered lists (lines starting with - or * )
    // We split by newline, parse lists, and join back
    const lines = html.split('\n');
    let inList = false;
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        // Check if line starts with placeholder - don't process as list
        if (line.startsWith('__CODE_BLOCK_PLACEHOLDER_')) continue;

        if (line.startsWith('- ') || line.startsWith('* ')) {
            const listContent = line.substring(2);
            let listLine = `<li>${listContent}</li>`;
            if (!inList) {
                listLine = '<ul>' + listLine;
                inList = true;
            }
            lines[i] = listLine;
        } else {
            if (inList) {
                lines[i] = '</ul>' + lines[i];
                inList = false;
            }
        }
    }
    if (inList) {
        lines[lines.length - 1] += '</ul>';
    }
    html = lines.join('\n');

    // 6. Convert newlines to <br> except inside tags that don't need it
    // Splitting by lines is cleaner
    html = html.split('\n').map(line => {
        // If it starts with list tags or header or placeholder, keep as is
        if (line.match(/^<\/?(ul|li|pre|code|div)/) || line.includes('__CODE_BLOCK_PLACEHOLDER_')) {
            return line;
        }
        return line + '<br>';
    }).join('\n');

    // Clean up empty double <br> or trailing <br>
    html = html.replace(/(<br>){2,}/g, '<br><br>');

    // 7. Re-inject Code Blocks
    for (let i = 0; i < codeBlocks.length; i++) {
        html = html.replace(`__CODE_BLOCK_PLACEHOLDER_${i}__`, codeBlocks[i]);
    }

    // 8. Style tool calls and tool outputs
    html = html.replace(/\[TOOL_CALL:\s*(\w+)\(([\s\S]*?)\)\s*\]/g, (match, tool, args) => {
        return `
            <div class="tool-execution-block collapsed">
                <div class="tool-execution-header" onclick="toggleToolBlock(this)">
                    <div class="tool-status-left">
                        <span class="tool-status-icon">🔧</span>
                        <span class="tool-status-text">Used tool <code class="tool-code">${escapeHtml(tool)}</code></span>
                    </div>
                    <span class="tool-toggle-arrow">▶</span>
                </div>
                <div class="tool-execution-result">
                    <pre style="color: var(--text-muted); font-style: italic;">No output recorded</pre>
                </div>
            </div>
        `;
    });

    html = html.replace(/\[TOOL_RESULT:\s*(\w+)\s*output\]\n([\s\S]*?)(?=(?:<div class="tool-execution-block"|<br><br>|\Z))/g, (match, tool, output) => {
        const cleanOutput = output
            .replace(/<br>/g, '\n')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>');
        return `
            <div class="tool-execution-block collapsed">
                <div class="tool-execution-header" onclick="toggleToolBlock(this)">
                    <div class="tool-status-left">
                        <span class="tool-status-icon">📥</span>
                        <span class="tool-status-text">Result from <code class="tool-code">${escapeHtml(tool)}</code></span>
                    </div>
                    <span class="tool-toggle-arrow">▶</span>
                </div>
                <div class="tool-execution-result">
                    <pre><code>${cleanOutput.trim()}</code></pre>
                </div>
            </div>
        `;
    });

    return html;
}

// Background Polling for Chat History changes (e.g. background alerts)
let lastHistoryLength = 0;
async function pollHistoryChanges() {
    if (isGenerating) return; // Skip polling if streaming
    
    try {
        const response = await fetch('/api/history/load');
        if (response.ok) {
            const serverConversations = await response.json();
            if (serverConversations && serverConversations.length > 0) {
                const serverMessages = serverConversations[0].messages;
                
                // Set initial length on first poll
                if (lastHistoryLength === 0) {
                    lastHistoryLength = serverMessages.length;
                    return;
                }
                
                // If history grew, update local memory and re-render
                if (serverMessages.length !== lastHistoryLength) {
                    lastHistoryLength = serverMessages.length;
                    conversations = serverConversations;
                    
                    // Update active conversation reference
                    const activeChat = conversations.find(c => c.id === activeConversationId);
                    if (activeChat) {
                        localStorage.setItem('pocketstrike_conversations', JSON.stringify(conversations));
                        renderAll();
                        scrollToBottom();
                    }
                }
            }
        }
    } catch (err) {
        console.error("Error polling history changes:", err);
    }
}
// Run poll every 8 seconds
setInterval(pollHistoryChanges, 8000);

// Open/Close MCP Modal
function openMcpModal() {
    mcpName.value = "";
    mcpUrl.value = "";
    mcpModal.classList.add('show');
}

function closeMcpModal() {
    mcpModal.classList.remove('show');
}

// Load and render MCP connections
async function loadMcpConnections() {
    try {
        const response = await fetch('/api/mcp/list');
        if (response.ok) {
            const servers = await response.json();
            renderMcpList(servers);
        }
    } catch (err) {
        console.error("Error loading MCP connections:", err);
    }
}

// Render the MCP connections list in the sidebar
function renderMcpList(servers) {
    if (!sidebarMcpList) return;
    
    if (servers.length === 0) {
        sidebarMcpList.innerHTML = `
            <div style="font-size: 0.8rem; color: var(--text-muted); padding: 0.5rem 0.25rem;">
                No remote servers connected.
            </div>
        `;
        return;
    }
    
    sidebarMcpList.innerHTML = servers.map(srv => `
        <div class="mcp-item">
            <div class="mcp-item-info">
                <span class="mcp-status-dot ${srv.status === 'connected' ? 'connected' : 'offline'}" title="Status: ${srv.status}"></span>
                <span style="font-weight: 500;">${srv.name}</span>
            </div>
            <button class="mcp-delete-btn" onclick="handleRemoveMcp('${srv.name}')" title="Disconnect server">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `).join('');
}

// Add new MCP connection
async function handleAddMcp() {
    const name = mcpName.value.trim();
    const url = mcpUrl.value.trim();
    
    if (!name || !url) {
        alert("Please enter both a name and server URL.");
        return;
    }
    
    mcpSubmitBtn.disabled = true;
    mcpSubmitBtn.innerText = "Connecting...";
    
    try {
        const response = await fetch('/api/mcp/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url })
        });
        
        const result = await response.json();
        if (response.ok) {
            closeMcpModal();
            loadMcpConnections();
            alert(`Successfully connected to '${name}'! Loaded ${result.tools_count} remote tools.`);
            fetchBackendStatus();
        } else {
            alert("Connection error: " + (result.error || "Unknown error"));
        }
    } catch (err) {
        alert("Network error: Failed to reach backend.");
        console.error(err);
    } finally {
        mcpSubmitBtn.disabled = false;
        mcpSubmitBtn.innerText = "Connect";
    }
}

// Remove MCP connection
async function handleRemoveMcp(name) {
    if (!confirm(`Are you sure you want to disconnect remote server '${name}'?`)) return;
    
    try {
        const response = await fetch('/api/mcp/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        if (response.ok) {
            loadMcpConnections();
            fetchBackendStatus();
        } else {
            const err = await response.json();
            alert("Error removing server: " + (err.error || "Unknown error"));
        }
    } catch (err) {
        console.error("Error removing MCP:", err);
    }
}

// Run MCP connection health check every 15 seconds to update the status dot
setInterval(loadMcpConnections, 15000);
