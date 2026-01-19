// ==UserScript==
// @name         西电选课脚本助手+
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  自动提取并复制 UA、Accept-Language、BatchID、Cookie 到剪贴板
// @author       Qwen+XDU
// @match        https://xk.xidian.edu.cn/xsxk/elective/grablessons*
// @grant        GM_setClipboard
// @grant        GM_addStyle
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    // 获取 URL 中的 batchId 参数
    const urlParams = new URLSearchParams(window.location.search);
    const batchId = urlParams.get('batchId') || '未找到 BatchID';

    // 获取必要信息
    const userAgent = navigator.userAgent;

    let acceptLanguageHeader = 'zh-CN'; // 默认 fallback
    try {
        const langs = navigator.languages || [navigator.language || 'zh-CN'];
        const uniqueLangs = [...new Set(langs)]; // 去重
        const parts = uniqueLangs.map((lang, index) => {
            if (index === 0) return lang; // 第一个 q=1.0（省略）
            const q = Math.max(0.5, 1.0 - index * 0.1).toFixed(1); // 0.9, 0.8, ..., 最低 0.5
            return `${lang};q=${q}`;
        });
        acceptLanguageHeader = parts.join(',');
    } catch (e) {
        console.warn('[Accept-Language] 生成失败，使用默认值');
    }

    function formatCookie(cookieStr) {
        if (!cookieStr) return '';
        const cookies = cookieStr.split(';').map(c => c.trim()).filter(c => c);
        const authCookies = [];
        const otherCookies = [];

        for (const c of cookies) {
            if (c.startsWith('Authorization=')) {
                authCookies.push(c);
            } else {
                otherCookies.push(c);
            }
        }
        // 拼接：Authorization 在前，其余保持原始顺序
        return [...authCookies, ...otherCookies].join('; ');
    }

    const formattedCookie = formatCookie(document.cookie);

    // 构造输出字符串
    const output = `UserAgentTypeIn = "${userAgent}"\n` +
                   `AcceptLanguage = "${acceptLanguageHeader}"\n` +
                   `BatchID = "${batchId}"\n` +
                   `CookieIsHere = "${formattedCookie}"`;

    // 尝试使用 Tampermonkey 的 GM_setClipboard（兼容性最好）
    if (typeof GM_setClipboard === 'function') {
        GM_setClipboard(output, 'text');
        console.log('[西电选课脚本] 信息已复制到剪贴板（通过 GM_setClipboard）');
    } else {
        // 回退到原生 Clipboard API（现代浏览器支持）
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard.writeText(output).then(() => {
                console.log('[西电选课脚本] 信息已复制到剪贴板（通过 navigator.clipboard）');
            }).catch(err => {
                console.warn('[西电选课脚本] 无法写入剪贴板，请手动复制以下内容：\n', output);
                alert('⚠️ 无法自动复制到剪贴板！\n请打开开发者工具控制台查看信息并手动复制。');
            });
        } else {
            // 最后手段：弹出文本框供用户手动复制
            const textarea = document.createElement('textarea');
            textarea.value = output;
            textarea.style.position = 'fixed';
            textarea.style.top = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                const success = document.execCommand('copy');
                if (success) {
                    console.log('[西电选课脚本] 信息已通过 execCommand 复制');
                } else {
                    throw new Error('execCommand failed');
                }
            } catch (e) {
                console.warn('[西电选课脚本] 所有复制方法失败，请手动复制以下内容：\n', output);
                alert('⚠️ 请手动复制以下信息（已打印到控制台）：\n' + output);
            }
            document.body.removeChild(textarea);
        }
    }

    // 可选：在页面右下角显示一个临时提示（美观且不干扰）
    GM_addStyle(`
        #xidian-copy-notice {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 10px 16px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 9999;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            animation: fadeOut 3s forwards;
        }
        @keyframes fadeOut {
            0% { opacity: 1; transform: translateY(0); }
            70% { opacity: 1; }
            100% { opacity: 0; transform: translateY(-20px); }
        }
    `);

    const notice = document.createElement('div');
    notice.id = 'xidian-copy-notice';
    notice.textContent = '✅ 选课信息已复制到剪贴板';
    document.body.appendChild(notice);

    // 3秒后自动移除提示
    setTimeout(() => {
        if (notice.parentNode) notice.parentNode.removeChild(notice);
    }, 3000);
})();