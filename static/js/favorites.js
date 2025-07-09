document.addEventListener('DOMContentLoaded', function() {
    // 初始化图片放大功能
    window.openImageModal = initImageModal();
    
    const gallery = document.getElementById('favorites-gallery');
    const loading = document.getElementById('loading');
    const noFavorites = document.getElementById('no-favorites');
    const errorMessage = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');

    // 加载收藏的猫咪
    async function loadFavorites() {
        loading.style.display = 'block';
        noFavorites.style.display = 'none';
        errorMessage.style.display = 'none';

        try {
            const response = await fetch('/api/favorites');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.success && data.favorites.length > 0) {
                gallery.innerHTML = '';
                data.favorites.forEach(favorite => {
                    const galleryItem = createGalleryItem(favorite);
                    gallery.appendChild(galleryItem);
                });
            } else if (data.favorites.length === 0) {
                noFavorites.style.display = 'block';
            } else {
                errorMessage.style.display = 'block';
            }
        } catch (error) {
            console.error('加载收藏失败:', error);
            errorMessage.style.display = 'block';
        } finally {
            loading.style.display = 'none';
        }
    }

    // 创建图库项目
    function createGalleryItem(favorite) {
        const item = document.createElement('div');
        item.className = 'gallery-item';

        // 从URL中提取猫咪名字（简单实现）
        const urlParts = favorite.url.split('/');
        const catName = urlParts[urlParts.length - 2] || '未知';

        const catNameElement = document.createElement('p');
        catNameElement.className = 'cat-name';
        catNameElement.textContent = decodeURIComponent(catName);

        const img = document.createElement('img');
        img.src = favorite.url;
        img.alt = `收藏的猫咪`;
        img.loading = 'lazy';

        const actions = document.createElement('div');
        actions.className = 'actions';

        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-btn';
        removeBtn.innerHTML = '🗑️ 移除'; // 移除按钮
        removeBtn.title = '从收藏中移除';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            removeFavorite(favorite.id, item);
        };

        actions.appendChild(removeBtn);
        item.appendChild(catNameElement);
        item.appendChild(img);
        item.appendChild(actions);

        // 添加图片点击放大功能
        addImageClickHandler(img, favorite.url);

        return item;
    }

    // 从收藏中移除猫咪
    async function removeFavorite(favoriteId, element) {
        try {
            const response = await fetch('/api/remove_favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: favoriteId })
            });
            const data = await response.json();

            if (data.success) {
                element.remove();
                showNotification('已从收藏中移除');
                
                // 检查是否还有收藏
                if (gallery.children.length === 0) {
                    noFavorites.style.display = 'block';
                }
            } else {
                showNotification('移除失败', 'error');
            }
        } catch (error) {
            console.error('移除收藏时出错:', error);
            showNotification('移除时发生网络错误', 'error');
        }
    }

    // 重试加载
    if (retryBtn) {
        retryBtn.addEventListener('click', loadFavorites);
    }

    // 初始加载
    loadFavorites();
});
