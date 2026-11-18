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
    # Isolated checkpoint comparisons in build/pilot-smoke show that A
    # advances both the versus card and the two observed pitch dialogue pages.
    'versus_intro': (
        ((101,264,154,306),'b8731379ba066eacecc91337eb997f73aee2898a71264bcbb961fac4371ef437'),
        ((105,317,151,356),'a037394f889a442662f2ae7b7ce7d137907341ab9cfe10d8898b6ebdbad14c34')),
    'pitch_dialogue_confirm': (
        ((0,360,7,384),'339c901b442b9b4ecfa7286c2eec9374a2a8f194a78871c6ce61b5728d5192a8'),
        ((249,360,256,384),'5835d7ddc103635ad5c37678abf449b82846afcd08de0bc0a3912cbfa569cbc6')),
    'formation_overview': (
        ((202,360,250,376),'292890ac742736af4d0bee0a548d2632747928fa96bc4806d54730fa21dd125b'),
        ((6,360,50,376),'89a7554c7c8c534324e7ff6ce4fc6c1314a244344f3f278e206daf6dd625fff5')),
    'formation_details': (
        ((208,366,252,381),'b61faa53b0a3b494d8a1963b02dcef6fb60214d1883a82ae5645898f1c9a2a19'),
        ((16,194,127,207),'ef457719f0771ce7f0bd87a18892d08f97db67b41ded7f2ac836dc73d5cd19b3')),
    'kickoff_ready': (
        ((50,195,205,224),'9edce960ae229497acf752a3597e6e8b27b3e39820e545a79b2218c8ee9a5997'),
        ((42,360,100,377),'c30d085f13a31b6cc404a41ae6df4caf7c93cb64393e4d5ef72eeb0868fc9d3c')),
    'kickoff_ready_zeus': (
        ((50,195,205,224),'4f47ec48e2b769097d1973e2f35d8a51c51828df124164ec0689926cdd54a020'),
        ((42,360,100,377),'c30d085f13a31b6cc404a41ae6df4caf7c93cb64393e4d5ef72eeb0868fc9d3c')),
    # Native kickoff pass prompt, measured on field-1.png and field-2.png.
    'kickoff_pass': (
        ((40,193,128,207),'1359e4d2a29c8f2646f1a55ff7167f922551f203d5acd30e085ce8ae9fb4b62d'),
        ((128,193,216,207),'d83b709fc0934c219ff96c5836932c0369b15f33de35d1b9a57626a216003191'),
    ),
    'kickoff_pass_live': (
        ((40,193,128,207),'2bd4fd685f31f940bca1f07d0056fdba215993fc4e0862ac19e2d1879e7d81c2'),
        ((128,193,216,207),'eea59052fe38c53ad1952c951fe90c0c327f02abd0ec69f4ccd5d5cf94cdd6b0'),
    ),
    'kickoff_pass_forward': (
        ((40,193,128,207),'05f58f402ec33784e6f99aa0445d9f4fe5a74cfa5aaa76175eb582ecc34bf1ae'),
        ((128,193,216,207),'eb83f5a4337f39629bc1b5a2aeb13b6b50c52e9aedb6d3ec1315c2cf674ac613'),
    ),
    'kickoff_pass_forward_live': (
        ((40,193,128,207),'1f9ab145eae820bb270af153eeebe8aa3c2b5f3ce21b58d46c12b70c6751afc0'),
        ((128,193,216,207),'f497f1fae383ba4803977fb61c5778dde681a808596c11ede08f25b8518746fc'),
    ),
    'native_pitch_dialogue': (
        ((0,348,6,376),'68b16565822675e20d1f067ebe105360c7085c2b3f54dd9eecdb25c74934a57f'),
        ((250,348,256,376),'d8d48c260be87a84a35bded811dbd5794b33fa5e4de818f2a885aefe5167403a'),
    ),
    # Fixed borders inside the dialogue box, independent of speaker and pitch.
    'native_pitch_dialogue_box': (
        ((1,340,5,360),'dce3e08478ba004ca35a9a141e71b67815eae4b1f476d1659a663968412c35e0'),
        ((4,379,110,384),'52ed44e42135492503e620d6a2000306e695d32d4790fe250e0a61b0f5a394e1'),
    ),
    'goal_replay': (
        ((76,315,180,325),'0fec4e7976d890fe878a88809b59207e17d810ec68bcaf8ad2fe86ac2ece2e0c'),
        ((78,250,178,264),'a7b512c7788772a38012d983ec7648893ac74a8c88dc628e8b4bd98828c6eddb')),
    'stylus_prompt': (
        ((18,203,235,237),'1b0e76010e02c42a4cc60397e79c420577f5f02958e2e3ac5be838e020f77882'),
        ((100,250,228,325),'15a98b0b1cebb7740886e9abfb6673bb7a252b10659c897da111f2542887e304')),
    'defence_duel': (
        ((5,360,101,377),'a1bea77dcddaebf150d7058f11df036e12b21d43117583b3c5348414a2afb267'),
        ((150,360,249,377),'5407fa80f497f7611ed1efcb1b6736f76e59131c2767886c1941723a92cd9f40')),
    'defence_duel_contact': (
        ((5,360,101,377),'bc610ddb6efd26a4fd740af9a8dd39dcd9e969d93c6e83aefb800ae16251e9f6'),
        ((150,360,249,377),'5407fa80f497f7611ed1efcb1b6736f76e59131c2767886c1941723a92cd9f40')),
    'keeper_duel': (
        ((5,360,101,377),'4831574cf137df3d780fbe7b37ddad30e0c88f28123defb5efb9a3848ab3aa42'),
        ((150,360,249,377),'64574f4c4859e0856ded3ddd2f62e9280dff0fba2bf4a389d6ad9d10a56a16ba')),
    'shot_block_menu': (
        ((5,360,73,376),'3b114f29e3398a1b873120ee556e6b4ed267c0d3775692ad365d495ad9ecba58'),
        ((227,315,244,333),'0db629f1103369988298a2fc0287edf8ef9abbdc515304a0d10bc274911a72a0')),
    'attack_duel': (
        ((5,360,101,377),'7382d3c200f89dc1b28a7d14c69111e234c59f6beaf01c545ecd8c1ee23773de'),
        ((150,360,249,377),'27efac61f559f020459d2c5b59ee67a949f05ff0317b3fa79c9e1b6ef74b7ec5')),
    'attack_duel_dodge': (
        ((5,360,101,377),'f00b151f29f442016373fb75efe902ab3d007840f4246504024526ffb6735223'),
        ((150,360,249,377),'27efac61f559f020459d2c5b59ee67a949f05ff0317b3fa79c9e1b6ef74b7ec5')),
    'halftime': (
        (TITLE_RECT,'12a41f77c4091ce8db61d9bb492fc8eabe3ab845a8fec5454b11a9149e5b3abb'),
        ((102,353,154,373),'c3d6eb68175a572c329bdf65739b48495052f806c042f7340468d685d1c9ce2c')),
}

