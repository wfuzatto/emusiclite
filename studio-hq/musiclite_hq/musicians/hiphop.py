from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note
from ..song_form import section_for_bar

# Dark four-bar cycle centered on F minor: Fm / Db / Eb / Cm.
ROOTS=[29,25,27,24]
PIANO_VOICINGS=[[53,56,60,65],[49,53,56,61],[51,55,58,63],[48,51,55,60]]
BRASS_VOICINGS=[[53,60,65,68],[49,56,61,65],[51,58,63,67],[48,55,60,63]]
STRING_VOICINGS=[[53,56,60],[49,53,56],[51,55,58],[48,51,55]]

def _v(base,intensity,h,spread=3): return h.velocity(round(base*(.84+.16*intensity)),spread)
def _is_hook(name): return "hook" in name

def hiphop_drums(events,bars,bpm,seed=8101,form=None,notes=None):
    h=Humanizer(seed,bpm);beat=PPQ;eighth=beat//2;sixteenth=beat//4;n=notes or {}
    K=n.get("kick",36);SN=n.get("snare",38);CH=n.get("hh_closed",42);OH=n.get("hh_open",46)
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;pos=bar-sec.start;hook=_is_hook(sec.name);breakdown=sec.name=="breakdown";intro=sec.name=="intro";ending=bar==sec.end-1
        if not (intro and pos==0):
            for i in range(8):
                t=base+i*eighth+h.ticks(-.6 if i%2==0 else 3.0,1.4);vel=78 if i in (0,4) else (68 if i%2==0 else 60)
                add_note(events,t,round(sixteenth*.52),CH,_v(vel,sec.intensity,h),9)
        rolls=[]
        if hook and bar%2==1: rolls=[3.00,3.25,3.50,3.75]
        elif ending and sec.name not in ("outro","breakdown"): rolls=[3.50,3.666,3.833]
        elif not intro and bar%4==3: rolls=[1.75,1.875]
        for j,b in enumerate(rolls):add_note(events,base+round(b*beat)+h.ticks(1.2,.7),round(sixteenth*.30),CH,_v(70+j*3,sec.intensity,h,2),9)
        if not (intro and pos==0):
            sn_t=base+2*beat+h.ticks(7.0 if not hook else 4.5,1.8);add_note(events,sn_t,round(sixteenth*.86),SN,_v(117 if hook else 108,sec.intensity,h),9)
            if hook:add_note(events,sn_t+max(1,h.ticks(10.0,1.0)),round(sixteenth*.70),SN,_v(67,sec.intensity,h,2),9)
        if breakdown:kicks=[0,2.75] if pos%2==0 else [.5,3.25]
        elif hook:kicks=[0,.75,1.50,2.75,3.50] if bar%2==0 else [0,.50,1.75,2.50,3.25,3.75]
        elif intro:kicks=[0,2.75] if pos>0 else [0]
        else:kicks=[0,.75,1.75,2.75,3.50] if bar%2==0 else [0,1.25,2.50,3.25]
        for j,b in enumerate(kicks):add_note(events,base+round(b*beat)+h.ticks(-1.0 if j==0 else 1.4,1.5),round(sixteenth*.78),K,_v(119 if j==0 else 105,sec.intensity,h),9)
        if (hook and bar%2==0) or ending:add_note(events,base+round(3.50*beat)+h.ticks(2.0,1.0),round(eighth*.62),OH,_v(80,sec.intensity,h),9)

def hiphop_sub(events,bars,bpm,seed=8202,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);root=ROOTS[bar%4];base=bar*4*beat;hook=_is_hook(sec.name);breakdown=sec.name=="breakdown";intro=sec.name=="intro"
        if intro and bar==sec.start:seq=[(0,root,3.55,76)]
        elif breakdown:seq=[(0,root,1.75,82),(2.75,root+12,.72,76)]
        elif hook:seq=[(0,root,1.30,113),(1.50,root,.72,103),(2.45,root+12,.42,94),(2.92,root,1.00,108)]
        else:seq=[(0,root,1.55,105),(1.80,root,.62,93),(2.75,root,1.05,102)]
        for b,n,d,v in seq:add_note(events,base+round(b*beat)+h.ticks(3.0,1.8),h.duration(round(d*beat),.025),n,_v(v,sec.intensity,h),0)

def hiphop_piano(events,bars,bpm,seed=8303,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;chord=PIANO_VOICINGS[bar%4];hook=_is_hook(sec.name);breakdown=sec.name=="breakdown";intro=sec.name=="intro"
        if intro:hits=[(0,1.65,72),(2.0,1.45,64)]
        elif hook:hits=[(0,1.35,83),(2.0,1.25,78),(3.45,.34,61)]
        elif breakdown:hits=[(0,2.70,61)]
        else:hits=[(0,1.45,72),(2.50,.88,64)] if bar%2==0 else [(.50,1.25,67),(3.0,.65,60)]
        for k,(b,d,v) in enumerate(hits):
            t0=base+round(b*beat)+h.ticks(5.5,2.8);spread=max(1,abs(h.ticks(18 if k==0 else 12,2.0)));order=chord if k%2==0 else list(reversed(chord))
            for j,note in enumerate(order):add_note(events,t0+j*spread,h.duration(max(1,round(d*beat)-j*spread),.035),note,_v(v-j*2,sec.intensity,h),0)

def hiphop_brass(events,bars,bpm,seed=8404,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;hook=_is_hook(sec.name);ending=bar==sec.end-1
        if not hook and not (ending and sec.name not in ("intro","outro")):continue
        chord=BRASS_VOICINGS[bar%4];hits=[(0,.48,100),(2.50,.34,89)] if hook else [(3.25,.35,86)]
        if hook and bar%2==1:hits.append((3.50,.24,82))
        for b,d,v in hits:
            t0=base+round(b*beat)+h.ticks(-1.0,1.8);spread=max(1,abs(h.ticks(7.0,1.2)))
            for j,note in enumerate(chord):add_note(events,t0+j*spread,h.duration(max(1,round(d*beat)-j*spread),.02),note,_v(v-j*2,sec.intensity,h),0)

def hiphop_strings(events,bars,bpm,seed=8505,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat
        if not (_is_hook(sec.name) or sec.name in ("intro","breakdown")):continue
        chord=STRING_VOICINGS[bar%4];dur=3.70 if _is_hook(sec.name) else 3.40;t0=base+h.ticks(13.0,3.5)
        for j,note in enumerate(chord):add_note(events,t0+j*max(1,h.ticks(8.0,1.0)),h.duration(round(dur*beat),.018),note+12,_v(58+j*2,sec.intensity,h,2),0)
