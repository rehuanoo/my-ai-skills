/*
 * Flowise Custom JS Function
 * 商汤 SenseNova 智能 PPT 工作流
 *
 * 输入（$input）：纯文本「主题：xxx；页数：6页」或 JSON {"topic":"xxx","slideCount":6}
 * 处理：kimi-k3 生成 JSON 大纲 → sensenova-u1.5-lite 逐页生成 16:9 幻灯片图片
 * 输出：{ success, title, outline, slides:[{title,content,layout,imageUrl}], meta }
 *
 * 说明：sensenova-u1.5-lite 是文生图模型（/images/generations），
 * 不能作为文本大纲模型，因此 kimi-k3 限流时文本回退到 deepseek-v4-flash。
 */

const axios = require('axios');

const BASE_URL = 'https://token.sensenova.cn/v1';
const API_KEY = process.env.SENSENOVA_API_KEY || "";
const PRIMARY_MODEL = 'kimi-k3';
const TEXT_FALLBACK_MODEL = 'glm-5.2';
const TEXT_FALLBACK_MODEL_2 = 'deepseek-v4-flash';
const IMAGE_MODEL = 'sensenova-u1.5-lite';
const IMAGE_SIZE = '1536x864';
const MAX_SLIDES = 10;
const MIN_SLIDES = 3;
const IMAGE_CONCURRENCY = 3;
const startedAt = Date.now();

function log(msg) {
    try {
        console.log('[SensePPT] ' + msg);
    } catch (e) {}
}

function sleep(ms) {
    return new Promise(function (resolve) {
        setTimeout(resolve, ms);
    });
}

function asText(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    try {
        return JSON.stringify(value);
    } catch (e) {
        return String(value);
    }
}

function parseInput(raw) {
    const text = asText(raw).trim();
    let topic = '';
    let slideCount = 6;
    let providedOutline = null;
    let outlineOnly = false;

    try {
        const obj = JSON.parse(text);
        if (obj && typeof obj === 'object') {
            topic = asText(obj.topic || obj.question || obj.prompt || '').trim();
            slideCount = parseInt(obj.slideCount || obj.pages || obj.count || 0, 10) || 6;
            if (obj.outline && typeof obj.outline === 'object') providedOutline = obj.outline;
            if (obj.providedOutline && typeof obj.providedOutline === 'object') providedOutline = obj.providedOutline;
            outlineOnly = obj.outlineOnly === true || obj.mode === 'outline';
        }
    } catch (e) {
        // not JSON, parse the natural-language form below
    }

    if (!topic) {
        let m = text.match(/主题\s*[：:]\s*([^\n；;]+)/);
        if (m) topic = m[1].trim();
    }
    if (!topic && text) {
        topic = text
            .replace(/^(请|帮我|麻烦)?\s*(生成|制作|做|创建)?\s*(一份|一个)?\s*/u, '')
            .replace(/[，,。；;].*$/u, '')
            .trim();
    }
    const cm = text.match(/(\d+)\s*页/);
    if (cm) slideCount = parseInt(cm[1], 10);
    if (!Number.isFinite(slideCount)) slideCount = 6;
    slideCount = Math.max(MIN_SLIDES, Math.min(MAX_SLIDES, slideCount));
    if (!topic) topic = '人工智能赋能企业数字化转型';
    return { topic: topic, slideCount: slideCount, outline: providedOutline, outlineOnly: outlineOnly };
}

function extractJson(text) {
    let s = asText(text).trim();
    if (!s) return null;
    s = s.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
    const first = s.indexOf('{');
    const last = s.lastIndexOf('}');
    if (first < 0 || last <= first) return null;
    const candidate = s.slice(first, last + 1);
    try {
        return JSON.parse(candidate);
    } catch (e) {
        // Remove trailing commas and retry once.
        try {
            return JSON.parse(candidate.replace(/,\s*([}\]])/g, '$1'));
        } catch (e2) {
            return null;
        }
    }
}

