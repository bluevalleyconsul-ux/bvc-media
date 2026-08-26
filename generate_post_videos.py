#!/usr/bin/env python3
"""
BVC Social Video Generator v7.1
CDN: Backblaze B2 (primary) -> GitHub raw (IG/FB only) -> GHL CDN (last resort)
TikTok ONLY posts when B2 is active — GitHub raw rejected by TikTok domain policy.
Set B2_KEY_ID + B2_APP_KEY secrets to enable TikTok publishing.
"""
import os, sys, time, asyncio, requests, subprocess, base64, hashlib
from io import BytesIO
from datetime import datetime, timedelta, timezone
from PIL import Image

# ---- CONFIG ----
GHL_KEY = os.environ.get('GHL_API_KEY') or 'pit-e62a79f2-ec35-476f-9ad6-20b13d4ef298'
LOC_ID = 'DTacLMrxrP6l6lwZzEXS'
USER_ID = 'V28tkh3UNvOFjW0VPeNY'
VOICE = 'en-US-JennyNeural'
TK_ACCT = '6a8a64b7420254dd1829bde0_DTacLMrxrP6l6lwZzEXS_000mxYTwYvZ2tReVszHUrTu6InZ5vev5d_business'
IG_ACCT = '6a85c05ed4b88212be124fe4_DTacLMrxrP6l6lwZzEXS_17841431864857525'
FB_ACCT = '6a85d61b8665eb87e71baa29_DTacLMrxrP6l6lwZzEXS_1301490373043749_page'
GHL_BASE = 'https://services.leadconnectorhq.com'
GH_TOKEN = os.environ.get('GITHUB_TOKEN') or ''
GH_OWNER = 'bluevalleyconsul-ux'
GH_REPO = 'bvc-media'
FALLBACK = 'https://assets.cdn.filesafe.space/DTacLMrxrP6l6lwZzEXS/media/967984b9-90ea-4369-b445-6f00d1c56183.mp4'

# ---- BACKBLAZE B2 (optional — free 10GB, $0 egress via Cloudflare) ----
B2_KEY_ID = os.environ.get('B2_KEY_ID') or ''
B2_APP_KEY = os.environ.get('B2_APP_KEY') or ''
B2_BUCKET = os.environ.get('B2_BUCKET') or 'bvc-videos'

