from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note
from ..song_form import section_for_bar

# Custom SFZ map created by install_funk_hq.sh
KICK=36
CLAP=38
TAMBOR_LOW=45
TAMBOR_HIGH=47
HAT_CLOSED=42
HAT_OPEN=46
AGOGO_LOW=67
AGOGO_HIGH=68
CABASA=69

# F minor-ish club progression in the sub register.
FUNK_ROOTS=[29,32,24,27]


def _vel(base, intensity, h, spread=4):
    return h.velocity(round(base*(.80+.20*intensity)), spread)


def funk_drums(events,bars,bpm,seed=8101,form=None,**_):
    """Section-aware baile groove: tamborzao, claps, hats and organic percussion."""
    h=Humanizer(seed,bpm); beat=PPQ; eighth=beat//2; sixteenth=beat//4
    for bar in range(bars):
        sec=section_for_bar(form,bar); base=bar*4*beat; pos=bar-sec.start
        name=sec.name; intense=sec.intensity
        drop="drop" in name
        sparse=name in ("intro","break","outro")
        ending=bar==sec.end-1

        # Dry clap anchors 2 and 4, with a quieter pickup in high-energy sections.
        if not (name=="intro" and pos==0):
            for b in (1,3):
                add_note(events,base+b*beat+h.ticks(5.0,1.8),round(.18*beat),CLAP,_vel(111 if drop else 100,intense,h),9)
            if drop and bar%2:
                add_note(events,base+round(2.75*beat)+h.ticks(2.0,1.2),round(.12*beat),CLAP,_vel(57,intense,h),9)

        # Tamborzao core. Alternate bars so the loop never repeats mechanically.
        if sparse:
            kicks=[0,2.5]
            lows=[.75,2.0]
            highs=[1.5,3.25]
        elif drop:
            kicks=[0,.875,2.0,2.75,3.5] if bar%2==0 else [0,1.5,2.25,3.125]
            lows=[.5,1.75,3.0]
            highs=[1.25,2.5,3.75]
        else:
            kicks=[0,1.5,2.5,3.25]
            lows=[.75,2.0]
            highs=[1.25,2.75,3.5]

        for i,b in enumerate(kicks):
            add_note(events,base+round(b*beat)+h.ticks(0,1.25),round(.22*beat),KICK,_vel(118 if i==0 else 105,intense,h),9)
        for b in lows:
            add_note(events,base+round(b*beat)+h.ticks(2.2,1.5),round(.20*beat),TAMBOR_LOW,_vel(96,intense,h),9)
        for b in highs:
            add_note(events,base+round(b*beat)+h.ticks(-1.0,1.4),round(.16*beat),TAMBOR_HIGH,_vel(91,intense,h),9)

        # Hats: intentional 16th swing in drops; less dense outside them.
        hat_steps=range(16) if drop else range(0,16,2)
        for i in hat_steps:
            if sparse and i not in (0,4,8,12):
                continue
            delayed=(i%2)==1
            swing_ms=9.0 if delayed and drop else (3.5 if delayed else -0.5)
            note=HAT_OPEN if (i in (7,15) and (drop or ending)) else HAT_CLOSED
            vel=76 if i%4==0 else (63 if i%2==0 else 53)
            add_note(events,base+i*sixteenth+h.ticks(swing_ms,1.4),round(.11*beat),note,_vel(vel,intense,h,3),9)

        # Organic layer: agogo/cabasa enter by section, with round-robin handled in SFZ.
        if name not in ("intro","outro"):
            agogo_pattern=(1,5,9,13) if not drop else (1,3,6,9,11,14)
            for i,step in enumerate(agogo_pattern):
                note=AGOGO_HIGH if (i+bar)%2 else AGOGO_LOW
                add_note(events,base+step*sixteenth+h.ticks(4.0 if step%2 else 0,1.8),round(.16*beat),note,_vel(69 if drop else 58,intense,h),9)
            for step in range(2,16,4):
                add_note(events,base+step*sixteenth+h.ticks(6.0,1.6),round(.10*beat),CABASA,_vel(48 if drop else 41,intense,h),9)

        # Tiny end-of-section fill, not a rock drum fill.
        if ending and name not in ("outro",):
            for i,note in enumerate((TAMBOR_LOW,TAMBOR_HIGH,TAMBOR_LOW,TAMBOR_HIGH)):
                add_note(events,base+3*beat+i*sixteenth+h.ticks(1.0,1.1),round(.14*beat),note,_vel(88+i*4,intense,h),9)


def funk_sub(events,bars,bpm,seed=8202,form=None,**_):
    """808/sub follows the kick language but leaves breathing room for the tamborzao."""
    h=Humanizer(seed,bpm); beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar); base=bar*4*beat
        root=FUNK_ROOTS[bar%4]; drop="drop" in sec.name; sparse=sec.name in ("intro","break","outro")
        if sparse:
            seq=[(0,root,1.15,103),(2.5,root,1.05,92)]
        elif drop:
            seq=[(0,root,.72,114),(.875,root,.42,96),(2,root,.64,111),(2.75,root+12,.34,92),(3.5,root,.38,101)]
        else:
            seq=[(0,root,.82,106),(1.5,root,.52,91),(2.5,root,.68,104),(3.25,root+12,.34,88)]
        for b,n,d,v in seq:
            add_note(events,base+round(b*beat)+h.ticks(2.0,1.3),h.duration(round(d*beat),.018),n,_vel(v,sec.intensity,h,2),0)
