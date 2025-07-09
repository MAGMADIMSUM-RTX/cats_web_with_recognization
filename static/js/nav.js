document.addEventListener('DOMContentLoaded', function() {
    const uploadBtnNav = document.getElementById('upload-btn-nav');
    const uploadSection = document.getElementById('upload-section');
    const gallery = document.getElementById('cat-gallery');

    // 上传按钮点击事件
    if (uploadBtnNav && uploadSection) {
        uploadBtnNav.addEventListener('click', () => {
            // 只在主页操作
            if (window.location.pathname === '/') {
                const isHidden = uploadSection.style.display === 'none' || !uploadSection.style.display;
                uploadSection.style.display = isHidden ? 'block' : 'none';
                if (gallery) {
                    gallery.style.display = isHidden ? 'none' : 'grid';
                }
                
                // 切换上传按钮的激活状态
                if (isHidden) {
                    uploadBtnNav.classList.add('active');
                    // 移除其他按钮的激活状态
                    document.querySelectorAll('.sidebar-btn.active').forEach(btn => {
                        if (btn !== uploadBtnNav) {
                            btn.classList.remove('active');
                        }
                    });
                } else {
                    uploadBtnNav.classList.remove('active');
                    // 恢复主页按钮的激活状态
                    const homeBtn = document.querySelector('a[href="/"]');
                    if (homeBtn) {
                        homeBtn.classList.add('active');
                    }
                }
            } else {
                // 如果不在主页，则跳转到主页并带上一个参数以自动打开上传界面
                window.location.href = '/?upload=true';
            }
        });
    }
    
    // 检查URL中是否有upload=true参数
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('upload') === 'true' && uploadSection) {
        uploadSection.style.display = 'block';
        if (gallery) {
            gallery.style.display = 'none';
        }
        // 激活上传按钮
        if (uploadBtnNav) {
            uploadBtnNav.classList.add('active');
        }
    }
    
    // 当上传界面关闭时，恢复按钮状态
    document.addEventListener('click', function(e) {
        if (e.target.id === 'cancel-upload-btn' || e.target.closest('#cancel-upload-btn')) {
            if (uploadBtnNav) {
                uploadBtnNav.classList.remove('active');
            }
            // 恢复主页按钮的激活状态
            const homeBtn = document.querySelector('a[href="/"]');
            if (homeBtn) {
                homeBtn.classList.add('active');
            }
        }
    });
});

// 全局通知函数
function showNotification(message, type = 'success') {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    container.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
