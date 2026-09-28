(function() {
    function setupTransition() {
        try {
            var doc = window.parent.document;
            var win = window.parent;
            if (!doc || !win) return;

            win.triggerMulaiAnalisisTransition = function(e) {
                var target = doc.getElementById('langkah-analisis') ||
                             doc.getElementById('step1-header-title') ||
                             doc.getElementById('step1-card-marker') ||
                             doc.querySelector('.glass-card') ||
                             doc.querySelector('[data-testid="stFileUploader"]');
                if (!target) return;

                if (e) {
                    if (e.preventDefault) e.preventDefault();
                    if (e.stopPropagation) e.stopPropagation();
                    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                }

                try {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } catch(err) {}

                var candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('.main'),
                    doc.documentElement,
                    doc.body
                ];

                var rect = target.getBoundingClientRect();
                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollHeight > el.clientHeight) {
                        var currentY = el.scrollTop || 0;
                        var targetY = currentY + rect.top - 28;
                        try {
                            el.scrollTo({ top: targetY, behavior: 'smooth' });
                        } catch(err) {
                            el.scrollTop = targetY;
                        }
                    }
                }
            };

            win.triggerScrollToStep3 = function() {
                var target = doc.getElementById('step3-card-marker') || doc.getElementById('langkah-3-anchor');
                if (!target) return;

                var candidates = [
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('.main'),
                    doc.querySelector('section[data-testid="stMain"]'),
                    doc.documentElement,
                    doc.body
                ];

                var rect = target.getBoundingClientRect();
                var scrolled = false;

                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollHeight > el.clientHeight) {
                        var currentY = el.scrollTop || 0;
                        var targetY = currentY + rect.top - 24;
                        try {
                            el.scrollTo({ top: targetY, behavior: 'smooth' });
                            scrolled = true;
                        } catch(err) {
                            el.scrollTop = targetY;
                            scrolled = true;
                        }
                    }
                }

                try {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } catch(err) {}

                if (!scrolled) {
                    try {
                        var winY = (win.pageYOffset || 0) + rect.top - 24;
                        win.scrollTo({ top: winY, behavior: 'smooth' });
                    } catch(err) {}
                }
            };

            // Global capture listener on parent document: intercepts click instantly with 0ms delay
            if (!win.__cacaTransitionHandlerInstalled) {
                win.__cacaTransitionHandlerInstalled = true;
                doc.addEventListener('click', function(e) {
                    var btn = e.target && e.target.closest ? e.target.closest('#btn-mulai-analisis') : null;
                    if (btn) {
                        win.triggerMulaiAnalisisTransition(e);
                    }

                    var runBtn = e.target && e.target.closest ? e.target.closest('button') : null;
                    if (runBtn && runBtn.innerText && runBtn.innerText.indexOf('Jalankan Komputasi Analisis') !== -1) {
                        setTimeout(function() {
                            if (win.triggerScrollToStep3) win.triggerScrollToStep3();
                        }, 50);
                    }
                }, true);
            }

        } catch (err) {
            console.error('CACA transition setup error:', err);
        }
    }

    setupTransition();
    var count = 0;
    var interval = setInterval(function() {
        count++;
        setupTransition();
        if (count > 25) clearInterval(interval);
    }, 100);
})();
