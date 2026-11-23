"""Club organiser: native actor interaction and native yes/no offers.

1000F is a bounded fixture mailbox, acknowledged by ClubBridge before the
native event may launch. The same measured slots as the dynamic arena are used.
"""
from ssd import Program, helper_prefix, expression, variable, string
from club_fixtures import CLUB_FIXTURE, FIXTURES
from recruitment_rom import FIRST_RECRUIT_ID
from scene_team import emit_dynamic_removals

RECRUIT_UNIT = 0x10010
RECRUIT_LEVEL = 0x10011
RECRUIT_SLOT = 0x10012
RECRUIT_READY = 0x10013


def event_pair(ssd, sst, config):
    p = Program(*helper_prefix(ssd, sst))
    text_id = 500

    def say(text, portrait=261, question=False):
        nonlocal text_id
        if question:
            # Same choice-message setup as chapter 21010000, callback 102C.
            p.emit(0x306B, 4)
            p.emit(0x301C, 5, 1, 0, 0, 0, 0)
        else:
            p.emit(0x301A, 1, portrait, 0, 1, 0, -1)
        row = p.emit(0x301D, string(text, 1, text_id))
        # Native choice prompts are nonblocking: 3057, rather than the message
        # itself, waits for input. Blocking here consumes A and clears the box.
        if question: row.unknown = 0
        text_id += 1

    # Helpers precede engine callbacks, as in the original event library.
    launch_id = 0x2000 + p.ordinal
    begin = p.function(launch_id)
    p.assign(0x10008, 4)
    say('Affiche prete ! Appuie sur A\\npour retrouver les capitaines.')
    p.emit(0x301E)
    p.emit(0x6008, expression(0x7003, variable(0x1000F), 0))
    ready = p.emit(0x6001, 1, 0)
    p.assign(0x10008, 2)
    for i in range(6):
        say(f'IZARENA-LINE-{i:02d} ' + '.' * 140, 1 if i % 2 == 0 else 190)
    p.emit(0x301E)
    emit_dynamic_removals(p)
    for slot in range(1, 17):
        p.emit(0x6008, expression(0x7002, expression(0x7003, slot, 0)))
        nonzero = p.emit(0x6001, 1, 0)
        p.emit(0x403E, slot, 30, slot)
        p.end(nonzero)
    p.emit(0x3005, 1, 30)
    p.emit(0x4058, 11)
    p.assign(0x10008, 10)
    p.assign(0x1000A, 3)
    p.assign(0x1002D, 1)
    p.assign(0x1001A, config['entry_key'])
    p.emit(0x4048, config['entry_key'])
    p.emit(0x4046, 33)
    p.emit(0x4016, 2)
    p.end(ready)
    p.emit(0x600C, 1)
    unavailable = p.emit(0x6001, 1, 0)
    say('Pour jouer cette affiche, ouvre\\nJouer au Club - coeur\\nmelonDS.cmd sur ton PC.')
    p.emit(0x301E)
    p.end(unavailable)
    p.end(begin)

    begin = p.function(0x1023)
    p.emit(0x2012)
    p.emit(0x6008, expression(0x7003, variable(RECRUIT_UNIT), FIRST_RECRUIT_ID))
    recruitment = p.emit(0x6001, 1, 0)
    p.emit(0x403E, variable(RECRUIT_UNIT), variable(RECRUIT_LEVEL), variable(RECRUIT_SLOT))
    p.assign(RECRUIT_UNIT, 0)
    p.assign(RECRUIT_LEVEL, 0)
    p.assign(RECRUIT_SLOT, 0)
    p.assign(RECRUIT_READY, FIRST_RECRUIT_ID)
    p.emit(0x2014)
    p.end(recruitment)
    p.emit(0x600C, 1)
    fixtures = p.emit(0x6001, 1, 0)
    p.assign(0x10008, 0)
    p.assign(0x1000E, 1)
    p.assign(0x1000F, 0)
    say('Bienvenue ! Choisis une affiche.\\nLes equipes invitees joueront\\navec leurs propres joueurs.')
    # A nested else chain gives each native No button the next offer.
    branches = []
    offers = [(index, title) for index, (_, _, title) in FIXTURES.items()]
    for index, title in [*offers, (CLUB_FIXTURE, 'Mon equipe du Club')]:
        if index == CLUB_FIXTURE:
            p.emit(0x6008, expression(0x7003, variable(RECRUIT_READY), FIRST_RECRUIT_ID))
            club_offer = p.emit(0x6001, 1, 0)
        p.emit(0x301E)
        p.assign(0x10008, 0)
        say(title + ' ?', question=True)
        p.emit(0x3057)
        p.emit(0x6008, expression(0x4020))
        yes = p.emit(0x6001, 1, 0)
        p.emit(0x301E)
        p.assign(0x1000F, index)
        p.emit(launch_id)
        p.end(yes)
        p.emit(0x600C, 1)
        otherwise = p.emit(0x6001, 1, 0)
        if index == CLUB_FIXTURE:
            p.end(otherwise)
            p.end(club_offer)
        else:
            branches.append(otherwise)
    p.emit(0x6008, expression(0x7002, expression(0x7003, variable(0x10008), 10)))
    no_match = p.emit(0x6001, 1, 0)
    say('Une autre fois alors !\\nReviens me voir quand tu veux.')
    p.end(no_match)
    for branch in reversed(branches):
        p.end(branch)
    # 4016 queues the match asynchronously. Do not run the field-event return
    # helper after a successful launch; it would cancel the pending transition.
    p.emit(0x6008, expression(0x7002, expression(0x7003, variable(0x10008), 10)))
    cancelled = p.emit(0x6001, 1, 0)
    p.emit(0x301E)
    p.assign(0x10008, 0)
    p.assign(0x1000F, 0)
    p.assign(0x1000E, 0)
    p.emit(0x2014)
    p.end(cancelled)
    p.end(fixtures)
    p.end(begin)
    return p.encode()
