# -*- coding: utf-8 -*-
"""构建 Flowise 工作流：商汤 SenseNova 6.8 Flash Lite 文档生成"""
import os
import json, urllib.request, urllib.error

BASE = 'http://127.0.0.1:3000'
KEY = os.getenv("FLOWISE_API_KEY", "")
SENSE_URL = 'https://token.sensenova.cn/v1'
SENSE_KEY = os.getenv("SENSENOVA_API_KEY", "")
MODEL = 'sensenova-6.8-flash-lite'


def api(path, method='GET', body=None):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + KEY)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode('utf-8')
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        print('HTTP', e.code, e.read().decode('utf-8', 'ignore')[:800])
        raise


def get_node(name):
    return api('/api/v1/nodes/' + name)


def build_node(node_id, api_name, inputs, pos, credential=None, label=None):
    d = get_node(api_name)
    data = {
        'label': label or d['label'],
        'name': d['name'],
        'version': d.get('version', 1),
        'type': d['type'],
        'icon': d.get('icon', ''),
        'category': d['category'],
        'description': d.get('description', ''),
        'baseClasses': d['baseClasses'],
        'inputs': inputs,
        'filePath': d.get('filePath', ''),
        'id': node_id,
        'inputParams': d.get('inputs', []),
    }
    if credential:
        data['credential'] = credential
        data['inputs'] = dict(inputs, credential=credential)

    input_anchors = []
    for i in d.get('inputs', []):
        if i.get('type') in ('BaseLanguageModel', 'BaseChatModel', 'BasePromptTemplate', 'BaseMemory',
                             'BaseLLMOutputParser', 'BaseCache', 'Moderation', 'BaseRetriever',
                             'BaseDocumentStore', 'Tool', 'BaseOutputParser', 'ChatPromptTemplate'):
            input_anchors.append({
                'id': '%s-input-%s-%s' % (node_id, i['name'], i['type']),
                'label': i.get('label', i['name']),
                'name': i['name'],
                'type': 'input',
            })
    output_anchors = [{
        'id': '%s-output-%s-%s' % (node_id, d['name'], '|'.join(d['baseClasses'])),
        'label': label or d['label'],
        'name': d['name'],
        'type': 'output',
    }]
    data['inputAnchors'] = input_anchors
    data['outputAnchors'] = output_anchors
    default_output = d.get('outputs', [])
    if api_name == 'llmChain':
        data['outputs'] = {'output': 'llmChain'}
    else:
        data['outputs'] = {'output': default_output[0]['name']} if default_output else {}

    return {
        'id': node_id,
        'position': {'x': pos[0], 'y': pos[1]},
        'type': 'customNode',
        'data': data,
        'width': 300,
        'height': 300,
        'selected': False,
        'dragging': False,
        'positionAbsolute': {'x': pos[0], 'y': pos[1]},
    }


def edge(src, src_name, src_classes, dst, dst_name, dst_type):
    return {
        'source': src,
        'target': dst,
        'sourceHandle': '%s-output-%s-%s' % (src, src_name, '|'.join(src_classes)),
        'targetHandle': '%s-input-%s-%s' % (dst, dst_name, dst_type),
        'id': 'edge-%s-%s-%s' % (src, dst, dst_name),
        'type': 'buttonedge',
    }


# ---------- 1. 创建凭据 ----------
creds = api('/api/v1/credentials') or []
cred_id = None
for c in creds:
    if c['name'] == '商汤 SenseNova':
        cred_id = c['id']
if not cred_id:
    c = api('/api/v1/credentials', 'POST', {
        'name': '商汤 SenseNova',
        'credentialName': 'openAIApi',
        'plainDataObj': {'openAIApiKey': SENSE_KEY},
    })
    cred_id = c['id']
print('[cred]', cred_id)

# ---------- 2. 组装节点 ----------
SYSTEM_PROMPT = """你是一名专业的中文公文与商务文档写作助手。请根据用户的需求，生成完整、可直接使用的中文文档。

写作要求：
1. 严格贴合用户要求的文种（如请假条、通知、项目大纲、工作总结、合同条款、演讲稿等），格式符合该文种的通用规范。
2. 只输出文档正文本身，不要输出任何解释性话语（不要说"以下是"、"希望对您有帮助"之类）。
3. 不要使用 Markdown 标记（不要用 #、**、```、-- 等符号），直接使用纯文本段落。标题单独成行，层级使用"一、""（一）""1."等中文序号。
4. 用户没有提供的信息（姓名、日期、部门、金额等），用【待填写】占位，不要编造真实具体的个人信息。
5. 语言简洁、正式、无明显语病；长度与文种匹配。
6. 结尾的署名与日期按公文习惯单独成行，右对齐可用空格缩进表示。"""

llm = build_node(
    'chatOpenAICustom_0', 'chatOpenAICustom',
    {
        'cache': '',
        'modelName': MODEL,
        'temperature': 0.7,
        'streaming': False,
        'maxTokens': 4096,
        'topP': '',
        'frequencyPenalty': '',
        'presencePenalty': '',
        'timeout': 180000,
        'basepath': SENSE_URL,
        'baseOptions': '',
    },
    (60, 380), credential=cred_id, label='商汤 SenseNova 6.8 Flash Lite')

prompt = build_node(
    'chatPromptTemplate_0', 'chatPromptTemplate',
    {
        'systemMessagePrompt': SYSTEM_PROMPT,
        'humanMessagePrompt': '{question}',
        'promptValues': '',
        'messageHistory': '',
    },
    (60, 20), label='文档生成提示词')

chain = build_node(
    'llmChain_0', 'llmChain',
    {
        'model': '{{chatOpenAICustom_0.data.instance}}',
        'prompt': '{{chatPromptTemplate_0.data.instance}}',
        'outputParser': '',
        'inputModeration': '',
        'chainName': '文档生成链',
    },
    (560, 200), label='文档生成链')

flow = {
    'nodes': [prompt, llm, chain],
    'edges': [
        edge('chatOpenAICustom_0', 'chatOpenAICustom',
             ['ChatOpenAI-Custom', 'BaseChatOpenAI', 'BaseChatModel', 'BaseLanguageModel', 'Runnable'],
             'llmChain_0', 'model', 'BaseLanguageModel'),
        edge('chatPromptTemplate_0', 'chatPromptTemplate',
             ['ChatPromptTemplate', 'BaseChatPromptTemplate', 'BasePromptTemplate', 'Runnable'],
             'llmChain_0', 'prompt', 'BasePromptTemplate'),
    ],
    'viewport': {'x': 0, 'y': 0, 'zoom': 0.8},
}

# ---------- 3. 创建或更新 chatflow ----------
NAME = '智能文档生成（商汤 SenseNova）'
existing = [f for f in (api('/api/v1/chatflows') or []) if f['name'] == NAME]
payload = {
    'name': NAME,
    'flowData': json.dumps(flow, ensure_ascii=False),
    'type': 'CHATFLOW',
    'deployed': False,
    'isPublic': False,
    'category': '智能文档',
}
if existing:
    fid = existing[0]['id']
    payload['id'] = fid
    res = api('/api/v1/chatflows/' + fid, 'PUT', payload)
    print('[flow] updated', fid)
else:
    res = api('/api/v1/chatflows', 'POST', payload)
    fid = res['id']
    print('[flow] created', fid)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flow_id.txt'),
          'w', encoding='utf-8') as f:
    f.write(fid)
print('FLOW_ID=' + fid)
