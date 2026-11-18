"""Measured native BEBF screen-title signatures, including dimmed frames.

Only a small title region is classified. A final score is never inferred from
an intermediate score or elapsed time. Signatures store hashes, not ROM assets.
"""
import hashlib
import struct

TITLE_RECT=(52,4,204,30)
TITLE_HASHES={
    'bdebabbd5e0d10a1116c2eb40a01ce154e61c980cbb00a7f2816e140538d72fe':'result',
    '12a41f77c4091ce8db61d9bb492fc8eabe3ab845a8fec5454b11a9149e5b3abb':'halftime',
}

# Each pair identifies two independent, fixed text/button regions. The source
# captures were inspected locally; only their threshold hashes are retained.
# Rectangles use the stacked 256x384 framebuffer, not touchscreen coordinates.
# Evidence: build/research/{continue-7,continue-10,field-0,native-screen,
# arena-play-10,field-3,native-start}.png and build/delivery/halftime.png.
SCREEN_SIGNATURES = {
    'formation_overview': (
        ((202,360,250,376),'292890ac742736af4d0bee0a548d2632747928fa96bc4806d54730fa21dd125b'),
        ((6,360,50,376),'89a7554c7c8c534324e7ff6ce4fc6c1314a244344f3f278e206daf6dd625fff5')),
    'formation_details': (
        ((208,366,252,381),'b61faa53b0a3b494d8a1963b02dcef6fb60214d1883a82ae5645898f1c9a2a19'),
        ((16,194,127,207),'ef457719f0771ce7f0bd87a18892d08f97db67b41ded7f2ac836dc73d5cd19b3')),
    'kickoff_ready': (
        ((50,195,205,224),'9edce960ae229497acf752a3597e6e8b27b3e39820e545a79b2218c8ee9a5997'),
        ((42,360,100,377),'c30d085f13a31b6cc404a41ae6df4caf7c93cb64393e4d5ef72eeb0868fc9d3c')),
    'goal_replay': (
        ((76,315,180,325),'0fec4e7976d890fe878a88809b59207e17d810ec68bcaf8ad2fe86ac2ece2e0c'),
        ((78,250,178,264),'a7b512c7788772a38012d983ec7648893ac74a8c88dc628e8b4bd98828c6eddb')),
    'stylus_prompt': (
        ((18,203,235,237),'1b0e76010e02c42a4cc60397e79c420577f5f02958e2e3ac5be838e020f77882'),
        ((100,250,228,325),'15a98b0b1cebb7740886e9abfb6673bb7a252b10659c897da111f2542887e304')),
    'defence_duel': (
        ((5,360,101,377),'a1bea77dcddaebf150d7058f11df036e12b21d43117583b3c5348414a2afb267'),
        ((150,360,249,377),'5407fa80f497f7611ed1efcb1b6736f76e59131c2767886c1941723a92cd9f40')),
    'attack_duel': (
        ((5,360,101,377),'7382d3c200f89dc1b28a7d14c69111e234c59f6beaf01c545ecd8c1ee23773de'),
        ((150,360,249,377),'27efac61f559f020459d2c5b59ee67a949f05ff0317b3fa79c9e1b6ef74b7ec5')),
    'halftime': (
        (TITLE_RECT,'12a41f77c4091ce8db61d9bb492fc8eabe3ab845a8fec5454b11a9149e5b3abb'),
        ((102,353,154,373),'c3d6eb68175a572c329bdf65739b48495052f806c042f7340468d685d1c9ce2c')),
}


def _touch_action(name, x, y):
    return {'name':name, 'frames':6, 'keys':[], 'touch':{'x':x,'y':y}}


def screen_observation(frame):
    """Expose measured UI choices; unknown frames never imply a legal action.

    Recognition is local pixel comparison, not a vision-model request and not a
    memory observation. Both region hashes must match; player identities, score
    and time are deliberately excluded from these fixed controls.
    """
    name = 'unknown'
    if frame is not None:
        for candidate, regions in SCREEN_SIGNATURES.items():
            try:
                matched = all(title_signature(green_region(frame,rect)) == digest
                              for rect,digest in regions)
            except (struct.error, IndexError, TypeError, ValueError):
                matched = False
            if matched:
                name = candidate
                break
    actions = {
        'formation_overview':[_touch_action('Suite',230,175)],
        'formation_details':[{'name':'Quitter les détails','frames':3,'keys':['B'],'touch':None}],
        'kickoff_ready':[_touch_action('Début',70,175)],
        'goal_replay':[_touch_action('Retour au match',128,128)],
        'stylus_prompt':[_touch_action('Continuer',128,96)],
        'halftime':[_touch_action('Continuer',128,170)],
        'defence_duel':[_touch_action('Blocage',55,175),_touch_action('Tacle',200,175)],
        'attack_duel':[_touch_action('Feinte',55,175),_touch_action('Dribble',200,175)],
    }.get(name,[])
    return {'name':name, 'source':'measured_frame_signature', 'actions':actions,
            'requires_tactics':name in ('defence_duel','attack_duel')}


def green_region(frame, rectangle=TITLE_RECT):
    if frame is None:return b''
    width,height,data,pitch,format_id=frame
    left,top,right,bottom=rectangle
    if width!=256 or height!=384 or not 0<=left<right<=width or not 0<=top<bottom<=height:
        return b''
    values=bytearray()
    for y in range(top,bottom):
        if format_id==1:
            values.extend(data[y*pitch+left*4+1:y*pitch+right*4:4])
        elif format_id in (0,2):
            raw=struct.unpack_from('<'+'H'*(right-left),data,y*pitch+left*2)
            maximum=63 if format_id==2 else 31
            values.extend(((pixel>>5)&maximum)*255//maximum for pixel in raw)
        else:return b''
    return bytes(values)


def title_signature(values):
    if not values or max(values)-min(values)<8:return None
    threshold=min(values)+(max(values)-min(values))*2//3
    return hashlib.sha256(bytes(value>threshold for value in values)).hexdigest()


def screen_phase(frame):
    return TITLE_HASHES.get(title_signature(green_region(frame)))
