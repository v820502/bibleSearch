document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const openSelector = document.getElementById('openSelector');
    const selectorModal = document.getElementById('selectorModal');
    const closeSelector = document.getElementById('closeSelector');
    const confirmSelection = document.getElementById('confirmSelection');
    const bookSelect = document.getElementById('bookSelect');
    const chapterSelect = document.getElementById('chapterSelect');
    const verseSelect = document.getElementById('verseSelect');
    const bibleContent = document.getElementById('bibleContent');
    const copyBtn = document.getElementById('copyVerseBtn');

    // 載入書卷列表
    fetch('/api/books')
        .then(response => response.json())
        .then(books => {
            books.forEach(book => {
                const option = document.createElement('option');
                option.value = book;
                option.textContent = book;
                bookSelect.appendChild(option);
            });
        });

    // 書卷選擇變更時更新章節
    bookSelect.addEventListener('change', function() {
        const book = this.value;
        fetch(`/api/chapters/${book}`)
            .then(response => response.json())
            .then(chapters => {
                chapterSelect.innerHTML = '';
                // 新增一個空白選項，代表「請選擇章」
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = '（請選擇章）';
                chapterSelect.appendChild(emptyOption);
                chapters.forEach((chapter, idx) => {
                    const option = document.createElement('option');
                    option.value = chapter;
                    option.textContent = chapter;
                    chapterSelect.appendChild(option);
                });
                // 不自動呼叫 updateVerses()
                verseSelect.innerHTML = '';
            });
    });

    // 章節選擇變更時才更新節數
    chapterSelect.addEventListener('change', function() {
        if (!chapterSelect.value) {
            verseSelect.innerHTML = '';
            return;
        }
        updateVerses();
    });

    function updateVerses() {
        const book = bookSelect.value;
        const chapter = chapterSelect.value;
        fetch(`/api/verses/${book}/${chapter}`)
            .then(response => response.json())
            .then(verses => {
                verseSelect.innerHTML = '';
                // 新增一個空白選項，代表「不選擇」
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = '（全部）';
                verseSelect.appendChild(emptyOption);
                verses.forEach(verse => {
                    const option = document.createElement('option');
                    option.value = verse;
                    option.textContent = verse;
                    verseSelect.appendChild(option);
                });
            });
    }

    // 搜尋功能
    let searchTimeout;
    let selectedIndex = -1; // 新增：目前選中的下拉選單索引
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 1) {
            searchResults.classList.add('hidden');
            selectedIndex = -1;
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(results => {
                    searchResults.innerHTML = '';
                    selectedIndex = -1; // 每次搜尋重置
                    // 判斷是否為多節查詢（全部元素都有 verse 屬性且無 type: 'book'）
                    const isMultiVerse = results.length > 1 && results.every(r => r.verse && !r.type);
                    if (isMultiVerse) {
                        let html = `<div class='search-result-item search-result-range' style='cursor:pointer;'><div class='verse-reference'>${results[0].book} ${results[0].chapter}:${results[0].verse}-${results[results.length-1].verse}</div><div class='verse-content'>`;
                        results.forEach(vd => {
                            html += `<div><span class='text-gray-400'>${vd.verse}</span> ${vd.text}</div>`;
                        });
                        html += '</div></div>';
                        searchResults.innerHTML = html;
                        // 點擊整個區塊時顯示內容到主區塊
                        searchResults.querySelector('.search-result-range').addEventListener('click', () => {
                            showVerseContent(html);
                            searchResults.classList.add('hidden');
                            searchInput.value = '';
                        });
                        searchResults.classList.remove('hidden');
                        return;
                    }
                    // 其餘情況維持原本行為
                    if (results.length > 0) {
                        results.forEach((result, idx) => {
                            const div = document.createElement('div');
                            div.className = 'search-result-item';
                            div.tabIndex = 0; // 讓其可聚焦
                            div.dataset.index = idx;
                            if (result.type === 'book') {
                                div.textContent = result.book;
                                div.addEventListener('click', () => {
                                    bookSelect.value = result.book;
                                    bookSelect.dispatchEvent(new Event('change'));
                                    selectorModal.classList.remove('hidden');
                                    selectorModal.classList.add('flex');
                                    searchResults.classList.add('hidden');
                                    searchInput.value = '';
                                });
                            } else if (result.type === 'range') {
                                div.textContent = `${result.book} ${result.chapter}:${result.verse_start}-${result.verse_end}`;
                                div.addEventListener('click', () => {
                                    // 這裡可加載該範圍經文內容
                                    fetch(`/api/verses/${result.book}/${result.chapter}`)
                                        .then(response => response.json())
                                        .then(verses => {
                                            const versesInRange = verses.filter(v => v >= result.verse_start && v <= result.verse_end);
                                            let html = `<div class='verse-reference'>${result.book} ${result.chapter}:${result.verse_start}-${result.verse_end}</div><div class='verse-content'>`;
                                            let fetches = versesInRange.map(v =>
                                                fetch(`/api/verse/${result.book}/${result.chapter}/${v}`).then(r => r.json())
                                            );
                                            Promise.all(fetches).then(verseDatas => {
                                                verseDatas.forEach(vd => {
                                                    html += `<div><span class='text-gray-400'>${vd.verse}</span> ${vd.text}</div>`;
                                                });
                                                html += '</div>';
                                                showVerseContent(html);
                                                searchResults.classList.add('hidden');
                                                searchInput.value = '';
                                            });
                                        });
                                });
                            } else if (result.type === 'single') {
                                div.textContent = `${result.book} ${result.chapter}:${result.verse}`;
                                div.addEventListener('click', () => {
                                    fetch(`/api/verse/${result.book}/${result.chapter}/${result.verse}`)
                                        .then(response => response.json())
                                        .then(data => {
                                            displayVerse(data);
                                            searchResults.classList.add('hidden');
                                            searchInput.value = '';
                                        });
                                });
                            } else if (result.type === 'chapter') {
                                div.textContent = `${result.book} ${result.chapter}章`;
                                div.addEventListener('click', () => {
                                    fetch(`/api/verses/${result.book}/${result.chapter}`)
                                        .then(response => response.json())
                                        .then(verses => {
                                            if (verses.length === 0) {
                                                showVerseContent('<div class="text-center text-gray-500">查無經文</div>');
                                                return;
                                            }
                                            let html = `<div class='verse-reference'>${result.book} 第${result.chapter}章</div><div class='verse-content'>`;
                                            let fetches = verses.map(v =>
                                                fetch(`/api/verse/${result.book}/${result.chapter}/${v}`).then(r => r.json())
                                            );
                                            Promise.all(fetches).then(verseDatas => {
                                                verseDatas.forEach(vd => {
                                                    html += `<div><span class='text-gray-400'>${vd.verse}</span> ${vd.text}</div>`;
                                                });
                                                html += '</div>';
                                                showVerseContent(html);
                                                searchResults.classList.add('hidden');
                                                searchInput.value = '';
                                            });
                                        });
                                });
                            }
                            searchResults.appendChild(div);
                        });
                        searchResults.classList.remove('hidden');
                    } else {
                        searchResults.classList.add('hidden');
                    }
                });
        }, 300);
    });

    // 新增：鍵盤上下鍵與 Enter 支援
    searchInput.addEventListener('keydown', function(e) {
        const items = searchResults.querySelectorAll('.search-result-item');
        if (searchResults.classList.contains('hidden') || items.length === 0) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = (selectedIndex + 1) % items.length;
            updateActiveItem();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = (selectedIndex - 1 + items.length) % items.length;
            updateActiveItem();
        } else if (e.key === 'Enter') {
            if (selectedIndex >= 0 && selectedIndex < items.length) {
                items[selectedIndex].click();
            }
        }
    });

    function updateActiveItem() {
        const items = searchResults.querySelectorAll('.search-result-item');
        items.forEach((item, idx) => {
            if (idx === selectedIndex) {
                item.classList.add('bg-blue-100', 'dark:bg-blue-700');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('bg-blue-100', 'dark:bg-blue-700');
            }
        });
    }

    // 點擊外部關閉搜尋結果
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });

    // 模態框控制
    openSelector.addEventListener('click', () => {
        // 每次打開時全部清空
        bookSelect.value = '';
        chapterSelect.innerHTML = '';
        verseSelect.innerHTML = '';
        selectorModal.classList.remove('hidden');
        selectorModal.classList.add('flex');
    });

    closeSelector.addEventListener('click', () => {
        selectorModal.classList.add('hidden');
        selectorModal.classList.remove('flex');
    });

    confirmSelection.addEventListener('click', function() {
        const book = bookSelect.value;
        const chapter = chapterSelect.value;
        const verse = verseSelect.value;
        if (!chapter) {
            showVerseContent('<div class="text-center text-gray-500">請先選擇章</div>');
            return;
        }
        if (!verse) {
            // 若未選擇節，查詢整章所有經文
            fetch(`/api/verses/${book}/${chapter}`)
                .then(response => response.json())
                .then(verses => {
                    if (verses.length === 0) {
                        showVerseContent('<div class="text-center text-gray-500">查無經文</div>');
                        return;
                    }
                    let html = `<div class='verse-reference'>${book} 第${chapter}章</div><div class='verse-content'>`;
                    let fetches = verses.map(v =>
                        fetch(`/api/verse/${book}/${chapter}/${v}`).then(r => r.json())
                    );
                    Promise.all(fetches).then(verseDatas => {
                        verseDatas.forEach(vd => {
                            html += `<div><span class='text-gray-400'>${vd.verse}</span> ${vd.text}</div>`;
                        });
                        html += '</div>';
                        showVerseContent(html);
                        selectorModal.classList.add('hidden');
                        selectorModal.classList.remove('flex');
                    });
                });
        } else {
            fetch(`/api/verse/${book}/${chapter}/${verse}`)
                .then(response => response.json())
                .then(data => {
                    displayVerse(data);
                    selectorModal.classList.add('hidden');
                    selectorModal.classList.remove('flex');
                });
        }
    });

    // 幫助函式：只更新經文內容
    function showVerseContent(html) {
        // 直接覆蓋 verse-content 外層，確保內容乾淨
        const verseContent = bibleContent.querySelector('.verse-content');
        if (verseContent) {
            verseContent.outerHTML = `<div class="verse-content">${html}</div>`;
        }
        updateCopyBtnVisibility();
    }

    // 修改 displayVerse
    function displayVerse(verse) {
        showVerseContent(`
            <div class="verse-reference">${verse.book} ${verse.chapter}:${verse.verse}</div>
            <div><span class='text-gray-400'>${verse.verse}</span> ${verse.text}</div>
        `);
    }

    // 明亮/黑暗模式切換
    const toggleThemeBtn = document.getElementById('toggleTheme');
    function setTheme(dark) {
        if (dark) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            toggleThemeBtn.querySelector('i').className = 'fas fa-sun text-xl';
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            toggleThemeBtn.querySelector('i').className = 'fas fa-moon text-xl';
        }
    }
    // 初始化主題
    const userTheme = localStorage.getItem('theme');
    setTheme(userTheme === 'dark');
    toggleThemeBtn.addEventListener('click', () => {
        const isDark = document.documentElement.classList.contains('dark');
        setTheme(!isDark);
    });

    // 經文複製功能
    const verseContent = bibleContent.querySelector('.verse-content');

    function updateCopyBtnVisibility() {
        // 只要有 .verse-content 就顯示按鈕
        const verseContent = bibleContent.querySelector('.verse-content');
        if (verseContent && verseContent.innerText.trim() && verseContent.innerText.trim() !== '請選擇或搜尋經文') {
            copyBtn.style.display = '';
        } else {
            copyBtn.style.display = 'none';
        }
    }

    copyBtn.addEventListener('click', function() {
        const verseContent = bibleContent.querySelector('.verse-content');
        if (verseContent) {
            const text = verseContent.innerText;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy"></i>'; }, 1200);
            });
        }
    });

    updateCopyBtnVisibility();

    // 監聽內容變化（保險起見）
    const observer = new MutationObserver(updateCopyBtnVisibility);
    observer.observe(bibleContent, { childList: true, subtree: true, characterData: true });
}); 