SCREEN_ALIASES = {
    'kickoff_pass_live': 'kickoff_pass',
    'kickoff_pass_forward_live': 'kickoff_pass_forward',
    'kickoff_ready_zeus': 'kickoff_ready',
    'native_pitch_dialogue_box': 'pitch_dialogue_confirm',
}

PASS_PROMPT = (
    ((42,194,128,207),'5c02b413d1cab97b7cf008ae864a32c5425c76202f82ab05ae1090c79d0a0f65'),
    ((128,194,215,207),'c6362fd5c83321cba3cf31c8a89379ab50442c9571d8f85e6c5c7d15634c99c8'),
)
POSITION_HINT = (
    ((63,209,128,223),'0dfb9fd3cb435d566e5819e74b4fc04d30b75c0afb6ad55b63af520f159783b8'),
    ((128,209,194,223),'6f79e81a45cd5930296566278b599564453567e965aa0853e25f6fe599b85b28'),
)
POSITION_BUTTONS = {
    '3c83cedc1949d281c191e213f71ac4747d010efeb51b304e3921aa5baea25ee7': 'restart_ready',
    'c30d085f13a31b6cc404a41ae6df4caf7c93cb64393e4d5ef72eeb0868fc9d3c': 'kickoff_ready',
}
GOAL_REPLAY_TITLES = {
    '3841f10729af082514387fe479b78af3b31c5d6ebda31f29a78a603d4452caee',  # Tir ricochets
    'c08a91abe8c089f1a5f51d3d034a456f45bf79fc0d63234333c69867f5bc34ee',  # Portique mystère
}
SCOREBOARD_PERIOD_TITLES = {
    'd6f30891fc98d999bb120a734eaa9dbb4cc1d991c2f965aaf5d26567cffe9a05',
    'c23af18ccfe0e96cec8f6a350ef1f6bcbb2a36d46270cb1b7b05b5892c2f18e8',
}


