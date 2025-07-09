// 图片放大模态框功能
function initImageModal() {
    const modalOverlay = document.getElementById('modal-overlay');
    const modalImage = document.getElementById('modal-image');
    const modalClose = document.getElementById('modal-close');
    const modalSaveBtn = document.getElementById('modal-save-btn');
    
    if (!modalOverlay || !modalImage || !modalClose) {
        console.warn('模态框元素未找到');
        return;
    }
    
    let currentImageUrl = '';
    
    // 关闭模态框
    function closeModal() {
        modalOverlay.classList.remove('show');
        modalOverlay.style.display = 'none';
        currentImageUrl = '';
        document.body.style.overflow = 'auto'; // 恢复滚动
    }
    
    // 打开模态框
    function openModal(imageUrl) {
        if (!imageUrl) return;
        
        currentImageUrl = imageUrl;
        modalImage.src = imageUrl;
        modalOverlay.style.display = 'flex';
        modalOverlay.classList.add('show');
        document.body.style.overflow = 'hidden'; // 禁止滚动
        
        // 更新收藏按钮状态
        if (modalSaveBtn) {
            checkIfSaved(imageUrl);
        }
    }
    
    // 检查图片是否已收藏
    async function checkIfSaved(imageUrl) {
        try {
            const response = await fetch('/api/favorites');
            const data = await response.json();
            
            if (data.success) {
                const isSaved = data.favorites.some(fav => fav.url === imageUrl);
                if (isSaved) {
                    modalSaveBtn.classList.add('saved');
                    modalSaveBtn.innerHTML = '✅ 已收藏';
                    modalSaveBtn.disabled = true;
                } else {
                    modalSaveBtn.classList.remove('saved');
                    modalSaveBtn.innerHTML = '💖 保存到收藏';
                    modalSaveBtn.disabled = false;
                }
            }
        } catch (error) {
            console.error('检查收藏状态失败:', error);
        }
    }
    
    // 收藏图片
    async function saveCurrentImage() {
        if (!currentImageUrl) return;
        
        try {
            const response = await fetch('/api/save_cat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_url: currentImageUrl })
            });
            const data = await response.json();
            
            if (data.success) {
                showNotification('收藏成功！');
                modalSaveBtn.classList.add('saved');
                modalSaveBtn.innerHTML = '✅ 已收藏';
                modalSaveBtn.disabled = true;
            } else if (data.error === 'Already saved') {
                showNotification('已经收藏过了');
                modalSaveBtn.classList.add('saved');
                modalSaveBtn.innerHTML = '✅ 已收藏';
                modalSaveBtn.disabled = true;
            } else {
                showNotification('收藏失败', 'error');
            }
        } catch (error) {
            console.error('收藏时出错:', error);
            showNotification('收藏时发生网络错误', 'error');
        }
    }
    
    // 绑定事件
    modalClose.onclick = closeModal;
    modalOverlay.onclick = (e) => {
        if (e.target === modalOverlay) {
            closeModal();
        }
    };
    
    if (modalSaveBtn) {
        modalSaveBtn.onclick = saveCurrentImage;
    }
    
    // ESC键关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modalOverlay.classList.contains('show')) {
            closeModal();
        }
    });
    
    // 返回打开模态框的函数，供其他模块使用
    return openModal;
}

// 为图片元素添加点击放大功能
function addImageClickHandler(imgElement, imageUrl) {
    if (!imgElement || !imageUrl) return;
    
    imgElement.style.cursor = 'pointer';
    imgElement.onclick = (e) => {
        e.stopPropagation();
        if (window.openImageModal) {
            window.openImageModal(imageUrl);
        }
    };
}

// 显示通知
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // 3秒后自动隐藏
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}
