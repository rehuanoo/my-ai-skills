"""在 Flowise 里创建"智能PPT生成"工作流（克隆已验证的文档流结构）"""
import os, sqlite3, json, urllib.request, ssl, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.getenv('FLOWISE_DB',
               r'<你的Flowise目录>\.flowise\database\database.sqlite')
API = 'http://127.0.0.1:3000/api/v1'
KEY = 'Bearer ' + os.getenv('FLOWISE_API_KEY', '')
FLOW_NAME = '智能PPT生成（商汤 kimi-k3）'
FALLBACK_MODEL = 'sensenova-6.8-flash-lite'

SYSTEM_PROMPT = (
    '你是专业的 PPT 策划与结构化数据生成助手。用户会给出主题和页数，你必须只输出一个合法的 JSON 对象，'
    '不要输出任何解释、前言、注释或 Markdown 代码块标记。\n'
    'JSON 结构必须严格如下：\n'
    '{"title":"整套PPT主标题(不超过15字)","slides":[{"title":"本页标题(不超过12字)",'
    '"content":"本页正文要点,2到4条,用分号分隔,总长不超过80字",'
    '"image_prompt":"本页配图的英文描述短语,20到40个英文单词"}]}\n'
    '要求：\n'
    '1. slides 数组的元素个数等于用户要求的页数（含封面页）。\n'
    '2. 每个元素都必须同时包含 title、content、image_prompt 三个字段，一个都不能少。\n'
    '3. content 用中文分号 "；" 分隔要点，不要使用换行、Markdown 或编号符号。\n'
    '4. image_prompt 必须是英文，描述具体可绘制的画面，不要出现文字logo。\n'
    '5. 第一个 slides 元素作为封面页。\n'
    '6. 只输出 JSON，第一个字符必须是 {，最后一个字符必须是 }。'
)

# ---- 1. 从数据库读取模板流 ----
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("SELECT flowData FROM chat_flow WHERE name LIKE '%智能文档%' LIMIT 1")
row = cur.fetchone()
if not row:
    print('找不到模板流')
    sys.exit(1)
flow = json.loads(row['flowData'])
con.close()

# ---- 2. 修改节点 ----
for n in flow['nodes']:
    name = n['data'].get('name')
    if name == 'chatPromptTemplate':
        n['data']['label'] = 'PPT大纲提示词'
        n['data']['inputs']['systemMessagePrompt'] = SYSTEM_PROMPT
        n['data']['inputs']['humanMessagePrompt'] = '{question}'
    elif name == 'chatOpenAICustom':
        n['data']['label'] = '商汤 kimi-k3'
        n['data']['inputs']['modelName'] = 'kimi-k3'
        n['data']['inputs']['maxTokens'] = 4096
        n['data']['inputs']['temperature'] = 0.6
        n['data']['inputs']['streaming'] = False
    elif name == 'llmChain':
        n['data']['label'] = 'PPT生成链'
        n['data']['inputs']['chainName'] = 'PPT生成链'

payload = {
    'name': FLOW_NAME,
    'flowData': json.dumps(flow, ensure_ascii=False),
    'type': 'CHATFLOW',
    'deployed': True,
    'isPublic': False,
    'category': '智能PPT',
}

ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    f'{API}/chatflows',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Authorization': KEY, 'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        resp = json.loads(r.read().decode())
    print('[CREATE OK] id =', resp.get('id'), ' name =', resp.get('name'))
    with open(os.path.join(HERE, 'ppt_flow_id.txt'), 'w', encoding='utf-8') as f:
        f.write(resp['id'])
    print('flowId 已写入 ppt_flow_id.txt')
except urllib.error.HTTPError as e:
    print(f'[CREATE FAIL] HTTP{e.code}: {e.read().decode()[:800]}')
    sys.exit(1)
