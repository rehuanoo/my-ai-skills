const fs = require('fs');
const path = require('path');
const code = fs.readFileSync(path.join(__dirname, 'sensetime_ppt_node.js'), 'utf8');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
(async () => {
    const fn = new AsyncFunction('$input', 'require', code);
    const result = await fn(process.argv[2] || '主题：人工智能赋能客户服务；页数：3页', require);
    fs.writeFileSync(path.join(__dirname, 'workflow_result.json'), JSON.stringify(result, null, 2), 'utf8');
    console.log(JSON.stringify({
        success: result.success,
        title: result.title,
        slideCount: result.slideCount,
        meta: result.meta,
        slides: result.slides.map(s => ({ index: s.index, title: s.title, imageUrl: s.imageUrl ? s.imageUrl.slice(0, 80) + '...' : null }))
    }, null, 2));
})().catch(e => {
    console.error('FAILED', e && e.stack ? e.stack : e);
    process.exit(1);
});
