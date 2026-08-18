from ..humanize import Humanizer, PPQ
from ..midi_tools import add_note
from ..song_form import section_for_bar

ROCK_ROOTS=[40,43,36,38]
SERT_ROOTS=[43,38,40,36]

def _v(base,intensity,h,spread=3): return h.velocity(round(base*(.82+.18*intensity)),spread)

def rock_drums(events,bars,bpm,seed=7101,form=None,notes=None):
    h=Humanizer(seed,bpm);beat=PPQ;e=beat//2;s=beat//4;n=notes or {}
    K=n.get("kick",36);SN=n.get("snare",38);CH=n.get("hh_closed",42);OH=n.get("hh_open",46);CR=n.get("crash",49);RD=n.get("ride",51);RB=n.get("ride_bell",53);T1=n.get("tom_high",48);T2=n.get("tom_mid",47);T3=n.get("tom_low",45);TF=n.get("tom_floor",41)
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;pos=bar-sec.start;intense=sec.intensity;ending=pos==sec.bars-1;chorus="chorus" in sec.name;bridge=sec.name in ("bridge","solo");intro=sec.name=="intro";cym=RD if chorus and pos%4>=2 else CH
        if intro and pos<2:
            for i in (0,2,4,6):add_note(events,base+i*e+h.ticks(0,1.5),s,cym,_v(60,intense,h),9)
        else:
            for i in range(8):
                use=OH if i==7 and ending else cym
                if bridge and i in (2,6):use=RB
                vel=86 if i in (0,4) else (74 if i%2==0 else 65)
                add_note(events,base+i*e+h.ticks(-.6 if i%2==0 else 1.3,1.7),h.duration(round(e*.36),.04),use,_v(vel,intense,h),9)
            for b in (1,3):
                add_note(events,base+b*beat+h.ticks(5.5,2.0),round(s*.9),SN,_v(116 if chorus else 107,intense,h),9)
                if not chorus and (bar+b)%3==0:add_note(events,base+b*beat-s+h.ticks(-2,1.5),round(s*.45),SN,_v(42,intense,h),9)
            kicks=[0,2]+([1.5,2.75,3.5] if chorus else [.75,2.75])
            if bridge:kicks=[0,1.75,2.5,3.25]
            for j,b in enumerate(kicks):add_note(events,base+round(b*beat)+h.ticks(0,1.5),round(s*.75),K,_v(114 if j<2 else 101,intense,h),9)
        if pos==0 and not intro:add_note(events,base+h.ticks(0,1),beat,CR,_v(118,intense,h),9)
        if ending and sec.name!="outro":
            for i,note in enumerate([T1,T1,T2,T3,TF,SN]):add_note(events,base+round(2.5*beat)+i*s+h.ticks(0,1.6),round(s*.72),note,_v(84+i*5,intense,h),9)

def rock_bass(events,bars,bpm,seed=7202,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);root=ROCK_ROOTS[bar%4];base=bar*4*beat;chorus="chorus" in sec.name;bridge=sec.name in ("bridge","solo")
        if chorus:seq=[(0,root,.78,103),(.5,root,.36,88),(1,root+7,.72,96),(2,root,.78,105),(2.5,root,.34,88),(3,root+7,.68,98),(3.5,root+12,.32,84)]
        elif bridge:seq=[(0,root,.82,92),(1.5,root+7,.46,84),(2,root+12,.8,96),(3.25,root+7,.40,82)]
        else:seq=[(0,root,.82,96),(1,root+7,.60,85),(2,root,.80,96),(2.75,root+12,.38,78),(3.5,root+7,.34,80)]
        for b,n,d,v in seq:add_note(events,base+round(b*beat)+h.ticks(7.0,2.4),h.duration(round(d*beat),.035),n,_v(v,sec.intensity,h),0)
        if bar%2==1 and sec.name!="intro":add_note(events,base+round(3.82*beat)+h.ticks(7,2),round(.10*beat),root+2,_v(45,sec.intensity,h),0)

