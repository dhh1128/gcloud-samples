import os, sys, requests, re, json

_api_key = None
def _get_api_key():
    global _api_key
    if _api_key is None:
        api_key_file = os.path.expanduser('~/.gcloud/myapp.api-key')
        if not os.path.isfile(api_key_file):
            raise Exception('''
    You have to configure credentials before this script will work properly.
    Define an application for your account in the Google Cloud Platform
    console. Then look up the application's API key and store its value in
    %s.
    
    (It's highly recommended that you restrict access to this file, such that
    it cannot be read, written, or deleted except by your account.)
    ''' % api_key_file)
        with open(api_key_file, 'r') as f:
            _api_key = f.read().strip()
    return _api_key


_html_pat = re.compile(r'</?(html|body|p|table|tr|td|li|em|strong|b|i|style|script|head|meta|dl|dt|dd|object)(\s+[a-z]+="[^"]*")*\s*/?>', re.I)
def is_html(text):
    i = 0
    for match in _html_pat.finditer(text):
        i += 1
        if i >= 2:
            return True


def raise_if_response_is_an_error(resp):
    if resp.status_code < 200 or resp.status_code > 299:
        x = json.loads(resp.text)['error']
        msg = 'Error %d: %s' % (resp.status_code, x['message'])
        first_error = x['errors'][0]
        if 'extendedHelp' in first_error:
            msg += ' For more help, see %s.' % first_error['extendedHelp']
        raise Exception(msg)


class google_translator:
    '''
    Transparently manages access to the Google Translate web service,
    including both language detection and translation.
    
    Requires a password in an external data file, plus some simple account
    setup as documented at http://j.mp/1STVStv.
    '''
    def __init__(self, should_trace=True):
        self._access_token = None
        self.should_trace = should_trace
        
    def trace(self, msg):
        if self.should_trace:
            print(msg)
            
    def detect_lang(self, text):
        uri = 'https://www.googleapis.com/language/translate/v2/detect'
        self.trace('GET %s' % uri)
        resp = requests.get(uri, params=[('key', _get_api_key()), ('q', text)])
        print(resp.text)
        raise_if_response_is_an_error(resp)
        return json.loads(resp.text)['data']['detections'][0]
    
    def translate(self, text, source_lang_code, target_lang_code, fmt=None):
        uri = 'https://www.googleapis.com/language/translate/v2'
        method = 'GET'
        if len(text) >= 2048:
            if len(text) >= 5*1024:
                raise Exception('Max text size = 5k')
            method = 'POST'
        if fmt is None:
            fmt = 'text'
            if is_html(text):
                fmt = 'html'
        self.trace('%s %s (format=%s)' % (method, uri, fmt))
        args=[('key', _get_api_key()),
              ('format', fmt),
              ('source', source_lang_code),
              ('target', target_lang_code),
              ('q', text)]
        if method == 'GET':
            resp = requests.get(uri, params=args)
        else:
            resp = requests.post(uri, params=args, headers={'X-HTTP-Method-Override': 'GET'})
        x = json.loads(resp.text)
        print(resp.text)
        raise_if_response_is_an_error(resp)
        return x['data']['translations'][0]['translatedText']
    
if __name__ == '__main__':
    # Make sure we have credentials configured properly.
    _get_api_key()
    gt = google_translator()
    gt.detect_lang('This is a test; how well do you handle it?')
    try:
        while True:
            sys.stdout.write('Enter some English text (blank line to finish, CTRL+C to abort): ')
            src_txt = ''
            while True:
                line = raw_input().strip()
                if not line:
                    break
                src_txt = src_txt + line + '\n'
            tgt_txt = gt.translate(src_txt.rstrip(), 'en', 'es')
            print(tgt_txt)
    except KeyboardInterrupt:
        sys.stdout.write('\n')
        
