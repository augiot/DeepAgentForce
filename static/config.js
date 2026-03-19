/**
 * 配置管理模块
 * 负责加载、保存和验证模型配置
 * 适配扁平化配置结构 (无嵌套组)
 */

// 动态获取后端地址
// 策略：1. 先尝试从 ?api= 参数获取
//       2. 如果没有参数，页面加载时自动从当前域名请求 server_info 接口获取
//       3. 如果 server_info 失败，则使用当前域名作为 API 地址

let _serverInfo = null;

// 页面加载时自动获取服务器信息
async function initServerInfo() {
    try {
        const currentBase = `${window.location.protocol}//${window.location.host}`;
        const response = await fetch(`${currentBase}/api/server_info`, {
            signal: AbortSignal.timeout(3000)
        });
        if (response.ok) {
            _serverInfo = await response.json();
            console.log('✅ 获取到服务器信息:', _serverInfo);
        }
    } catch (e) {
        console.warn('⚠️ 无法获取 server_info，使用默认配置:', e.message);
    }
}

// 同步版本 - 优先使用 URL 参数，否则使用已获取的 server_info
const getApiBase = () => {
    // 优先使用 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const apiParam = urlParams.get('api');
    if (apiParam) return apiParam;
    
    // 使用 server_info
    if (_serverInfo && _serverInfo.api_base) return _serverInfo.api_base;
    
    // 回退：假设后端在当前服务器的 8000 端口
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
};

const getWsBase = () => {
    // 优先使用 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const apiParam = urlParams.get('api');
    if (apiParam) return apiParam.replace('/api', '') + '/ws/stream';
    
    // 使用 server_info
    if (_serverInfo && _serverInfo.ws_base) return _serverInfo.ws_base;
    
    // 回退：假设后端在当前服务器的 8000 端口
    return `ws://${window.location.hostname}:8000/ws/stream`;
};

// 页面加载时自动获取 server_info
initServerInfo();

// 暴露给全局
window.getApiBase = getApiBase;
window.getWsBase = getWsBase;

// DOM ID 到 配置文件 Key 的映射
// 格式: { HTML元素ID : 后端配置Key }
const FIELD_MAPPING = {
    // LLM 配置
    'llmApiKey': 'LLM_API_KEY',
    'llmUrl': 'LLM_URL',
    'llmModel': 'LLM_MODEL',
    
    // 搜索配置
    'tavilyApiKey': 'TAVILY_API_KEY',
    
    // Firecrawl 配置
    'firecrawlApiKey': 'FIRECRAWL_API_KEY',
    'firecrawlUrl': 'FIRECRAWL_URL',
    
    // Embedding 配置
    'embeddingApiKey': 'EMBEDDING_API_KEY',
    'embeddingUrl': 'EMBEDDING_URL',
    'embeddingModel': 'EMBEDDING_MODEL'
};

// ==================== 工具函数 ====================

// 安全调用全局 Toast
function safeShowToast(message, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        console.log(`[${type}] ${message}`);
        // 如果没有全局 toast，可以使用简单的 alert 作为回退，或者什么都不做
        if (type === 'error') alert(message);
    }
}

// ==================== 加载配置 ====================

async function loadConfig() {
    try {
        const response = await fetch(`${window.getApiBase()}/config`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 确保 data.config 存在
        if (!data.success || !data.config) {
            console.log('⚠️ 未找到有效配置或配置为空');
            return;
        }

        const config = data.config; // 扁平化对象

        // 遍历映射表填充数据
        for (const [domId, configKey] of Object.entries(FIELD_MAPPING)) {
            const element = document.getElementById(domId);
            if (element) {
                // 如果配置中有值则填充，否则保持原样或清空
                element.value = config[configKey] || '';
            }
        }
        
        console.log('✅ 配置加载完成');
    } catch (error) {
        console.error('❌ 加载配置失败:', error);
        safeShowToast('加载配置失败，请检查后端服务', 'error');
    }
}

// ==================== 保存配置 ====================

async function saveConfig() {
    const saveButton = document.getElementById('saveConfigBtn');
    if (saveButton) {
        saveButton.disabled = true;
        saveButton.textContent = '保存中...';
    }
    
    try {
        // 1. 收集数据
        const configToSave = {};
        for (const [domId, configKey] of Object.entries(FIELD_MAPPING)) {
            const element = document.getElementById(domId);
            if (element && element.value.trim() !== '') {
                configToSave[configKey] = element.value.trim();
            }
        }
        
        // 2. 验证必填项 (根据需求调整)
        const requiredKeys = ['LLM_API_KEY', 'LLM_URL', 'LLM_MODEL'];
        const missing = requiredKeys.filter(key => !configToSave[key]);
        
        if (missing.length > 0) {
            throw new Error(`缺少必填项: ${missing.join(', ')}`);
        }
        
        // 3. 发送请求
        const response = await fetch(`${window.getApiBase()}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configToSave)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || '保存请求失败');
        }
        
        const result = await response.json();
        
        safeShowToast('配置已保存！新的对话将使用新配置', 'success');
        console.log('✅ 保存成功:', result);
        
    } catch (error) {
        console.error('❌ 保存配置失败:', error);
        safeShowToast(error.message, 'error');
    } finally {
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.textContent = '保存配置';
        }
    }
}

// ==================== 初始化 ====================

function initConfigPage() {
    // 绑定保存按钮
    const saveButton = document.getElementById('saveConfigBtn');
    if (saveButton) {
        // 移除旧的监听器（防止重复绑定，虽然后面是直接执行，但习惯上要注意）
        saveButton.removeEventListener('click', saveConfig);
        saveButton.addEventListener('click', saveConfig);
    }
    
    // 加载数据
    loadConfig();
}

// 确保 DOM 加载完毕后执行
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initConfigPage);
} else {
    initConfigPage();
}

// 暴露给全局 (方便控制台调试或 HTML onclick 调用)
window.loadConfig = loadConfig;
window.saveConfig = saveConfig;