def _rock_guitar(events,bars,bpm,seed,side,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ;side_ms=-3.5 if side=="left" else 4.7
    for bar in range(bars):
        sec=section_for_bar(form,bar);root=ROCK_ROOTS[bar%4];base=bar*4*beat;chorus="chorus" in sec.name;bridge=sec.name in ("bridge","solo");intro=sec.name=="intro";ending=bar==sec.end-1;fifth=root+7;octave=root+12;chord=[root,fifth,octave] if side=="left" else [root,fifth,octave+7]
        if intro:hits=[(0,.85,92),(2,.85,88)] if bar-sec.start<2 else [(0,.7,92),(1,.45,82),(2,.7,94),(3,.45,84)]
        elif chorus:hits=[(0,.78,108),(1,.72,102),(2,.78,110),(3,.72,104)]
        elif bridge:hits=[(0,.92,92),(2,.90,96)]
        else:hits=[(0,.33,94),(.5,.28,78),(1,.31,88),(1.5,.27,76),(2,.36,98),(2.5,.27,77),(3,.31,89),(3.5,.27,79)]
        for k,(b,d,v) in enumerate(hits):
            t0=base+round(b*beat)+h.ticks(side_ms,2.0);notes=chord if chorus or bridge or k in (0,4) else chord[:2];spread_ms=9.5 if chorus else (13 if bridge else 3.5)
            if (k%2==1)^(side=="right"):notes=list(reversed(notes))
            spread=max(1,abs(h.ticks(spread_ms,1.0)))
            for j,note in enumerate(notes):add_note(events,t0+j*spread,h.duration(max(1,round(d*beat)-j*spread),.025),note,_v(v-j*2,sec.intensity,h),0)
        if ending and sec.name!="outro":
            lick=[octave,octave+2,octave+3,octave+2] if side=="left" else [fifth+12,octave+3,octave+2,octave]
            for i,note in enumerate(lick):add_note(events,base+round((3.05+i*.21)*beat)+h.ticks(side_ms,1.8),round(.16*beat),note,_v(84+i*2,sec.intensity,h),0)

def rock_guitar_left(events,bars,bpm,seed=7303,form=None,**kw):return _rock_guitar(events,bars,bpm,seed,"left",form=form,**kw)
def rock_guitar_right(events,bars,bpm,seed=7404,form=None,**kw):return _rock_guitar(events,bars,bpm,seed,"right",form=form,**kw)

def sertanejo_drums(events,bars,bpm,seed=7505,form=None,notes=None):
    h=Humanizer(seed,bpm);beat=PPQ;e=beat//2;s=beat//4;n=notes or {};K=n.get("kick",36);SN=n.get("snare",38);CH=n.get("hh_closed",42);OH=n.get("hh_open",46);CR=n.get("crash",49);T1=n.get("tom_high",48);T2=n.get("tom_mid",47);T3=n.get("tom_low",45)
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;pos=bar-sec.start;chorus="chorus" in sec.name;ending=bar==sec.end-1
        for i in range(8):
            note=OH if i==7 and (ending or chorus) else CH;accent=78 if i in (0,4) else (66 if i%2==0 else 57);add_note(events,base+i*e+h.ticks(-.5 if i%2==0 else 1.8,2.1),round(s*.82),note,_v(accent,sec.intensity,h),9)
        for b in (1,3):
            add_note(events,base+b*beat+h.ticks(7.0,2.5),round(s*.86),SN,_v(110 if chorus else 101,sec.intensity,h),9)
            if not chorus and (bar+b)%3==0:add_note(events,base+b*beat-s+h.ticks(-2,2),round(s*.44),SN,_v(38,sec.intensity,h),9)
        for j,b in enumerate([0,1,2,2.5] if chorus else [0,1,2,2.75]):add_note(events,base+round(b*beat)+h.ticks(1.0,1.8),round(s*.70),K,_v(108 if j in (0,2) else 91,sec.intensity,h),9)
        if pos==0 and chorus:add_note(events,base+h.ticks(0,1),beat,CR,_v(108,sec.intensity,h),9)
        if ending and sec.name!="outro":
            for i,note in enumerate([T1,T2,T3,SN]):add_note(events,base+3*beat+i*s+h.ticks(0,2),round(s*.7),note,_v(78+i*7,sec.intensity,h),9)

def sertanejo_bass(events,bars,bpm,seed=7606,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);root=SERT_ROOTS[bar%4];base=bar*4*beat;seq=[(0,root,.86,95),(1,root+7,.70,82),(2,root,.82,92),(2.75,root+12,.38,72),(3.5,root+7,.34,76)]
        if "chorus" in sec.name:seq += [(1.5,root,.25,75),(3.0,root,.28,78)]
        for b,n,d,v in seq:add_note(events,base+round(b*beat)+h.ticks(7.5,2.8),h.duration(round(d*beat),.04),n,_v(v,sec.intensity,h),0)

VOICINGS=[[55,59,62,67],[54,57,62,66],[52,55,59,64],[52,55,60,64]]
def sertanejo_guitar(events,bars,bpm,seed=7707,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;chord=VOICINGS[bar%4];chorus="chorus" in sec.name;pattern=[(0,1,.43,88),(.5,0,.27,60),(1,1,.40,78),(1.5,0,.25,62),(2,1,.43,91),(2.75,0,.21,60),(3,1,.39,79),(3.5,0,.25,64)]
        if chorus:pattern=[(0,1,.54,94),(.5,0,.30,66),(1,1,.48,84),(1.5,0,.29,68),(2,1,.55,96),(2.5,0,.29,65),(3,1,.48,85),(3.5,0,.30,69)]
        for b,down,d,v in pattern:
            notes=list(chord if down else reversed(chord));t0=base+round(b*beat)+h.ticks(-2 if down else 4,2.7);spread=max(1,abs(h.ticks(24 if down else 17,2)))
            for j,n in enumerate(notes):add_note(events,t0+j*spread,h.duration(max(1,round(d*beat)-j*spread),.03),n,_v(v-j*2,sec.intensity,h),0)

def sertanejo_piano(events,bars,bpm,seed=7808,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar)
        if sec.name in ("intro","bridge") or ("chorus" in sec.name and bar%2==0):
            base=bar*4*beat;chord=VOICINGS[bar%4]
            for b in (0,2):
                t0=base+b*beat+h.ticks(5,3)
                for i,n in enumerate(chord):add_note(events,t0+i*max(1,h.ticks(4.5,.8)),h.duration(round(1.5*beat),.025),n+12,_v(55+i*2,sec.intensity,h),0)

def sertanejo_accordion(events,bars,bpm,seed=7909,form=None,**_):
    h=Humanizer(seed,bpm);beat=PPQ
    for bar in range(bars):
        sec=section_for_bar(form,bar);base=bar*4*beat;chord=VOICINGS[bar%4][:3]
        if sec.name in ("intro","bridge") or (bar==sec.end-1 and sec.name!="outro"):
            if bar%2==0:
                t=base+h.ticks(12,4)
                for i,n in enumerate(chord):add_note(events,t+i*max(1,h.ticks(5,1)),h.duration(round(1.35*beat),.035),n+12,_v(54+i*2,sec.intensity,h),0)
            else:
                for i,n in enumerate([67,69,71,74,71,69,67]):add_note(events,base+round((2.0+i*.27)*beat)+h.ticks(6,2.5),round(.20*beat),n,_v(70+(5 if i==3 else 0),sec.intensity,h),0)