# ---- DYNAMIC SCHEDULE: tomorrow 14:00-23:00 UTC ----
_now = datetime.now(timezone.utc)
_base = (_now + timedelta(days=1)).date()
def sched(hour, extra_min=0):
    dt = datetime(_base.year, _base.month, _base.day, hour, extra_min, 0, tzinfo=timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')

print('BVC v7.1 | key={} | base={}'.format(GHL_KEY[:20], _base))
print('CDN: B2={} | GH={} | TK={}'.format(
    'READY' if B2_KEY_ID else 'skip',
    'READY' if GH_TOKEN else 'missing',
    'ENABLED' if B2_KEY_ID else 'SKIP-no-B2'
))

# ---- POST DATA ----
POSTS = [
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504603318/d839dfc5-7be5-4ef2-a681-a2eefc63351d.png',
     'Breaking. Millions in unclaimed Florida foreclosure surplus is sitting in government accounts right now. If your home was foreclosed in the last five years and sold for more than you owed, that money may be yours. Average claim: thirty to one hundred fifty thousand dollars. Zero upfront. D M CLAIM for a free case review. Blue Valley Consult.',
     'BREAKING: Millions in unclaimed foreclosure surplus RIGHT NOW.\nForeclosed in last 5 yrs? That money is YOURS.\nAvg $30K-$150K. Zero upfront.\nDM CLAIM - Free review.\n#ExcessFunds #ForeclosureRecovery #BlueValleyConsult', 14),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504596968/a8f06242-d827-4f2f-b9ea-b80cd30b0f39.png',
     'Why did not the bank tell you about your surplus? Because they did not have to. When your home sold at foreclosure for more than you owed, the rest went into a government trust account. That money belongs to YOU. D M WHY for a free five minute review. Blue Valley Consult.',
     'Why did the bank NOT tell you?\nThat surplus went to a government account. It is YOURS.\nDM WHY - Free 5 min review.\n#ExcessFunds #KnowYourRights #FloridaLaw #BlueValleyConsult', 15),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504596950/2bcfbc17-f52a-4b76-a91f-c24340ac20a4.png',
     'How much time do you have to claim your surplus? Every Florida county has a different deadline. Some close in one year. Some in five. Once the deadline passes the state keeps your money forever. D M DEADLINE for a free check. Blue Valley Consult.',
     'How much time do you HAVE?\nEvery FL county = different deadline.\nOnce it passes state keeps it FOREVER.\nDM DEADLINE - Free check 5 min.\n#LegalDeadline #FloridaLaw #ActNow #BlueValleyConsult', 16),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504602806/23c4c682-b6e8-4654-b4fb-b56c7e513687.png',
     'Four simple steps after you call Blue Valley Consult. We pull your case on the phone. If surplus exists we send our agreement same day. You sign we file. Sixty to one hundred twenty days later your check arrives. Zero upfront. D M CALL. Blue Valley Consult.',
     '4 steps after you call BVC:\n1. Pull case live 5 min\n2. Agreement same day\n3. You sign, we file\n4. Check in 60-120 days\nDM CALL - Zero upfront.\n#TheProcess #ExcessFunds #BlueValleyConsult', 17),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504603357/b7072396-78b7-43b7-b47e-c88c90485338.png',
     'Real Florida homeowners. Real money recovered. Broward County ninety four thousand dollars. Miami Dade sixty seven thousand five hundred. Palm Beach one hundred thirty one thousand dollars. D M RESULTS for your free eligibility check. Blue Valley Consult.',
     'Real FL clients. Real checks.\n$94K Broward | $67.5K Miami-Dade | $131K Palm Beach\nDM RESULTS - Free eligibility check.\n#ClientWins #RealResults #ExcessFunds #BlueValleyConsult', 18),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504596844/80478d72-464c-4193-9086-8f0e33505729.png',
     'You only need four documents. Proof of identity. Proof you were the homeowner. Your foreclosure case number which we can find for you. Your signature. That is all. We handle everything else. Zero upfront. D M DOCS to start today. Blue Valley Consult.',
     'Only 4 documents to start:\nID + Proof of ownership + Case number + Signature\nWe handle the rest. Zero upfront.\nDM DOCS - Start today.\n#SimpleProcess #ExcessFunds #BlueValleyConsult', 19),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504594834/e785991c-6d21-47e0-8234-e43ffe5e286c.png',
     'The bank foreclosed your home. The court sold it. The surplus disappeared. Or did it? In Florida that money goes into a government account and it is legally yours. D M SURPLUS for a free check. Blue Valley Consult.',
     'Bank foreclosed. Court sold. Surplus disappeared.\nOR DID IT?\nIn FL it goes to a government account. It is YOURS.\nDM SURPLUS - Free check 5 min.\n#DontLetThemKeepIt #ExcessFunds #BlueValleyConsult', 20),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504602383/faae6812-9e6c-4043-96d4-dde398747af3.png',
     'Most foreclosure attorneys will not take your surplus case. Blue Valley Consult specializes exclusively in excess funds recovery. Five star rated. Number one for three years running. Five hundred plus cases across all sixty seven Florida counties. D M SPECIALIST. Blue Valley Consult.',
     'Most attorneys will not take your case.\nWe ONLY do excess funds. 5 Stars | #1 | 500+ Cases | All 67 FL counties.\nDM SPECIALIST - Free review.\n#Specialist #ExcessFunds #BlueValleyConsult', 21),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504627925/ef1465bd-08d4-46f9-841f-8af27e1e52e1.png',
     'This week only. Ten free priority case review slots available. We pull your records on the call in five minutes. We tell you exactly how much surplus may exist. We start your claim same day. Zero upfront. D M PRIORITY right now. Blue Valley Consult.',
     'THIS WEEK ONLY - 10 Free Priority Slots\nPull records live 5 min, know your surplus, start claim same day.\nDM PRIORITY - Slots filling fast.\n#LimitedSlots #ActNow #ExcessFunds #BlueValleyConsult', 22),
    ('https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-images/1787504630297/9e847782-6c74-4671-837f-2fb29a79fefc.png',
     'This is your final chance. If your home was foreclosed in Florida in the last five years there may be money in a government account with your name on it. Average recovery thirty to one hundred fifty thousand dollars. Zero upfront. D M REVIEW right now. Blue Valley Consult.',
     'FINALE - Last chance to claim what is YOURS.\nAvg $30K-$150K | All 67 FL counties | Zero upfront.\nDM REVIEW RIGHT NOW.\nBlue Valley Consult - FL Foreclosure Specialists\n#FreeConsultation #ActNow #BlueValleyConsult', 23),
]