function cleanLine(value, maxLen) {
    return asText(value)
        .replace(/[\r\n]+/g, ' ')
        .replace(/^[\s•·\-—*#\d.、)）]+/u, '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, maxLen || 120);
}

function normalizeOutline(obj, topic, slideCount) {
    if (!obj || typeof obj !== 'object') return null;
    let slides = Array.isArray(obj.slides) ? obj.slides : null;
    if (!slides || slides.length === 0) return null;

    const title = cleanLine(obj.title || topic, 30) || topic;
    let out = [];
    for (let i = 0; i < slides.length && out.length < slideCount; i++) {
        const src = slides[i] || {};
        let st = cleanLine(src.title || src.heading || src.name, 24);
        let content = src.content || src.points || src.bullets || src.body || '';
        if (Array.isArray(content)) content = content.join('；');
        content = cleanLine(content, 220);
        if (!st) st = out.length === 0 ? title : '核心要点 ' + (out.length + 1);
        if (!content) content = '围绕主题提炼关键信息；结合场景说明价值；给出可执行建议';
        let layout = asText(src.layout || '').toLowerCase();
        if (!/^(cover|content|cards|closing|end)$/.test(layout)) {
            layout = out.length === 0 ? 'cover' : out.length === slideCount - 1 ? 'closing' : 'content';
        }
        if (out.length === 0) layout = 'cover';
        out.push({ title: st, content: content, layout: layout });
    }

    // If the model returned too few pages, fill with useful, non-empty pages.
    const fillers = [
        { title: '背景与挑战', content: '行业环境正在快速变化；传统模式效率受限；需要新的技术抓手' },
        { title: '核心方案', content: '以智能技术重构关键流程；数据驱动持续优化；兼顾体验与成本' },
        { title: '落地路径', content: '先试点验证价值；再规模化推广；建立指标与反馈闭环' },
        { title: '价值衡量', content: '效率提升可量化；服务质量可追踪；长期价值可复用' }
    ];
    let fi = 0;
    while (out.length < slideCount) {
        const f = fillers[fi % fillers.length];
        out.push({ title: f.title, content: f.content, layout: out.length === slideCount - 1 ? 'closing' : 'content' });
        fi++;
    }
    out = out.slice(0, slideCount);
    if (out.length > 1) out[out.length - 1].layout = 'closing';
    return { title: title, slides: out };
}

function splitPoints(content) {
    let parts = asText(content)
        .split(/[；;]+/u)
        .map(function (x) { return cleanLine(x, 60); })
        .filter(Boolean);
    if (parts.length < 2) {
        parts = asText(content)
            .split(/[。！？!?]+/u)
            .map(function (x) { return cleanLine(x, 60); })
            .filter(Boolean);
    }
    if (parts.length === 0) parts = [cleanLine(content, 60) || '核心要点'];
    return parts.slice(0, 5);
}

function styleLine(layout) {
    if (layout === 'cover') {
        return '深蓝到青绿色的高级渐变背景，细微光晕与几何线条，现代商务科技感，扁平化信息图，留白充足，中文黑体，标题大而醒目，无照片，无水印。';
    }
    if (layout === 'closing') {
        return '深蓝渐变背景，简洁光带与几何装饰，现代商务科技感，扁平化信息图，留白充足，中文黑体，标题大而醒目，无照片，无水印。';
    }
    return '浅灰白背景，深蓝主色，青绿色点缀，圆角卡片，细腻阴影，现代商务科技感，扁平化信息图，留白充足，中文黑体，文字大而清晰，无照片，无水印。';
}

function buildImagePrompt(outline, slide, index, total) {
    const layout = slide.layout;
    const points = splitPoints(slide.content);
    const head = '请生成一张 16:9 横版中文 PPT 幻灯片图片。' +
        '整体风格：' + styleLine(layout) +
        '画面中不要显示页码、“第 X 页”、logo、水印，也不要出现下列指定文字之外的任何文字。\n';

    if (layout === 'cover') {
        return head +
            '这是封面页。画面中必须逐字准确显示以下中文，不得错字、漏字、加引号或添加其他文字：\n' +
            '主标题：' + outline.title + '\n' +
            '副标题：' + slide.title + '\n' +
            '底部小字：AI 智能生成\n' +
            '标题居中偏左，副标题在标题下方，整体大气、克制、有秩序感。';
    }
    if (layout === 'closing') {
        return head +
            '这是结尾页。画面中必须逐字准确显示以下中文，不得错字、漏字、加引号或添加其他文字：\n' +
            '主标题：' + (slide.title || '感谢聆听') + '\n' +
            '副标题：' + points[0] + '\n' +
            '底部小字：THANK YOU\n' +
            '画面简洁，留白充足，标题醒目，适合作为演示文稿最后一页。';
    }

    const cardLayout = points.length >= 4
        ? '2×2 四宫格（两行两列），避免横向挤成四列'
        : points.length + ' 个横向并列卡片';
    const cardLines = points.map(function (p, i) {
        return '卡片 ' + (i + 1) + ' 显示文字：' + p;
    }).join('\n');

    return head +
        '这是内容页。页面顶部必须逐字准确显示主标题，不要加引号或方括号：\n' +
        '主标题：' + slide.title + '\n' +
        '页面主体采用' + cardLayout + '，每个卡片配一个简洁线性图标；\n' +
        '每个卡片必须逐字准确显示以下中文，不得错字、漏字、加引号或添加其他文字：\n' +
        cardLines + '\n' +
        '卡片文字最多两行、字号足够大，层级分明；不要出现页码、英文乱码、logo、水印或无关装饰文字。';
}

async function callChat(model, topic, slideCount) {
    const system = '你是资深 PPT 策划与结构化数据专家。你只输出合法 JSON，绝不输出 Markdown 代码块、解释或前后缀。';
    const user = [
        '请为主题「' + topic + '」策划一份 ' + slideCount + ' 页的中文 PPT 大纲（含封面和结尾页）。',
        '只输出一个 JSON 对象，结构严格如下：',
        '{"title":"整套PPT主标题，不超过 18 个字","slides":[{"title":"本页标题，不超过 14 个字","content":"2 到 4 条要点，用中文分号；分隔，总长不超过 90 字","layout":"cover|content|cards|closing"}]}',
        '要求：',
        '1. slides 数组必须正好 ' + slideCount + ' 个元素；第 1 页 layout=cover，最后一页 layout=closing。',
        '2. 中间页面 layout 只能是 content 或 cards；每页 content 必须有 2-4 条具体、可读的要点。',
        '3. 内容要专业、具体、有逻辑，避免空话；整套大纲形成清晰的叙事结构。',
        '4. 所有文字使用简体中文；不要在 JSON 中使用换行符、Markdown 或编号符号。',
        '5. 第一个字符必须是 {，最后一个字符必须是 }。'
    ].join('\n');

    const body = {
        model: model,
        messages: [
            { role: 'system', content: system },
            { role: 'user', content: user }
        ],
        max_tokens: 2200,
        temperature: model === PRIMARY_MODEL ? 1 : 0.5,
        stream: false
    };
    const resp = await axios.post(BASE_URL + '/chat/completions', body, {
        headers: { Authorization: 'Bearer ' + API_KEY, 'Content-Type': 'application/json' },
        timeout: 150000,
        validateStatus: function () { return true; }
    });
    if (resp.status < 200 || resp.status >= 300) {
        const detail = asText(resp.data).slice(0, 400);
        const err = new Error('chat ' + model + ' HTTP ' + resp.status + ': ' + detail);
        err.status = resp.status;
        throw err;
    }
    const choice = resp.data && resp.data.choices && resp.data.choices[0];
    const msg = choice && choice.message ? choice.message : {};
    const text = asText(msg.content) || asText(msg.reasoning_content) || asText(msg.reasoning);
    return { text: text, model: model, usage: resp.data.usage || null };
}

async function generateOutline(topic, slideCount) {
    const attempts = [
        { model: PRIMARY_MODEL, label: 'primary' },
        { model: TEXT_FALLBACK_MODEL, label: 'fallback' },
        { model: TEXT_FALLBACK_MODEL_2, label: 'fallback2' }
    ];
    let lastErr = null;
    for (let i = 0; i < attempts.length; i++) {
        const a = attempts[i];
        try {
            log('生成大纲，模型 ' + a.model + ' ...');
            const result = await callChat(a.model, topic, slideCount);
            const obj = extractJson(result.text);
            const outline = normalizeOutline(obj, topic, slideCount);
            if (!outline) throw new Error('模型返回内容不是可解析的大纲 JSON');
            return {
                outline: outline,
                model: a.model,
                fallback: a.label !== 'primary',
                usage: result.usage
            };
        } catch (e) {
            lastErr = e;
            log('大纲模型 ' + a.model + ' 失败：' + asText(e.message || e));
            if (i < attempts.length - 1) {
                // Small pause before trying the fallback; never block the request for long.
                await sleep(800);
            }
        }
    }
    throw new Error('大纲生成失败（kimi-k3 与文本回退模型均不可用）：' + asText(lastErr && lastErr.message));
}

async function generateOneImage(prompt, index) {
    let lastStatus = 0;
    let lastDetail = '';
    for (let attempt = 1; attempt <= 3; attempt++) {
        const resp = await axios.post(BASE_URL + '/images/generations', {
            model: IMAGE_MODEL,
            prompt: prompt,
            n: 1,
            size: IMAGE_SIZE,
            output_format: 'png',
            response_format: 'url',
            watermark: false,
            prompt_extend: false
        }, {
            headers: { Authorization: 'Bearer ' + API_KEY, 'Content-Type': 'application/json' },
            timeout: 240000,
            validateStatus: function () { return true; }
        });
        lastStatus = resp.status;
        if (resp.status >= 200 && resp.status < 300) {
            const item = resp.data && resp.data.data && resp.data.data[0];
            const url = item && (item.url || '');
            if (url) {
                log('第 ' + (index + 1) + ' 页图片完成');
                return { url: url, usage: resp.data.usage || null };
            }
            lastDetail = '响应中没有图片 URL';
        } else {
            lastDetail = asText(resp.data).slice(0, 400);
        }
        if (resp.status === 429 || resp.status >= 500) {
            if (attempt < 3) {
                await sleep(attempt === 1 ? 2500 : 6000);
                continue;
            }
        }
        break;
    }
    throw new Error('第 ' + (index + 1) + ' 页生图失败 HTTP ' + lastStatus + ': ' + lastDetail);
}

async function generateImages(outline) {
    const slides = outline.slides;
    const results = new Array(slides.length);
    const prompts = slides.map(function (s, i) { return buildImagePrompt(outline, s, i, slides.length); });

    for (let start = 0; start < slides.length; start += IMAGE_CONCURRENCY) {
        const batch = [];
        for (let i = start; i < Math.min(start + IMAGE_CONCURRENCY, slides.length); i++) {
            batch.push((function (idx) {
                return generateOneImage(prompts[idx], idx).then(function (r) {
                    results[idx] = { url: r.url, usage: r.usage, prompt: prompts[idx] };
                });
            })(i));
        }
        await Promise.all(batch);
    }

    return slides.map(function (s, i) {
        return {
            index: i + 1,
            title: s.title,
            content: s.content,
            layout: s.layout,
            imageUrl: results[i].url,
            imagePrompt: results[i].prompt
        };
    });
}

async function main() {
    const rawInput = asText($input).trim();
    if (rawInput === '__PING__' || rawInput.indexOf('"ping":true') >= 0) {
        return {
            success: true,
            ping: true,
            service: 'SenseTime PPT Flowise Workflow',
            primaryModel: PRIMARY_MODEL,
            imageModel: IMAGE_MODEL,
            at: new Date().toISOString()
        };
    }
    const input = parseInput($input);
    log('开始：' + input.topic + ' / ' + input.slideCount + ' 页' + (input.outlineOnly ? '（仅大纲）' : ''));

    let outlineResult;
    if (input.outline) {
        const supplied = normalizeOutline(input.outline, input.topic, input.slideCount);
        if (!supplied) throw new Error('传入的 outline 结构无效：缺少 slides 数组');
        outlineResult = { outline: supplied, model: 'provided-outline', fallback: false, usage: null };
        log('使用调用方传入的大纲，跳过 LLM');
    } else {
        outlineResult = await generateOutline(input.topic, input.slideCount);
        log('大纲完成，模型 ' + outlineResult.model);
    }

    const baseMeta = {
        outlineModel: outlineResult.model,
        outlineFallback: outlineResult.fallback,
        imageModel: IMAGE_MODEL,
        imageSize: IMAGE_SIZE,
        primaryModel: PRIMARY_MODEL,
        textFallbackModel: TEXT_FALLBACK_MODEL,
        note: 'U1.5 Lite 为文生图模型，负责逐页幻灯片图片；Kimi-K3 限流时文本大纲回退到 GLM-5.2 / DeepSeek-V4-Flash。',
        elapsedMs: Date.now() - startedAt,
        generatedAt: new Date().toISOString()
    };

    if (input.outlineOnly) {
        return {
            success: true,
            outlineOnly: true,
            title: outlineResult.outline.title,
            topic: input.topic,
            slideCount: outlineResult.outline.slides.length,
            outline: outlineResult.outline,
            slides: [],
            meta: baseMeta
        };
    }

    const slides = await generateImages(outlineResult.outline);

    return {
        success: true,
        outlineOnly: false,
        title: outlineResult.outline.title,
        topic: input.topic,
        slideCount: slides.length,
        outline: outlineResult.outline,
        slides: slides,
        meta: Object.assign({}, baseMeta, { elapsedMs: Date.now() - startedAt })
    };
}

return await main();