def white_text_signature(frame, rect):
    return hashlib.sha256(bytes(value >= 240 for value in green_region(frame, rect))).hexdigest()


def matches_white_text(frame, signature):
    return all(white_text_signature(frame, rect) == digest for rect, digest in signature)

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
                name = SCREEN_ALIASES.get(candidate, candidate)
                break
        if name == 'unknown':
            position_screen = POSITION_BUTTONS.get(title_signature(green_region(frame, (42,360,100,377))))
            if position_screen and matches_white_text(frame, POSITION_HINT):
                name = position_screen
            elif matches_white_text(frame, PASS_PROMPT):
                name = 'pass_prompt'
            elif title_signature(green_region(frame, (85,0,172,15))) in SCOREBOARD_PERIOD_TITLES:
                if (title_signature(green_region(frame, (3,196,71,212))) ==
                        '063478b63ba043f292cb4ff8a3ca31244c6265dea6ece233e67ef423f2d0b044'):
                    name = 'goal_replay_video'
                elif white_text_signature(frame, (48,352,210,377)) in GOAL_REPLAY_TITLES:
                    name = 'goal_replay_technique'
                elif not any(green_region(frame, (0,192,256,384))):
                    name = 'scoreboard_transition'
    actions = {
        'formation_overview':[_touch_action('Suite',230,175)],
        'versus_intro':[{'name':'Ouvrir la formation','frames':6,'keys':['A'],'touch':None}],
        'formation_details':[{'name':'Quitter les détails','frames':3,'keys':['B'],'touch':None}],
        'kickoff_ready':[_touch_action('Début',70,175)],
        'restart_ready':[_touch_action('Reprendre la remise en jeu',70,175)],
        'kickoff_pass':[_touch_action('Engager vers la gauche',68,132)],
        'kickoff_pass_forward':[_touch_action('Engager vers l’avant',128,96)],
        'pass_prompt':[_touch_action('Passer vers l’avant',150,55)],
        'native_pitch_dialogue':[{'name':'Avancer le dialogue natif','frames':3,'keys':['A'],'touch':None}],
        'pitch_dialogue_confirm':[{'name':'Avancer le dialogue natif','frames':6,'keys':['A'],'touch':None}],
        'goal_replay':[_touch_action('Retour au match',128,128)],
        'goal_replay_technique':[_touch_action('Retour au match',128,128)],
        'stylus_prompt':[_touch_action('Continuer',128,96)],
        'halftime':[_touch_action('Continuer',128,170)],
        'defence_duel':[_touch_action('Blocage',55,175),_touch_action('Tacle',200,175)],
        'defence_duel_contact':[_touch_action('Contact',55,175),_touch_action('Tacle',200,175)],
        'keeper_duel':[_touch_action('Arrêt',55,175),_touch_action('Coup de poing',200,175)],
        'shot_block_menu':[_touch_action('Pied céleste',55,175)],
        'attack_duel':[_touch_action('Feinte',55,175),_touch_action('Dribble',200,175)],
        'attack_duel_dodge':[_touch_action('Esquive',55,175),_touch_action('Dribble',200,175)],
    }.get(name,[])
    return {'name':name, 'source':'measured_frame_signature', 'actions':actions,
            'requires_tactics':name in ('defence_duel','defence_duel_contact','keeper_duel',
                                        'attack_duel','attack_duel_dodge')}


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