async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE).save(path)

def tts_gen(text, path):
    print(' [TTS] generating...')
    asyncio.run(_tts(text, path))
    print(' [TTS] {}KB'.format(os.path.getsize(path)//1024))

def dl_img(url, out):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content)).convert('RGB')
    img = img.resize((1080, 1920), Image.LANCZOS)
    img.save(out, 'JPEG', quality=95)
    print(' [IMG] {}KB'.format(os.path.getsize(out)//1024))

def make_vid(img, audio, out):
    cmd = ['ffmpeg','-y','-loop','1','-framerate','24','-i',img,
           '-i',audio,'-c:v','libx264','-preset','fast','-crf','28',
           '-c:a','aac','-b:a','128k','-pix_fmt','yuv420p','-shortest',out]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0: raise RuntimeError('ffmpeg: '+r.stderr[-150:])
    print(' [VID] {}KB'.format(os.path.getsize(out)//1024))

# ============================================================
# BACKBLAZE B2 — free 10GB, no egress fees, native API v2
# ============================================================
def upload_to_b2(path, fname):
    """Upload to Backblaze B2 public bucket. Returns CDN URL or None on failure."""
    if not B2_KEY_ID or not B2_APP_KEY:
        return None
    try:
        creds = base64.b64encode('{}:{}'.format(B2_KEY_ID, B2_APP_KEY).encode()).decode()
        auth = requests.get(
            'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
            headers={'Authorization': 'Basic {}'.format(creds)},
            timeout=15
        ).json()
        if 'apiUrl' not in auth: raise RuntimeError('auth failed: {}'.format(auth.get('message','?')))
        api_url = auth['apiUrl']
        auth_token = auth['authorizationToken']
        dl_url = auth['downloadUrl']
        bl = requests.post(
            '{}/b2api/v2/b2_list_buckets'.format(api_url),
            headers={'Authorization': auth_token},
            json={'accountId': auth['accountId'], 'bucketName': B2_BUCKET},
            timeout=15
        ).json()
        if not bl.get('buckets'): raise RuntimeError('bucket "{}" not found'.format(B2_BUCKET))
        bucket_id = bl['buckets'][0]['bucketId']
        up = requests.post(
            '{}/b2api/v2/b2_get_upload_url'.format(api_url),
            headers={'Authorization': auth_token},
            json={'bucketId': bucket_id},
            timeout=15
        ).json()
        with open(path, 'rb') as f:
            data = f.read()
        sha1 = hashlib.sha1(data).hexdigest()
        res = requests.post(
            up['uploadUrl'],
            headers={
                'Authorization': up['authorizationToken'],
                'X-Bz-File-Name': fname,
                'Content-Type': 'video/mp4',
                'Content-Length': str(len(data)),
                'X-Bz-Content-Sha1': sha1
            },
            data=data,
            timeout=120
        ).json()
        if 'fileId' not in res: raise RuntimeError('upload failed: {}'.format(res.get('message','?')))
        pub = '{}/file/{}/{}'.format(dl_url, B2_BUCKET, fname)
        print(' [B2] {}B -> {}'.format(res.get('contentLength','?'), pub))
        return pub
    except Exception as e:
        print(' [B2] FAIL: {} -> trying GitHub...'.format(e))
        return None

# ============================================================
# GITHUB API — IG/FB fallback (NOT used for TikTok)
# ============================================================
def upload_github(path, fname):
    if not GH_TOKEN: raise RuntimeError('GITHUB_TOKEN missing')
    api = 'https://api.github.com/repos/{}/{}/contents/media/{}'.format(GH_OWNER, GH_REPO, fname)
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    r = requests.put(api,
        headers={'Authorization': 'token '+GH_TOKEN, 'Accept': 'application/vnd.github.v3+json'},
        json={'message': 'Add '+fname, 'content': b64},
        timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError('HTTP {}: {}'.format(r.status_code, r.text[:80]))
    raw = 'https://raw.githubusercontent.com/{}/{}/main/media/{}'.format(GH_OWNER, GH_REPO, fname)
    print(' [GH] {} -> {}'.format(r.status_code, raw))
    return raw

# ============================================================
# UPLOAD CHAIN: B2 -> GitHub (IG/FB) -> GHL CDN
# Returns (url, is_b2):
#   is_b2=True  -> video on B2, safe for ALL platforms incl. TikTok
#   is_b2=False -> video on GitHub raw or GHL CDN, TikTok will be SKIPPED
# ============================================================
def upload(path, fname):
    url = upload_to_b2(path, fname)          # 1. Backblaze B2 (all platforms)
    if url:
        return url, True
    try:
        return upload_github(path, fname), False  # 2. GitHub raw (IG + FB only)
    except Exception as e:
        print(' [GH] FAIL: {} -> GHL CDN'.format(e))
        return FALLBACK, False               # 3. GHL CDN static (last resort)

H = {'Authorization': 'Bearer '+GHL_KEY, 'Content-Type': 'application/json', 'Version': '2021-07-28'}

def ghl_post(acct, vurl, caption, scheduled, extra=None):
    body = {'accountIds': [acct], 'summary': caption,
            'media': [{'url': vurl, 'type': 'video/mp4', 'thumbnail': '', 'defaultThumb': ''}],
            'status': 'scheduled', 'scheduleDate': scheduled, 'type': 'post', 'userId': USER_ID}
    if extra: body.update(extra)
    r = requests.post(GHL_BASE+'/social-media-posting/'+LOC_ID+'/posts', headers=H, json=body, timeout=30)
    print(' GHL {} | {}'.format(r.status_code, r.text[:80]))
    if r.status_code not in (200, 201): raise RuntimeError('GHL {} {}'.format(r.status_code, r.text[:100]))
    return r.status_code

def main():
    os.makedirs('out', exist_ok=True)
    ts = int(time.time())
    tk_enabled = bool(B2_KEY_ID)
    mode = 'B2+GitHub+GHL' if B2_KEY_ID else 'GitHub+GHL (TikTok=SKIP)'
    print('\nBVC v7.1 | {} posts | base={} | ts={} | CDN={}'.format(
        len(POSTS), _base, ts, mode))
    if not tk_enabled:
        print('WARNING: TikTok disabled — B2_KEY_ID secret not set. Set B2_KEY_ID + B2_APP_KEY to enable.\n')

    results = []
    for i, (img_url, tts_text, caption, hour) in enumerate(POSTS, 1):
        tk_s = sched(hour)
        ig_s = sched(hour, 5)
        fb_s = sched(hour, 10)
        a = 'out/a{}.mp3'.format(i)
        j = 'out/i{}.jpg'.format(i)
        v = 'out/v{}.mp4'.format(i)
        fn = 'bvc_{}_{:02d}.mp4'.format(ts, i)
        print('\n{}\nPOST {}/10 | TK={} | CDN={}\n{}'.format(
            '='*55, i, tk_s, mode, '='*55))
        ok = True
        try:
            tts_gen(tts_text, a)
            dl_img(img_url, j)
            make_vid(j, a, v)
            vurl, is_b2 = upload(v, fn)
            print(' URL: {} | B2={}'.format(vurl, is_b2))

            # TikTok: ONLY post when video is on B2 (GitHub raw domain not verified by TikTok)
            if is_b2:
                ghl_post(TK_ACCT, vurl, caption, tk_s, {
                    'tiktokPostDetails': {
                        'privacyLevel': 'PUBLIC_TO_EVERYONE',
                        'enableComment': True,
                        'enableDuet': True,
                        'enableStitch': True
                    }
                })
                print(' TK OK')
            else:
                print(' TK SKIP: GitHub CDN rejected by TikTok — set B2_KEY_ID + B2_APP_KEY secrets to enable.')

            # Instagram and Facebook: GitHub raw is accepted
            ghl_post(IG_ACCT, vurl, caption, ig_s, {
                'instagramPostDetails': {'type': 'reel', 'showOnFeed': True}
            })
            ghl_post(FB_ACCT, vurl, caption, fb_s)
            print(' POST {} OK'.format(i))
        except Exception as e:
            ok = False
            print(' POST {} FAIL: {}: {}'.format(i, type(e).__name__, e))
        results.append(ok)
        time.sleep(3)

    ok_n = sum(results)
    print('\n{}\nDONE {}/{} | CDN={}'.format('='*55, ok_n, len(POSTS), mode))
    for idx, r in enumerate(results, 1):
        print('  POST {:02d}: {}'.format(idx, 'OK' if r else 'FAIL'))
    if ok_n < len(POSTS):
        sys.exit(1)

if __name__ == '__main__':
    main()
