// Компонент загрузки для отображения процесса загрузки
(function() {
    const loaderHtml = `
        <div id="global-loader-overlay" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.4); z-index:9999; justify-content:center; align-items:center;">
            <div style="background:white; padding:40px 60px; border-radius:16px; box-shadow:0 8px 32px rgba(0,0,0,0.2); display:flex; flex-direction:column; align-items:center;">
                <div class="spinner-border text-primary" style="width:3rem; height:3rem; margin-bottom:16px;" role="status">
                  <span class="visually-hidden">Загрузка...</span>
                </div>
                <div style="font-size:1.2rem; color:#333;">Пожалуйста, подождите...</div>
            </div>
        </div>
    `;
    if (!document.getElementById('global-loader-overlay')) {
        document.body.insertAdjacentHTML('beforeend', loaderHtml);
    }
    window.showLoader = function() {
        document.getElementById('global-loader-overlay').style.display = 'flex';
    };
    window.hideLoader = function() {
        document.getElementById('global-loader-overlay').style.display = 'none';
    };
})(); 