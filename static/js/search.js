document.addEventListener('DOMContentLoaded', function() {
    // 初始化图片放大功能
    window.openImageModal = initImageModal();
    
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchResults = document.getElementById('search-results');
    const searchMessage = document.getElementById('search-message');

    // 执行搜索
    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            searchMessage.textContent = '请输入要搜索的名字。';
            searchMessage.className = 'message-indicator info';
            searchResults.innerHTML = '';
            return;
        }

        searchMessage.textContent = '正在搜索...';
        searchMessage.className = 'message-indicator info';
        searchResults.innerHTML = '';

        try {
            const response = await fetch(`/api/search_cats?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.success && data.cats.length > 0) {
                searchMessage.textContent = `🎉 找到了 ${data.count} 张图片。`;
                searchMessage.className = 'message-indicator success';
                data.cats.forEach(cat => {
                    const galleryItem = createGalleryItem(cat);
                    searchResults.appendChild(galleryItem);
                });
            } else if (data.cats.length === 0) {
                searchMessage.textContent = '😿 没有找到符合条件的猫咪。';
                searchMessage.className = 'message-indicator info';
            } else {
                searchMessage.textContent = '❌ 搜索失败，请稍后重试。';
                searchMessage.className = 'message-indicator error';
            }
        } catch (error) {
            console.error('搜索时出错:', error);
            searchMessage.textContent = '😿 搜索时发生网络错误。';
            searchMessage.className = 'message-indicator error';
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

    // 事件监听
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            performSearch();
        }
    });
});
