from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Section:
    name: str
    start: int
    bars: int
    intensity: float

    @property
    def end(self) -> int:
        return self.start + self.bars

def _add(out: List[Section], name: str, bars: int, intensity: float):
    bars=max(0,int(bars))
    if bars:
        out.append(Section(name,sum(x.bars for x in out),bars,intensity))

def make_form(total_bars: int, genre: str) -> List[Section]:
    total_bars=max(4,int(total_bars))
    out: List[Section]=[]

    if total_bars <= 16:
        plan=[("intro",2,.48),("verse",4,.62),("chorus",4,.92),("bridge",2,.70),("final_chorus",3,1.0),("outro",1,.48)]
        remaining=total_bars
        for idx,(name,bars,intensity) in enumerate(plan):
            later_min=1 if idx < len(plan)-1 else 0
            use=min(bars,max(0,remaining-later_min))
            _add(out,name,use,intensity); remaining-=use
        if remaining: _add(out,"outro",remaining,.45)
        return out

    if total_bars <= 24:
        base=[["intro",2,.48],["verse",4,.62],["chorus",4,.94],["bridge",2,.72],["final_chorus",4,1.0],["outro",1,.45]]
        extra=total_bars-sum(x[1] for x in base)
        for idx,cap in ((1,6),(2,6),(4,6),(5,2)):
            add=min(max(0,extra),cap-base[idx][1]); base[idx][1]+=add; extra-=add
        if extra: base.insert(2,["pre",extra,.75])
        for name,bars,intensity in base: _add(out,name,bars,intensity)
        return out

    if total_bars <= 40:
        base=[["intro",3,.48],["verse",6,.62],["pre",2,.75],["chorus",6,.94],["bridge",2,.72],["final_chorus",5,1.0],["outro",1,.45]]
        extra=total_bars-sum(x[1] for x in base)
        for idx,cap in ((1,8),(2,4),(3,8),(4,4),(5,8),(6,2)):
            add=min(max(0,extra),cap-base[idx][1]); base[idx][1]+=add; extra-=add
        for name,bars,intensity in base[:-2]: _add(out,name,bars,intensity)
        if extra: _add(out,"solo",extra,.80 if genre=="rock" else .76)
        for name,bars,intensity in base[-2:]: _add(out,name,bars,intensity)
        return out

    extra=total_bars-40
    _add(out,"intro",4,.46); _add(out,"verse",8,.60); _add(out,"pre",4,.74); _add(out,"chorus",8,.93)
    use=min(8,extra)
    if use: _add(out,"verse2",use,.66); extra-=use
    use=min(4,extra)
    if use: _add(out,"pre2",use,.78); extra-=use
    use=min(8,extra)
    if use: _add(out,"chorus2",use,.96); extra-=use
    if extra: _add(out,"solo",extra,.82 if genre=="rock" else .78)
    _add(out,"bridge",4,.72); _add(out,"final_chorus",8,1.0); _add(out,"outro",4,.43)
    return out

def section_for_bar(form: List[Section], bar: int) -> Section:
    for section in form:
        if section.start <= bar < section.end: return section
    return form[-1]

def section_progress(section: Section, bar: int) -> float:
    if section.bars <= 1: return 1.0
    return (bar-section.start)/max(1,section.bars-1)

def serialize_form(form):
    return [{"name":s.name,"start_bar":s.start,"bars":s.bars,"intensity":s.intensity} for s in form]
