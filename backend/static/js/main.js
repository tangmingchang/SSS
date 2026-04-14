let currentSessionId = null;
let currentScript = null;
let currentActions = null;

// 页面加载时获取动作库
window.addEventListener('DOMContentLoaded', () => {
    loadActionLibrary();
});

async function loadActionLibrary() {
    try {
        const response = await fetch('/api/action_library');
        const data = await response.json();
        
        if (data.success) {
            const libraryDiv = document.getElementById('action_library');
            libraryDiv.innerHTML = '';
            
            data.emotions.forEach(emotion => {
                const info = data.emotion_info[emotion];
                const item = document.createElement('div');
                item.className = 'action-library-item';
                item.innerHTML = `
                    <strong>${emotion}</strong>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        ${info.description}
                    </div>
                `;
                libraryDiv.appendChild(item);
            });
        }
    } catch (error) {
        console.error('加载动作库失败:', error);
    }
}

async function generateScript() {
    const theme = document.getElementById('theme').value;
    const character = document.getElementById('character').value;
    const length = document.getElementById('length').value;
    const apiKey = document.getElementById('api_key').value;
    
    if (!theme) {
        showError('请输入主题');
        return;
    }
    
    showLoading();
    hideResults();
    
    try {
        const response = await fetch('/api/generate_script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                theme: theme,
                character: character,
                length: parseInt(length),
                api_key: apiKey || null
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            currentScript = data.script;
            currentActions = data.action_sequence;
            
            displayScript(data.script);
            showSuccess('剧本生成成功！');
        } else {
            showError(data.error || '生成失败');
        }
    } catch (error) {
        showError('请求失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayScript(script) {
    const scriptDiv = document.getElementById('script_content');
    scriptDiv.innerHTML = '';
    
    const title = document.createElement('h3');
    title.textContent = script.title || '剧本';
    scriptDiv.appendChild(title);
    
    script.scenes.forEach((scene, index) => {
        const sceneCard = document.createElement('div');
        sceneCard.className = 'scene-card';
        
        sceneCard.innerHTML = `
            <h3>场景 ${scene.scene_number}: ${scene.description}</h3>
            <div>
                <strong>情感:</strong>
                <span class="emotion-badge emotion-${scene.emotion}">${scene.emotion}</span>
                <span style="margin-left: 15px;">持续时间: ${scene.duration}秒</span>
            </div>
            <div style="margin-top: 10px;">
                <strong>动作序列:</strong>
                ${scene.actions.map(action => 
                    `<span class="action-item">${action}</span>`
                ).join('')}
            </div>
        `;
        
        scriptDiv.appendChild(sceneCard);
    });
    
    document.getElementById('script_result').style.display = 'block';
}

async function captureMotion() {
    const fileInput = document.getElementById('video_file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('请选择视频文件');
        return;
    }
    
    showLoading();
    hideResults();
    
    const formData = new FormData();
    formData.append('video', file);
    
    try {
        const response = await fetch('/api/capture_motion', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            displayMotionResult(data);
            showSuccess('动作捕捉成功！');
        } else {
            showError(data.error || '捕捉失败');
        }
    } catch (error) {
        showError('请求失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayMotionResult(data) {
    const motionDiv = document.getElementById('motion_content');
    motionDiv.innerHTML = `
        <div class="success">
            <p><strong>成功捕捉动作！</strong></p>
            <p>帧数: ${data.frames}</p>
            <p>BVH文件已生成</p>
        </div>
    `;
    
    document.getElementById('motion_result').style.display = 'block';
}

async function labelActions() {
    if (!currentActions) {
        showError('请先生成剧本');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch('/api/label_actions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action_sequence: currentActions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayLabeledActions(data.labeled_actions);
            showSuccess('标签添加成功！');
        } else {
            showError(data.error || '标签添加失败');
        }
    } catch (error) {
        showError('请求失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayLabeledActions(actions) {
    const actionsDiv = document.getElementById('actions_content');
    actionsDiv.innerHTML = '';
    
    actions.forEach((action, index) => {
        const actionCard = document.createElement('div');
        actionCard.className = 'scene-card';
        
        const emotion = action.emotion || '未知';
        const actionName = action.action_name || '未知';
        const similarity = (action.similarity || 0).toFixed(3);
        
        actionCard.innerHTML = `
            <h3>动作 ${index + 1}: ${action.action}</h3>
            <div>
                <strong>动作名称:</strong> ${actionName}
                <span class="emotion-badge emotion-${emotion}">${emotion}</span>
                <span style="margin-left: 15px;">相似度: ${similarity}</span>
            </div>
        `;
        
        actionsDiv.appendChild(actionCard);
    });
    
    document.getElementById('actions_result').style.display = 'block';
}

function downloadScript() {
    if (!currentSessionId) {
        showError('没有可下载的文件');
        return;
    }
    
    window.location.href = `/api/download/${currentSessionId}?type=script`;
}

function downloadBVH() {
    if (!currentSessionId) {
        showError('没有可下载的文件');
        return;
    }
    
    window.location.href = `/api/download/${currentSessionId}?type=bvh`;
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function hideResults() {
    document.getElementById('script_result').style.display = 'none';
    document.getElementById('motion_result').style.display = 'none';
    document.getElementById('actions_result').style.display = 'none';
}

function showError(message) {
    const content = document.querySelector('.content');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    content.insertBefore(errorDiv, content.firstChild);
    
    setTimeout(() => errorDiv.remove(), 5000);
}

function showSuccess(message) {
    const content = document.querySelector('.content');
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    content.insertBefore(successDiv, content.firstChild);
    
    setTimeout(() => successDiv.remove(), 3000);
}








