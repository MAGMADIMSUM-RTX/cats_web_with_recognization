// 全局变量
let catImages = [];
let likedImages = new Set();
let isLoading = false;
let hasError = false;
let selectedImage = '';
let selectedFiles = [];

// DOM 元素
let catContainer, loadMoreBtn, loadingIndicator, errorMessage, modalOverlay, modalImage, notification;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化图片放大功能
    window.openImageModal = initImageModal();
    
    const gallery = document.getElementById('cat-gallery');
    const loading = document.getElementById('loading');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const catNameInput = document.getElementById('cat-name-input');
    const previewContainer = document.getElementById('preview-container');
    const uploadProgress = document.getElementById('upload-progress');
    const uploadProgressBar = document.getElementById('upload-progress-bar');
    const cancelUploadBtn = document.getElementById('cancel-upload-btn');
    const cancelUploadBtnProgress = document.getElementById('cancel-upload-btn-progress');
    const recognizeBtn = document.getElementById('recognize-btn');


    let isLoading = false;
    let currentRequest = null; // 用于中止上传
    let page = 0;
    const limit = 10;
    let noMoreCats = false;

    // 加载猫咪
    async function loadCats() {
        if (isLoading || noMoreCats) return;
        isLoading = true;
        loading.style.display = 'block';

        try {
            const response = await fetch(`/api/cats?count=${limit}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.success && data.cats.length > 0) {
                data.cats.forEach(cat => {
                    const galleryItem = createGalleryItem(cat);
                    gallery.appendChild(galleryItem);
                });
                page++;
            } else {
                loading.textContent = '没有更多猫咪了';
                noMoreCats = true;
                window.removeEventListener('scroll', handleScroll);
            }
        } catch (error) {
            console.error('无法加载猫咪:', error);
            loading.textContent = '加载失败，请稍后重试';
        } finally {
            isLoading = false;
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
        saveBtn.onclick = (e) => {
            e.stopPropagation();
            saveCat(cat.url, saveBtn);
        };

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

    // 保存猫咪
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

    // 滚动加载
    function handleScroll() {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
            loadCats();
        }
    }

    // 文件预览
    if(fileInput) {
        fileInput.addEventListener('change', () => {
            previewContainer.innerHTML = '';
            const files = fileInput.files;
            if (files.length > 0) {
                previewContainer.style.display = 'flex';
                Array.from(files).forEach(file => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const previewItem = document.createElement('div');
                        previewItem.className = 'preview-item';
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        previewItem.appendChild(img);
                        previewContainer.appendChild(previewItem);
                    };
                    reader.readAsDataURL(file);
                });
            } else {
                previewContainer.style.display = 'none';
            }
        });
    }

    // 表单提交
    if(uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const files = fileInput.files;
            const catName = catNameInput.value.trim();

            if (files.length === 0) {
                showNotification('请选择要上传的图片', 'error');
                return;
            }
            if (!catName) {
                showNotification('请输入猫咪的名字', 'error');
                return;
            }

            const formData = new FormData();
            for (const file of files) {
                formData.append('files', file);
            }
            formData.append('cat_name', catName);

            uploadProgress.style.display = 'block';
            uploadProgressBar.style.width = '0%';

            try {
                const xhr = new XMLHttpRequest();
                currentRequest = xhr;

                xhr.open('POST', '/api/upload_cats', true);

                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        uploadProgressBar.style.width = percentComplete + '%';
                    }
                };

                xhr.onload = () => {
                    if (xhr.status === 200) {
                        const data = JSON.parse(xhr.responseText);
                        if (data.success) {
                            showNotification(`成功上传 ${data.uploaded_count} 张图片！`);
                            resetUploadForm();
                            // 隐藏上传区域，显示图库
                            document.getElementById('upload-section').style.display = 'none';
                            gallery.style.display = 'grid';
                            // 刷新主页内容
                            gallery.innerHTML = '';
                            page = 0;
                            noMoreCats = false;
                            loadCats();
                        } else {
                            showNotification(data.error || '上传失败', 'error');
                        }
                    } else {
                        showNotification(`上传失败: ${xhr.statusText}`, 'error');
                    }
                    uploadProgress.style.display = 'none';
                    currentRequest = null;
                };

                xhr.onerror = () => {
                    showNotification('上传时发生网络错误', 'error');
                    uploadProgress.style.display = 'none';
                    currentRequest = null;
                };

                xhr.send(formData);

            } catch (error) {
                console.error('上传时出错:', error);
                showNotification('上传时发生未知错误', 'error');
                uploadProgress.style.display = 'none';
                currentRequest = null;
            }
        });
    }

    // 识别按钮处理
    if(recognizeBtn) {
        recognizeBtn.addEventListener('click', async () => {
            if (!fileInput.files.length) {
                showNotification('请先选择图片文件');
                return;
            }
            
            const formData = new FormData();
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append('files', fileInput.files[i]);
            }
            
            // 禁用识别按钮并显示加载状态
            recognizeBtn.disabled = true;
            recognizeBtn.innerHTML = '🔄 识别中...';
            
            try {
                const response = await fetch('/api/recognize_cats', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 识别成功，填充猫咪名字到文本框
                    const suggestedName = data.suggested_name;
                    if (suggestedName && catNameInput) {
                        catNameInput.value = suggestedName;
                        catNameInput.focus();
                        
                        // 高亮显示文本框，提示用户注意
                        catNameInput.style.backgroundColor = '#fffacd';
                        catNameInput.style.border = '2px solid #ffd700';
                        
                        // 3秒后恢复正常样式
                        setTimeout(() => {
                            catNameInput.style.backgroundColor = '';
                            catNameInput.style.border = '';
                        }, 3000);
                    }
                    
                    // 显示识别结果
                    let message = `✨ 识别成功！建议猫咪名字：${suggestedName}<br>`;
                    message += `📊 识别了 ${data.recognized_count} 张图片<br>`;
                    
                    if (data.recognition_results && data.recognition_results.length > 0) {
                        message += '<br>📋 详细识别结果：<br>';
                        data.recognition_results.forEach(result => {
                            message += `📷 ${result.filename} → 🐱 ${result.cat_name}<br>`;
                        });
                    }
                    
                    if (data.failed_count > 0) {
                        message += `<br>⚠️ ${data.failed_count} 张图片识别失败`;
                    }
                    
                    message += '<br><br>💡 请确认猫咪名字后点击"上传图片"按钮完成上传';
                    
                    showNotification(message, 'success');
                    
                } else {
                    // 识别失败
                    let errorMessage = '识别失败：';
                    if (data.failed_files && data.failed_files.length > 0) {
                        data.failed_files.forEach(file => {
                            if (file.error === 'Recognition failed') {
                                errorMessage += `<br>📷 ${file.filename} → ❌ 未识别`;
                            } else {
                                errorMessage += `<br>📷 ${file.filename} → ❌ ${file.error}`;
                            }
                        });
                    } else {
                        errorMessage += data.error || '未知错误';
                    }
                    
                    errorMessage += '<br><br>💡 请手动输入猫咪名字后点击"上传图片"按钮';
                    
                    showNotification(errorMessage, 'error');
                }
                
            } catch (error) {
                console.error('识别时出错:', error);
                if (error.name === 'AbortError') {
                    showNotification('识别已取消');
                } else {
                    showNotification('识别服务不可用，请稍后再试', 'error');
                }
            } finally {
                // 恢复按钮状态
                recognizeBtn.disabled = false;
                recognizeBtn.innerHTML = '🔍 识别猫咪';
            }
        });
    }
    
    // 取消上传
    function cancelUpload() {
        if (currentRequest) {
            currentRequest.abort();
            showNotification('上传已取消');
            uploadProgress.style.display = 'none';
            currentRequest = null;
        }
        resetUploadForm();
    }
    
    if(cancelUploadBtn) cancelUploadBtn.addEventListener('click', cancelUpload);
    if(cancelUploadBtnProgress) cancelUploadBtnProgress.addEventListener('click', cancelUpload);


    // 重置上传表单
    function resetUploadForm() {
        if(uploadForm) uploadForm.reset();
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';
        uploadProgressBar.style.width = '0%';
        uploadProgress.style.display = 'none';
    }

    // 显示通知
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = message; // 使用 innerHTML 支持 HTML 内容
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000); // 延长显示时间到 5 秒
    }

    // 初始加载
    loadCats();
    window.addEventListener('scroll', handleScroll);

    // 初始化图片放大功能
    window.openImageModal = initImageModal();
});
