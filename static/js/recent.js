document.addEventListener('DOMContentLoaded', function() {
    // 初始化图片放大功能
    window.openImageModal = initImageModal();
    
    const gallery = document.getElementById('cat-gallery');
    const loading = document.getElementById('loading');

    let isLoading = false;

    // 加载最近上传的猫咪
    async function loadRecentCats() {
        if (isLoading) return;
        isLoading = true;
        loading.style.display = 'block';

        try {
            const response = await fetch('/api/source_cats');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.success && data.cats.length > 0) {
                data.cats.forEach(cat => {
                    const galleryItem = createGalleryItem(cat);
                    gallery.appendChild(galleryItem);
                });
            } else if (data.cats.length === 0) {
                loading.textContent = '没有更多猫咪了';
            } else {
                loading.textContent = '加载失败，请稍后重试';
            }
        } catch (error) {
            console.error('无法加载最近的猫咪:', error);
            loading.textContent = '加载出错';
        } finally {
            isLoading = false;
            // 在此场景下，我们一次性加载所有，所以直接隐藏加载指示器
            loading.style.display = 'none';
        }
    }

    // 创建图库项目
    function createGalleryItem(cat) {
        const item = document.createElement('div');
        item.className = 'gallery-item';

        const catName = document.createElement('p');
        catName.className = 'cat-name';
        catName.textContent = cat.name;

        const img = document.createElement('img');
        img.src = cat.url;
        img.alt = `一只名叫 ${cat.name} 的猫`;
        img.loading = 'lazy';

        const actions = document.createElement('div');
        actions.className = 'actions';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'save-btn';
        saveBtn.innerHTML = '❤️ 喜欢'; // 改为喜欢按钮
        saveBtn.title = '收藏';
        saveBtn.onclick = () => saveCat(cat.url, saveBtn);

        // 检查是否已经收藏
        checkIfSaved(cat.url, saveBtn);

        actions.appendChild(saveBtn);
        item.appendChild(catName);
        item.appendChild(img);
        item.appendChild(actions);

        // 添加图片点击放大功能
        addImageClickHandler(img, cat.url);

        return item;
    }

    // 检查图片是否已收藏
    async function checkIfSaved(imageUrl, button) {
        try {
            const response = await fetch('/api/favorites');
            const data = await response.json();
            
            if (data.success) {
                const isSaved = data.favorites.some(fav => fav.url === imageUrl);
                if (isSaved) {
                    button.classList.add('saved');
                    button.innerHTML = '✅ 已收藏';
                    button.disabled = true;
                } else {
                    button.classList.remove('saved');
                    button.innerHTML = '❤️ 喜欢';
                    button.disabled = false;
                }
            }
        } catch (error) {
            console.error('检查收藏状态失败:', error);
        }
    }

    // 保存猫咪到收藏
    async function saveCat(imageUrl, button) {
        try {
            const response = await fetch('/api/save_cat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_url: imageUrl })
            });
            const data = await response.json();

            if (data.success) {
                showNotification('收藏成功！');
                button.classList.add('saved');
                button.disabled = true;
            } else if (data.error === 'Already saved') {
                showNotification('已经收藏过了');
                button.classList.add('saved');
                button.disabled = true;
            } else {
                showNotification('收藏失败', 'error');
            }
        } catch (error) {
            console.error('收藏时出错:', error);
            showNotification('收藏时发生网络错误', 'error');
        }
    }

    // 显示通知
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 初始加载
    loadRecentCats();
});
