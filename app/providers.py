import json
import time
import uuid
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import config
from .receipts import receipt, digest

class ProviderError(Exception):
    pass

def request_json(url, headers=None, body=None, timeout=90):
    req = Request(url, headers=headers or {}, data=json.dumps(body).encode() if body is not None else None,
                  method='POST' if body is not None else 'GET')
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        # Provider payloads can echo prompts, account data or credentials. Do not log them.
        raise ProviderError(f'Provider returned HTTP {error.code}. Check endpoint, credentials and permissions.') from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError('Provider could not be reached or timed out.') from None

def zetaris_query(sql, run_id=None):
    c = config()
    if not c.get('ZETARIS_API_KEY') or not c.get('ZETARIS_ORG_ID'):
        raise ProviderError('Set ZETARIS_API_KEY and the numeric ZETARIS_ORG_ID in .env.local.')
    headers = {'Authorization': 'Bearer ' + c['ZETARIS_API_KEY'], 'X-Org-ID': c['ZETARIS_ORG_ID'],
               'Content-Type': 'application/json', 'X-Request-ID': str(uuid.uuid4())}
    result = request_json(c['ZETARIS_BASE_URL'].rstrip('/') + '/api/proxy/sql-editor/sqls/run-query',
                          headers, {'sql': sql, 'limit': 1000})
    if run_id:
        receipt(run_id, 'zetaris_query', {'sql': sql, 'result_hash': digest(result)})
    return result

def chat(messages, run_id, provider='nebius', max_tokens=3000,thinking=None,model_override=None):
    c = config()
    prefix = 'NEBIUS' if provider == 'nebius' else 'NIGHTSHIFT'
    model = c.get('NEMOTRON_MODEL') if provider == 'nebius' else c.get('NIGHTSHIFT_MODEL')
    if model_override is not None:
        if provider!='nightshift' or model_override not in ('meterless/auto','meterless/fast','meterless/deep','meterless/text'): raise ProviderError('Unsupported routing override.')
        model=model_override
    base = c.get(prefix + '_BASE_URL', '').rstrip('/')
    key = c.get(prefix + '_API_KEY', '')
    if not base or not model or not key:
        raise ProviderError(f'{provider} is not configured. Set its endpoint and model in .env.local.')
    if provider=='nightshift':
        if '://' not in base: base='http://'+base
        parsed=urlparse(base)
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ProviderError('Nightshift endpoint must not contain credentials, a query string or a fragment.')
        base=parsed.scheme+'://'+parsed.netloc+'/v1'
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    if provider=='nightshift':
        headers.update({'meterless-app':'unitshift','meterless-scope':'user'})
    body = {'model': model, 'messages': messages, 'temperature': 0, 'max_tokens': max_tokens}
    if thinking is not None:
        body['chat_template_kwargs']={'enable_thinking':bool(thinking)}
        if thinking: body['chat_template_kwargs'].update({'low_effort':True,'reasoning_budget':2048})
    started = time.monotonic()
    result = request_json(base + '/chat/completions', headers, body, timeout=180 if provider=='nightshift' else 120)
    try:
        content = result['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError()
    except (KeyError, IndexError, ValueError, TypeError):
        receipt(run_id,'model_call_failed',{'provider':provider,'model':model,'finish_reason':(result.get('choices') or [{}])[0].get('finish_reason'),
                 'usage':result.get('usage',{}),'thinking':thinking,'elapsed_s':round(time.monotonic()-started,3)})
        raise ProviderError('Model returned no decision text within its output allowance. No plan was executed.') from None
    routing=result.get('meterless') or {}
    route_evidence={key:routing.get(key) for key in ('receipt_id','decision_id','routed_model','winning_route') if routing.get(key) is not None}
    receipt(run_id, 'model_call', {'provider': provider, 'model': model, 'effective_model':result.get('model'),
                                  'routing':route_evidence, 'elapsed_s': round(time.monotonic()-started, 3),
                                  'thinking':thinking,
                                  'usage': result.get('usage', {}), 'input_hash': digest(messages),
                                  'output_hash': digest(content), 'response_id': result.get('id')})
    return content

def parse_json(content):
    text = content.strip()
    if '<think>' in text:
        text = text.split('</think>')[-1].strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        raise ProviderError('Model output was not valid JSON; no contract was executed.') from None
